import argparse
import asyncio
import json
import logging
import logging.config
import signal
import time
import traceback
import websockets as ws
import ws_transport_exception as wste
from acquisition import AcqMsgIDs
from algorithm import Algorithm
from algorithm_list import AlgorithmList
from algorithm_runner import AlgorithmRunner
from custom_test import CustomTest
from instrument_server_manager import InstrumentServerManager, InstrMsgIDs
from mock_server_manager import MockServerManager
from protocol import Protocol
from test_list import TestList
from transport_layer import TransportLayer
from ws_transport import WebSocketTransport

VERSION = 'v0.1'

class MSReactorClient:

    def __init__(self):
        
        # Set up logging
        with open("log_conf.json", "r", encoding="utf-8") as fd:
            logging.config.dictConfig(json.load(fd))
        self.logger = logging.getLogger(__name__)
        
        # Set up async loop and process executor
        self.loop = asyncio.new_event_loop()
        self.loop.set_exception_handler(self.custom_exception_handler)
        asyncio.set_event_loop(self.loop)
        
        # Instantiate transport and protocol layers here. TODO: if later those 
        # modules are selectable through the application, the instantiation
        # can be moved to a separate function. 
        # Instrument server manager are declared here but not yet instantiated.
        self.transport = WebSocketTransport()
        self.protocol = Protocol(self.transport)
        self.inst_serv_man = None
        self.algo_runner = None
        
        # Instantiate the algorithm  and test algorithm lists
        self.algo_list = AlgorithmList()
        self.test_list = TestList()
        
    def parse_client_arguments(self):
        # Top level parser
        parser = argparse.ArgumentParser(description='MS Reactor python client')
        parser.add_argument('-v', '--version', action='version',
                            version = VERSION,
                            help='prints the version of the application')
        
        subparsers = parser.add_subparsers(help='available sub-commands:',
                                           dest='command')
                                           
        algorithm_choices = self.algo_list.get_available_names()
        algo_choice_string = "\n".join(algorithm_choices)
        
        # Parser for sub-command "normal"
        parser_normal = \
            subparsers.add_parser('normal',
                                  help='command to use a real instrument')
        parser_normal.add_argument('alg', choices = algorithm_choices,
                                   metavar = 'algorithm', default = 'monitor',
                                   help=f'algorithm to use during the acquisition, \
                                   choices: {", ".join(algorithm_choices)}')
        # TODO - This won't be an input, but will be retreived from 
        # the middleware
        parser_normal.add_argument('address',
                                   help='address to the MSReactor server')
        
        # Parser for sub-command "mock"
        parser_mock = \
            subparsers.add_parser('mock', 
                                  help='command to use mock instrument instead \
                                  of a real instrument')
        parser_mock.add_argument('alg', choices = algorithm_choices,
                                 metavar = 'algorithm', default = 'monitor',
                                 help=f'algorithm to use during the acquisition, \
                                 choices: {algo_choice_string}')
        parser_mock.add_argument('raw_files', nargs='+',
                                 help='full path and name of the raw files to \
                                       use for the simulated acquisition in \
                                       the sequence of the real acquisition')
        parser_mock.add_argument('scan_interval',
                                 help='interval between scans transmissions \
                                       in[ms], the time the algorithm has \
                                       between each scans to analyse the scan \
                                       and decide if it requests a custom scan')
                                       
        # Parser for sub-command "test"
        test_choices = self.test_list.get_available_names()
        parser_test = \
            subparsers.add_parser('test',
                                  help='command to use for testing')
                                  
        parser_test.add_argument('suite', choices = test_choices,
                                 metavar = 'suite', default = 'monitor',
                                 help=f'test suite to run, \
                                 choices: {", ".join(test_choices)}')
        # TODO - This won't be an input, but will be retreived from 
        # the middleware
        parser_test.add_argument('address',
                                 help='address to the MSReactor server')

        return parser.parse_args()
        
    def instrument_server_manager_cb(self, msg_id, args = None):
        if (InstrMsgIDs.SCAN == msg_id):
            self.algo_runner.deliver_scan(args)
        elif (InstrMsgIDs.FINISHED_ACQUISITION == msg_id):
            self.logger.info('Received finished acquisition message.')
            self.algo_runner.acquisition_ended()
        elif (InstrMsgIDs.ERROR == msg_id):
            self.logger.error(f'Receved error message from instrument: {args}')
            self.algo_runner.instrument_error()
        
    async def algorithm_runner_cb(self, msg_id, args = None):
        if (AcqMsgIDs.REQUEST_SCAN == msg_id):
            await self.inst_serv_man.request_scan(args)
        elif (AcqMsgIDs.REQUEST_REPEATING_SCAN == msg_id):
            pass
        elif (AcqMsgIDs.CANCEL_REPEATING_SCAN == msg_id):
            pass
        elif (AcqMsgIDs.READY_FOR_ACQUISITION_START == msg_id):
            await self.inst_serv_man.subscribe_to_scans()
            self.logger.info(f'{args.get_settings_dict()}')
            await self.inst_serv_man.configure_acquisition(args.get_settings_dict())
            if args is not None:
                if args.acquisition_workflow.is_acquisition_triggering:
                    await self.inst_serv_man.start_acquisition()
        elif (AcqMsgIDs.REQUEST_ACQUISITION_STOP == msg_id):
            await self.inst_serv_man.stop_acquisition()
        elif (AcqMsgIDs.ERROR == msg_id):
            self.logger.error(args)
        
    async def normal_app(self, loop, args):
        # Init the instrument server manager
        self.inst_serv_man = \
            InstrumentServerManager(self.protocol,
                                    self.instrument_server_manager_cb)

        self.logger.info(f'Instrument address: {args.address}')
        success = await self.inst_serv_man.connect_to_server(args.address)
        if success:
            self.logger.info("Successful connection to server!")
            # Wait a bit after connection
            await asyncio.sleep(1)
            
            loop.create_task(self.inst_serv_man.listen_for_messages())
            # Select instrument TODO - This should be instrument discovery
            await self.inst_serv_man.select_instrument(1)
            
            # Collect possible parameters for requesting custom scans
            possible_params = await self.inst_serv_man.get_possible_params()
            
            # Init the algorithm runner
            self.algo_runner = AlgorithmRunner(self.algorithm_runner_cb,
                                               self.algo_list)
            # TODO: Instrument info should be collected and provided to the 
            #       function later.
            if self.algo_runner.select_algorithm(args.alg, "Tribid"):
                await self.algo_runner.run_algorithm()
            else:
                self.logger.error(f"Failed loading {args.alg}")
            
        else:
            self.logger.error("Connection Failed")
    
    async def mock_app(self, loop, args):
        # Init the mock instrument server manager
        self.inst_serv_man = MockServerManager(self.protocol,
                                               self.instrument_server_manager_cb,
                                               loop)
                                               
        self.inst_serv_man.create_mock_server(args.raw_files,
                                              args.scan_interval)

        success = await self.inst_serv_man.connect_to_server()
        
        if success:
            self.logger.info("Successful connection to server!")
            # Wait a bit after connection
            await asyncio.sleep(1)
            
            loop.create_task(self.inst_serv_man.listen_for_messages())
            # Select instrument TODO - This should be instrument discovery
            await self.inst_serv_man.select_instrument(1)
            
            # Collect possible parameters for requesting custom scans
            possible_params = await self.inst_serv_man.get_possible_params()
            
            #self.inst_serv_man.set_ms_scan_tx_level
            
            # Init the algorithm runner
            self.algo_runner = AlgorithmRunner(self.algorithm_runner_cb,
                                               self.algo_list)
            # TODO: Instrument info should be collected and provided to the 
            #       function later.
            if self.algo_runner.select_algorithm(args.alg, "Tribid"):
                await self.algo_runner.run_algorithm()
                await self.inst_serv_man.request_shut_down_server()
            else:
                self.logger.error(f"Failed loading {args.alg}")
                self.inst_serv_man.terminate_mock_server()
        else:
            self.logger.error("Connection Failed")
            self.inst_serv_man.terminate_mock_server()
            
    async def test_app(self, loop, args):
        test = self.test_list.find_custom_test_by_name(args.suite)
        if test is not None:
            # It is a custom test
            test_instance = test(self.protocol, args.address, loop)
            test_instance.run_test()
        else:
            # It must be an algorithm
            # Init the instrument server manager
            self.inst_serv_man = \
                InstrumentServerManager(self.protocol,
                                        self.instrument_server_manager_cb)

            self.logger.info(f'Instrument address: {args.address}')
            success = await self.inst_serv_man.connect_to_server(args.address)
            if success:
                self.logger.info("Successful connection to server!")
                # Wait a bit after connection
                await asyncio.sleep(1)
                
                loop.create_task(self.inst_serv_man.listen_for_messages())
                # Select instrument TODO - This should be instrument discovery
                await self.inst_serv_man.select_instrument(1)
                
                # Collect possible parameters for requesting custom scans
                possible_params = await self.inst_serv_man.get_possible_params()
                
                # Init the algorithm runner
                self.algo_runner = \
                    AlgorithmRunner(self.algorithm_runner_cb, 
                                    self.test_list.algorithm_test_list)
                # TODO: Instrument info should be collected and provided to the 
                #       function later.
                if self.algo_runner.select_algorithm(args.suite, "Tribid"):
                    await self.algo_runner.run_algorithm()
                else:
                    self.logger.error(f"Failed loading {args.suite}")
                
            else:
                self.logger.error("Connection Failed")
        
    def custom_exception_handler(loop, context):
        # first, handle with default handler
        #loop.default_exception_handler(context)

        message = context.get('exception', context["message"])
        self.logger.info(f'Caught exception: {message}')
        asyncio.create_task(self.shutdown(loop))
        
    async def shutdown(loop, signal=None):
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
    client = MSReactorClient()
    args = client.parse_client_arguments()
    #client.logger.info(f'Selected algorithm: {args.alg}')
    client.logger.info(f'Selected sub-command: {args.command}')
    loop = asyncio.get_event_loop()
    
    if ('normal' == args.command):
        try:
            loop.run_until_complete(client.normal_app(loop, args))
        except Exception as e:
            traceback.print_exc()
            loop.stop()
    elif ('mock' == args.command):
        try:
            loop.run_until_complete(client.mock_app(loop, args))
        except Exception as e:
            traceback.print_exc()
            loop.stop()
    elif ('test' == args.command):
        try:
            loop.run_until_complete(client.test_app(loop, args))
        except Exception as e:
            traceback.print_exc()
            loop.stop()
