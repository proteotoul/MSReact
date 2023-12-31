import argparse
import asyncio
import json
import logging
import logging.config
import com.instrument as instrument
import com.mock as mock
import com.protocol.msrp as msrp
import com.transport.websocket as wst
from datetime import datetime
import signal
import time
import traceback
from algorithms.manager.acquisition import AcqMsgIDs
from algorithms.manager.algorithm_runner import AlgorithmManager
from custom_apps.manager import CustomAppManager
from enum import IntEnum

import cProfile

VERSION = 'v0.0'

class ClientStates(IntEnum):
    NO_ERROR    = 0
    ERROR       = 1

class MSReactClient:

    def __init__(self):
        
        # Set up logging
        logging.config.dictConfig(self.__load_log_config())
        self.logger = logging.getLogger(__name__)
        
        # Set up async loop and process executor
        self.loop = asyncio.new_event_loop()
        self.loop.set_exception_handler(self.custom_exception_handler)
        asyncio.set_event_loop(self.loop)
        
        # Instantiate transport and protocol layers here. TODO: if later those 
        # modules are selectable through the application, the instantiation
        # can be moved to a separate function. 
        # Instrument server manager are declared here but not yet instantiated.
        self.transport = wst.WebSocketTransport()
        self.protocol = msrp.MSReactProtocol(self.transport)
        self.inst_client = None
        
        # Instantiate the algorithm and custom app managers
        self.algo_manager = AlgorithmManager(self.algorithm_runner_cb)
        self.cusom_app_manager = CustomAppManager()
        
        self.state = ClientStates.NO_ERROR
        
    def parse_client_arguments(self):
        # Top level parser
        parser = argparse.ArgumentParser(description='MSReact python client')
        parser.add_argument('-v', '--version', action='version',
                            version = VERSION,
                            help='prints the version of the application')
        
        subparsers = parser.add_subparsers(help='available sub-commands:',
                                           dest='command')
                                           
        algorithm_choices = self.algo_manager.get_algorithm_names('releases')
        
        # Parser for sub-command "run"
        parser_run = \
            subparsers.add_parser('run',
                                  help='command to use developed algorithms')
        # TODO - Address won't be an input, but will be retreived from 
        # the middleware, or from elsewhere.
        parser_run.add_argument('address',
                                   help='address to the MSReact server')
        parser_run.add_argument('alg', choices = algorithm_choices,
                                   metavar = 'algorithm', default = 'monitor',
                                   help=f'algorithm to use during the acquisition, \
                                   choices: {", ".join(algorithm_choices)}')
                                   
        parser_run.add_argument('-c',
                                metavar = 'config',
                                dest = 'config',
                                help='configuration json file to pass into the \
                                      algorithm')
        
        parser_run.add_argument('-s',
                                metavar = 'sequence',
                                dest = 'sequence',
                                help='sequence file exported in csv format to \
                                      enable dynamic acquisition sequence execution')

        # Parser for sub-command "proto"
        proto_choices = \
            self.algo_manager.get_algorithm_names("prototypes")
        proto_choice_string = "\n".join(proto_choices)
        
        parser_proto = \
            subparsers.add_parser('proto',
                                  help='command for prototyping new algorithms')
                                  
        parser_proto.add_argument('-c',
                                  metavar = 'config',
                                  dest = 'config',
                                  help='configuration json file to pass into \
                                  the algorithm')
        
        parser_proto.add_argument('-s',
                                metavar = 'sequence',
                                dest = 'sequence',
                                help='sequence file exported in csv format to \
                                      enable dynamic acquisition sequence execution')
                                  
        parser_proto.add_argument('alg', choices = proto_choices,
                                 metavar = 'algorithm', default = 'monitor',
                                 help=f'algorithm to use during the acquisition, \
                                 choices: {", ".join(proto_choices)}')
        protoparser = parser_proto.add_subparsers(help='available modes:',
                                                  dest='mode')
        parser_proto_inst = \
            protoparser.add_parser('inst', help= 'subcommand to use MS \
                                   instrument for prototyping new algorithms')
        parser_proto_inst.add_argument('address',
                                       help='address to the MSReact server')
        
        parser_proto_mock = \
            protoparser.add_parser('mock', help= 'subcommand to use MS \
                                  mock for prototyping new algorithms')
        parser_proto_mock.add_argument('raw_files', nargs='+',
                                       help='full path and name of the raw \
                                       files to use for the simulated \
                                       acquisition in the sequence of the real \
                                       acquisition')
        parser_proto_mock.add_argument('scan_interval',
                                       help='interval between scans \
                                       transmissions in[ms], the time the \
                                       algorithm has between each scans to \
                                       analyse the scan and decide if it \
                                       requests a custom scan')
                                       
        # Parser for sub-command "test"
        app_choices = self.cusom_app_manager.get_app_names()
        parser_custom = \
            subparsers.add_parser('custom',
                                  help='command to use custom apps')
                                  
        parser_custom.add_argument('app', choices = app_choices,
                                   metavar = 'app', default = 'example',
                                   help=f'custom app to run, \
                                   choices: {", ".join(app_choices)}')
                                   
        parser_custom.add_argument('-c',
                                   metavar = 'config',
                                   dest = 'config',
                                   help='configuration json file to pass into \
                                   the algorithm')
        
        # TODO - This won't be an input, but will be retreived from 
        # the middleware
        parser_custom.add_argument('address',
                                   help='address to the MSReact server')


        self.args = parser.parse_args()
        
        return self.args
        
    def instrument_client_cb(self, msg_id, args = None):
        if (instrument.InstrMsgIDs.SCAN == msg_id):
            self.algo_manager.deliver_scan(args)
        elif (instrument.InstrMsgIDs.RECEIVED_RAW_FILE_NAMES == msg_id):
            self.logger.info(f'Received recent raw file names:{args}')
            self.algo_manager.received_recent_raw_file_names(args)
        elif (instrument.InstrMsgIDs.FINISHED_ACQ_FILE_DOWNLOAD == msg_id):
            self.logger.info('Received acquisition file download finished message.')
            self.algo_manager.acquisition_file_download_finished(args)
        elif (instrument.InstrMsgIDs.STARTED_ACQUISITION == msg_id):
            self.logger.info('Received started acquisition message.')
            self.algo_manager.acquisition_started()
        elif (instrument.InstrMsgIDs.FINISHED_ACQUISITION == msg_id):
            self.logger.info('Received finished acquisition message.')
            self.algo_manager.acquisition_ended()
        elif (instrument.InstrMsgIDs.ERROR == msg_id):
            self.logger.error(f'Received error message from instrument: {args}')
            self.algo_manager.instrument_error()
            self.state = ClientStates.ERROR
        
    async def algorithm_runner_cb(self, msg_id, args = None):
        if (AcqMsgIDs.REQUEST_SCAN == msg_id):
            await self.inst_client.request_scan(args)
        elif (AcqMsgIDs.REQUEST_REPEATING_SCAN == msg_id):
            pass
        elif (AcqMsgIDs.CANCEL_REPEATING_SCAN == msg_id):
            pass
        elif (AcqMsgIDs.READY_FOR_ACQUISITION_START == msg_id):
            #await self.inst_client.subscribe_to_scans()
            self.logger.info(f'{args.get_settings_dict()}')
            await self.inst_client.configure_acquisition(args.get_settings_dict())
            if args is not None:
                if args.acquisition_workflow.is_acquisition_triggering:
                    await self.inst_client.start_acquisition()
        elif (AcqMsgIDs.REQUEST_ACQUISITION_STOP == msg_id):
            await self.inst_client.stop_acquisition()
        elif (AcqMsgIDs.REQUEST_DEF_SCAN_PARAM_UPDATE == msg_id):
            await self.inst_client.update_default_scan_params(args)
        elif (AcqMsgIDs.SET_TX_SCAN_LEVEL == msg_id):
            if self.args.mode == "mock":
                await self.inst_client.set_ms_scan_tx_level(args)
        elif (AcqMsgIDs.ERROR == msg_id):
            self.logger.error(args)
            # Should let the instrument manager know that there was an error in
            # the algorithm manager.
            await self.inst_client.instrument_clean_up()
            self.state = ClientStates.ERROR
        elif (AcqMsgIDs.REQUEST_RAW_FILE_NAME == msg_id):
            await self.inst_client.request_raw_file_name()
        elif (AcqMsgIDs.REQUEST_LAST_RAW_FILE == msg_id):
            await self.inst_client.request_last_acquisition_file(args)
        elif (AcqMsgIDs.SUBSCRIBE_FOR_SCANS == msg_id):
            await self.inst_client.subscribe_to_scans()
        elif (AcqMsgIDs.UNSUBSCRIBE_FROM_SCANS == msg_id):
            await self.inst_client.unsubscribe_from_scans()
        
    async def run_on_instrument(self, loop, args):
    
        #pr = cProfile.Profile(builtins=False)
        #pr.enable()
        
        # Init the instrument server manager
        self.inst_client = \
            instrument.InstrumentClient(self.protocol,
                                        self.instrument_client_cb)

        self.logger.info(f'Instrument address: {args.address}')
        
        # Connect to the server
        success = await self.inst_client.connect_to_server(args.address)
        if success:
            self.logger.info("Successful connection to server!")
            # Wait a bit after connection
            await asyncio.sleep(1)
            
            # Start listening for messages from the server, select instrument,
            # and get possible parameters.
            await self.inst_client.setup_instrument_connection(1)

            # Get the type of the instrument
            intr_type = await self.inst_client.get_instrument_type()

            # Try to select the requested algorithm, and if the algorithm 
            # selection was successful run the algorithm.
            if self.algo_manager.select_algorithm(args.alg,
                                                  args.config,
                                                  intr_type,
                                                  args.sequence):
                await self.algo_manager.run_algorithm()
            else:
                self.logger.error(f"Failed loading {args.alg} workflow.")
            
            if self.state != ClientStates.ERROR:
                await self.inst_client.instrument_clean_up()
            self.logger.info("Client is shutting down.")
            
        else:
            self.logger.error("Connection Failed")
            
        #pr.disable()
        #pr.dump_stats('output/profiling.txt')
    
    async def run_on_mock(self, loop, args):
        # Init the mock instrument server manager
        self.inst_client = \
            mock.MockClient(self.protocol,
                            self.instrument_client_cb)
                                               
        self.inst_client.create_mock_server(args.raw_files,
                                            args.scan_interval)

        success = await self.inst_client.connect_to_server()
        
        if success:
            self.logger.info("Successful connection to server!")
            # Wait a bit after connection
            await asyncio.sleep(1)
            
            # Start listening for messages from the server, select instrument,
            # and get possible parameters.
            await self.inst_client.setup_instrument_connection(1)

            # Get the type of the instrument
            intr_type = await self.inst_client.get_instrument_type()

            if self.algo_manager.select_algorithm(args.alg,
                                                  args.config,
                                                  intr_type,
                                                  args.sequence):
                await self.algo_manager.run_algorithm()
            else:
                self.logger.error(f"Failed loading {args.alg} workflow.")
                self.inst_client.terminate_mock_server()
                
            self.logger.info("Unsubscribe from scans.")
            await self.inst_client.unsubscribe_from_scans()
            self.logger.info("Stop the listening loop.")
            listening_task.cancel()
            self.logger.info("Request shut down of mock server.")
            await self.inst_client.request_shut_down_server()
            self.logger.info("Client is shutting down.")
        else:
            self.logger.error("Connection Failed")
            self.inst_client.terminate_mock_server()
            
    async def test_app(self, loop, args):
        test = self.algo_manager.find_custom_test_by_name(args.suite, "test_algorithms")
        if test is not None:
            # It is a custom test
            test_instance = test(self.protocol, args.address, loop)
            test_instance.run_test()
        else:
            # It must be an algorithm
            # Init the instrument server manager
            self.inst_client = \
                instrument.InstrumentClient(self.protocol,
                                            self.instrument_client_cb)

            self.logger.info(f'Instrument address: {args.address}')
            success = await self.inst_client.connect_to_server(args.address)
            if success:
                self.logger.info("Successful connection to server!")
                # Wait a bit after connection
                await asyncio.sleep(1)
                
                await self.inst_client.setup_instrument_connection(1)

                # Get the type of the instrument
                intr_type = await self.inst_client.get_instrument_type()

                if self.algo_manager.select_algorithm(args.suite, args.config, intr_type):
                    await self.algo_manager.run_algorithm()
                else:
                    self.logger.error(f"Failed loading {args.suite} workflow.")
                    
                self.logger.info("Unsubscribe from scans.")
                await self.inst_client.unsubscribe_from_scans()
                self.logger.info("Stop the listening loop.")
                listening_task.cancel()
                self.logger.info("Disconnect from server.")
                await self.inst_client.disconnect_from_server()
                self.logger.info("Client is shutting down.")
                
            else:
                self.logger.error("Connection Failed")
            
    def __load_log_config(self):
        config = {}
        with open("pymsreact\\log_conf.json", "r", encoding="utf-8") as fd:
            config = json.load(fd)
            config["handlers"]["file"]["filename"] = \
                config["handlers"]["file"]["filename"] \
                + '_' \
                + datetime.now().strftime("%y%m%d_%H%M") \
                + '.log'
        return config
        
    def custom_exception_handler(self, loop, context):
        # first, handle with default handler
        #loop.default_exception_handler(context)

        message = context.get('exception', context["message"])
        self.logger.info(f'Caught exception: {message}')
        asyncio.create_task(self.shutdown(loop))
        
    async def shutdown(self, loop, signal=None):
        """Cleanup tasks tied to the service's shutdown."""
        if signal:
            self.logger.info(f"Received exit signal {signal.name}...")
        tasks = [t for t in asyncio.all_tasks() if t is not
                 asyncio.current_task()]

        [task.cancel() for task in tasks]

        self.logger.info(f"Cancelling {len(tasks)} outstanding tasks")
        await asyncio.gather(*tasks, return_exceptions=True)
        loop.stop()
        
if __name__ == "__main__":
    client = MSReactClient()
    args = client.parse_client_arguments()
    client.logger.info(f'Selected sub-command: {args.command}')
    loop = asyncio.get_event_loop()
    
    if ('run' == args.command):
        try:
            loop.run_until_complete(client.run_on_instrument(loop, args))
        except Exception as e:
            client.logger.error(f'Exception occured:')
            traceback.print_exc()
            loop.stop()
    elif ('proto' == args.command):
        try:
            client.logger.info(f'Selected mode: {args.mode}')
            if ('inst' == args.mode):
                loop.run_until_complete(client.run_on_instrument(loop, args))
            elif ('mock' == args.mode):
                loop.run_until_complete(client.run_on_mock(loop, args))
            else:
                client.logger.error('Please select a mode to run the selected' +
                                    ' algorithm prototype. See help [-h].')
        except Exception as e:
            client.logger.error(f'Exception occured:')
            traceback.print_exc()
            loop.stop()
    elif ('test' == args.command):
        try:
            loop.run_until_complete(client.test_app(loop, args))
        except Exception as e:
            client.logger.error(f'Exception occured:')
            traceback.print_exc()
            loop.stop()
