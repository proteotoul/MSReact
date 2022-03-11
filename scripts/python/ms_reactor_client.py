import argparse
import asyncio
import json
import logging
import logging.config
import multiprocessing
import signal
import time
import traceback
import websockets as ws
import ws_transport_exception as wste
from protocol import Protocol
from transport_layer import TransportLayer
from ws_transport import WebSocketTransport
from algorithm import Algorithm
from algorithm_runner import AlgorithmRunner, AlgorithmSync
from algorithm_list import AlgorithmList
from mock_server_manager import MockServerManager
from instrument_server_manager import InstrumentServerManager
from concurrent.futures import ProcessPoolExecutor
from acquisition_manager import AcquisitionManager
from mock_acquisition_manager import MockAcquisitionManager

VERSION = 'v0.1'

class MSReactorClient:

    DEFAULT_MOCK_URI = f'ws://localhost:4649/SWSS'
    def __init__(self):
        
        # Set up logging
        with open("log_conf.json", "r", encoding="utf-8") as fd:
            logging.config.dictConfig(json.load(fd))
        self.logger = logging.getLogger(__name__)
        
        # Set up async loop an process executor
        self.loop = asyncio.new_event_loop()
        self.loop.set_exception_handler(self.custom_exception_handler)
        asyncio.set_event_loop(self.loop)
        self.executor = ProcessPoolExecutor(max_workers=3)
        
        # Initialise algorithm, create algorithm list, create algorithm
        # synchronisation object
        self.algo = None
        self.algo_list = AlgorithmList()
        self.algo_sync = AlgorithmSync()
        self.algo_runner = AlgorithmRunner(self.algorithm_runner_cb)
        
    def parse_client_arguments(self):
        # Top level parser
        parser = argparse.ArgumentParser(description='MS Reactor python client')
        parser.add_argument('-v', '--version', action='version',
                            version = VERSION,
                            help='prints the version of the application')
        
        subparsers = parser.add_subparsers(help='available sub-commands:',
                                           dest='command')
                                           
        algorithm_choices = self.algo_runner.algo_list.get_available_names()
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
        parser_test = \
            subparsers.add_parser('test',
                                  help='command to use for testing')
                                  
        parser_test.add_argument('alg', choices = algorithm_choices,
                                 metavar = 'algorithm', default = 'monitor',
                                 help=f'algorithm to use during the acquisition, \
                                 choices: {", ".join(algorithm_choices)}')
        # TODO - This won't be an input, but will be retreived from 
        # the middleware
        parser_test.add_argument('address',
                                 help='address to the MSReactor server')

        return parser.parse_args()
        
    def instrument_server_manager_cb(self, id, args = None):
        if (self.inst_serv_man.CallbackIds.SCAN == id):
            self.algo_runner.deliver_scan(args)
        elif (self.inst_serv_man.CallbackIds.FINISHED_ACQUISITION == id):
            self.logger.info('Received finished acquisition message.')
            self.algo_runner.acquisition_ended()
        elif (self.inst_serv_man.CallbackIds.ERROR_CB == id):
            self.logger.error(args)
        
    async def algorithm_runner_cb(self, id, args = None):
        if (self.algo_runner.CallbackIds.REQUEST_SCAN == id):
            await self.inst_serv_man.request_scan(args)
        elif (self.algo_runner.CallbackIds.REQUEST_REPEATING_SCAN == id):
            pass
        elif (self.algo_runner.CallbackIds.CANCEL_REPEATING_SCAN == id):
            pass
        elif (self.algo_runner.CallbackIds.REQUEST_ACQUISITION_START == id):
            config = {
            "AcquisitionType": args.name,
            "AcquisitionParam": args.parameter
            }
            await self.inst_serv_man.subscribe_to_scans()
            await self.inst_serv_man.configure_acquisition(config)
            await self.inst_serv_man.start_acquisition()
        elif (self.algo_runner.CallbackIds.REQUEST_ACQUISITION_STOP == id):
            await self.inst_serv_man.stop_acquisition()
        elif (self.algo_runner.CallbackIds.ERROR == id):
            self.logger.error(args)
        
    def init_communication_layer(self):
        self.transport = WebSocketTransport()
        self.protocol = Protocol(self.transport)
        
    async def normal_app(self, loop, args):
        # Init transport and protocol layer
        self.init_communication_layer()
        
        # Init acquisition manager that is responsible for the sequence of 
        # acquisitions. TODO: Revisit these modules
        self.acq_man = AcquisitionManager()
        self.acq_man.interpret_acquisition(None, None)
        
        # Init the instrument server manager
        self.inst_serv_man = \
            InstrumentServerManager(self.protocol,
                                    self.algo_sync,
                                    self.acq_man,
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
            
            algorithm_type = self.algo_list.find_by_name(args.alg)
            if algorithm_type is not None:
                self.algo = algorithm_type()
                self.algorithm_runner = AlgorithmRunner(self.algo, 
                                                        None,
                                                        None,
                                                        self.algo_sync,
                                                        self.algorithm_runner_cb,
                                                        self.loop)
                # Note: args.raw_files were changed to None here.
                if self.algorithm_runner.configure_algorithm(None, None, None,
                                                             possible_params):
                    algo_proc = loop.run_in_executor(self.executor,
                                                     self.algo.algorithm_body)
                                                     
                    await asyncio.gather(self.start_instrument(),
                                         self.inst_serv_man.listen_for_scan_requests(),
                                         algo_proc)
            else:
                self.logger.error(f"Failed loading {args.alg}")
            
        else:
            self.logger.error("Connection Failed")
        
    async def normal_app_refactored(self, loop, args):
        # Init transport and protocol layer
        self.init_communication_layer()
        # Init the instrument server manager
        self.inst_serv_man = \
            InstrumentServerManager(self.protocol,
                                    self.algo_sync,
                                    None,
                                    self.instrument_server_manager_cb,
                                    loop)

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
            # TODO: Instrument info should be collected and provided to the 
            #       function later.
            if self.algo_runner.select_algorithm(args.alg, "Tribid"):
                #await asyncio.gather(self.start_instrument(),
                                     #self.algo_runner.run_algorithm())
                await self.algo_runner.run_algorithm()
            else:
                self.logger.error(f"Failed loading {args.alg}")
            
        else:
            self.logger.error("Connection Failed")
    
    async def mock_app(self, loop, args):
        # Init transport and protocol layer
        self.init_communication_layer()
        
        # Init acquisition manager that is responsible for the sequence of 
        # acquisitions. TODO: Revisit these modules
        self.acq_man = AcquisitionManager()
        self.acq_man.interpret_acquisition(None, None)
        
        # Init the mock instrument server manager
        self.inst_serv_man = MockServerManager(self.protocol,
                                               self.algo_sync,
                                               self.acq_man)
                                               
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
            
            algorithm_type = self.algo_list.find_by_name(args.alg)
            if algorithm_type is not None:
                self.algo = algorithm_type()
                self.algorithm_runner = AlgorithmRunner(self.algo, 
                                                        None,
                                                        None,
                                                        self.algo_sync,
                                                        self.algorithm_runner_cb,
                                                        self.loop)
                # Note: args.raw_files were changed to None here.                                       
                if self.algorithm_runner.configure_algorithm(None, None, None,
                                                             possible_params):
                    algo_proc = \
                        self.loop.run_in_executor(self.executor,
                                                  self.algo.algorithm_body)
                    
                    try:
                        await asyncio.gather(self.start_mock_instrument(),
                                             self.inst_serv_man.listen_for_scan_requests(),
                                             algo_proc)
                        await self.inst_serv_man.request_shut_down_server()
                    except Exception as e:
                        traceback.print_exc()
                        self.inst_serv_man.terminate_mock_server()
            else:
                self.logger.error(f"Failed loading {args.alg}")
            
        else:
            self.logger.error("Connection Failed")
            
    def test_app(self, args):
        # Init transport and protocol layer
        self.init_communication_layer()
        
        # Init acquisition manager that is responsible for the sequence of 
        # acquisitions. TODO: Revisit these modules
        self.acq_man = AcquisitionManager()
        self.acq_man.interpret_acquisition(None, None)
        
        # Init the Instrument controller
        self.inst_serv_man = InstrumentServerManager(self.protocol,
                                                     self.algo_sync,
                                                     self.acq_man)
        # Create URI for connection. TODO: should only address be given and 
        # the URI generated within the transport layer?
        self.logger.info(f'Instrument address: {args.address}')
        if self.run_async_as_sync(self.inst_serv_man.connect_to_server, 
                                  (args.address,)):
            self.logger.info("Successful connection to server!")
            # Wait a bit after connection
            time.sleep(1)
            
            # Select instrument TODO - This should be instrument discovery
            self.run_async_as_sync(self.inst_serv_man.select_instrument, (1,))
            
            # Collect possible parameters for requesting custom scans
            possible_params = \
                self.run_async_as_sync(self.inst_serv_man.get_possible_params, 
                                       None)
            
            algorithm_type = self.algo_list.find_by_name(args.alg)
            if algorithm_type is not None:
                self.algo = algorithm_type()
                # Note: args.raw_files were changed to None here.                                         
                algo_proc = \
                    self.loop.run_in_executor(self.executor,
                                              self.algo.algorithm_body)
                                                 
                tasks = asyncio.gather(self.start_instrument(),
                                       self.inst_serv_man.listen_for_scan_requests(),
                                       self.algo_runner.run_algorithm())
                try:
                    self.loop.run_until_complete(tasks)
                except Exception as e:
                    traceback.print_exc()
                    self.loop.stop()
            else:
                self.logger.error(f"Failed loading {args.alg}")
            
        else:
            self.logger.error("Connection Failed")
        
    async def start_mock_instrument(self):
        await self.inst_serv_man.subscribe_to_scans()
        await self.inst_serv_man.set_ms_scan_tx_level(self.algo.TRANSMITTED_SCAN_LEVEL)
        await self. inst_serv_man.prepare_acquisition()
        
    async def start_instrument(self):
        config = {
            "AcquisitionType": "Method",
            "AcquisitionParam": "default.meth"
        }
        '''
        config = {
            "AcquisitionType": "LimitedByTime",
            "AcquisitionParam": "5"
        }'''
        
        await self.inst_serv_man.subscribe_to_scans()
        await self.inst_serv_man.configure_acquisition(config)
        await self. inst_serv_man.prepare_acquisition()
        
    def run_async_as_sync(self, coroutine, args):
        loop = self.loop
        if args is not None:
            result = loop.run_until_complete(coroutine(*args))
        else:
            result = loop.run_until_complete(coroutine())
        return result
        
    def custom_exception_handler(loop, context):
        # first, handle with default handler
        #loop.default_exception_handler(context)

        message = context.get('exception', context["message"])
        self.logger.info(f'Caught exception: {message}')
        asyncio.create_task(self.shutdown(loop))
        #if isinstance(exception, ZeroDivisionError):
        #    self.logger.info(context)
        #    loop.stop()
        #self.logger.info(context)
        #loop.stop()
        
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
    client.logger.info(f'Selected algorithm: {args.alg}')
    client.logger.info(f'Selected sub-command: {args.command}')
    loop = asyncio.get_event_loop()
    
    if ('normal' == args.command):
        try:
            loop.run_until_complete(client.normal_app_refactored(loop, args))
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
        client.test_app(args)
