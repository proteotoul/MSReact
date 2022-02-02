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
from mock_controller import MockController
from instrument_controller import InstrumentController
from concurrent.futures import ProcessPoolExecutor
from acquisition_manager import AcquisitionManager
from mock_acquisition_manager import MockAcquisitionManager

VERSION = 'v0.1'

class ThermoMockClient:

    DEFAULT_MOCK_URI = f'ws://localhost:4649/SWSS'
    def __init__(self):
        self.algo_list = AlgorithmList()
        self.algorithm = None
        self.scan_queue = multiprocessing.Manager().Queue()
        self.req_queue = multiprocessing.Manager().Queue()
        self.algo_sync = AlgorithmSync()
        
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Set up logging
        #logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(module)s.' +
        #                           '%(funcName)s\n\t%(message)s',
        #                    level=logging.DEBUG)
        with open("log_conf.json", "r", encoding="utf-8") as fd:
            logging.config.dictConfig(json.load(fd))
        self.logger = logging.getLogger(__name__)
        
        #time.sleep(10)
        
    def parse_client_arguments(self):
        # Top level parser
        parser = argparse.ArgumentParser(description='ThermoMock python client')
        parser.add_argument('-v', '--version', action='version',
                            version = VERSION,
                            help='prints the version of the application')
        algorithm_choices = self.algo_list.get_available_names()
        parser.add_argument('alg', choices = algorithm_choices,
                            metavar = 'algorithm', default = 'monitor',
                            help=f'algorithm to use during the acquisition, \
                            choices: {", ".join(algorithm_choices)}')
        
        subparsers = parser.add_subparsers(help='available sub-commands:',
                                           dest='command')
        
        # Parser for sub-command "normal"
        parser_real = \
            subparsers.add_parser('real',
                                  help='command to use a real instrument')
        # TODO - This won't be an input, but will be retreived from 
        # the middleware
        parser_real.add_argument('address',
                                 help='address to the MSReactor server')
        
        # Parser for sub-command "mock"
        parser_mock = \
            subparsers.add_parser('mock', 
                                  help='command to use mock instrument instead \
                                  of a real instrument')
        parser_mock.add_argument('raw_files', nargs='+',
                                 help='full path and name of the raw files to \
                                       use for the simulated acquisition in \
                                       the sequence of the real acquisition')
        parser_mock.add_argument('scan_interval',
                                 help='interval between scans transmissions \
                                       in[ms], the time the algorithm has \
                                       between each scans to analyse the scan \
                                       and decide if it requests a custom scan')

        return parser.parse_args()
        
    def create_mock_server(self, raw_file_list, scan_interval):
        self.ws_transport = WebSocketTransport(self.DEFAULT_MOCK_URI)
        self.protocol = Protocol(self.ws_transport)
        self.acq_man = MockAcquisitionManager()
        self.acq_man.interpret_acquisition(None, raw_file_list)
        mock_controller = MockController(self.protocol,
                                         self.algo_sync,
                                         self.acq_man,
                                         raw_file_list = raw_file_list,
                                         scan_interval = scan_interval)
        #mock_controller.create_mock_server()
        
        return mock_controller
        
    def set_up_instrument_controller(self, address):
        # Use address instead of default URI
        uri = f'ws://{address}:4649/SWSS'
        self.logger.info(uri)
        self.ws_transport = WebSocketTransport(uri)
        self.protocol = Protocol(self.ws_transport)
        self.acq_man = AcquisitionManager()
        self.acq_man.interpret_acquisition(None, None)
        instrument_controller = InstrumentController(self.protocol,
                                                     self.algo_sync,
                                                     self.acq_man)
        return instrument_controller
        
    async def config_instrument(self, inst_cont, args):
        success = False
        
        #inst_cont = InstrumentController(self.protocol,
        #                                      self.algo_sync)
        #TODO - This is fine for now but in the future the client will connect
        #       to some other URI probably.
        await inst_cont.connect_to_instrument(f'ws://{args.address}:4649/SWSS')
        # TODO - Remove this if it's not necessary
        await asyncio.sleep(1)
        
        #logging.getLogger("websockets").setLevel(logging.WARNING)
        #logging.getLogger("websockets.protocol").setLevel(logging.WARNING)
        #logging.getLogger("websockets.server").setLevel(logging.WARNING)
        
        # TODO - Instrument discovery shall take place later.
        await inst_cont.select_instrument(1)
        possible_parameters = await inst_cont.get_possible_params()
        
        await inst_cont.subscribe_to_scans()
        
        algorithm_type = self.algo_list.find_by_name(args.alg)
        if algorithm_type is not None:
            self.algorithm = algorithm_type()
        if self.algorithm is not None:
            self.algorithm_runner = AlgorithmRunner(self.algorithm, 
                                                    None,
                                                    None,
                                                    self.algo_sync)
            # Note: args.raw_files were changed to None here. config_instrument should be separated just like most things in this class.                                        
            success = \
                self.algorithm_runner.configure_and_validate_algorithm(None,
                                                                       None,
                                                                       None,
                                                                       possible_parameters)
        return success
        
    async def start_mock_instrument(self, mock_cont):
        await mock_cont.set_ms_scan_tx_level(self.algorithm.TRANSMITTED_SCAN_LEVEL)
        await mock_cont.listen_for_scans()
        
    async def start_instrument(self, inst_cont):
        config = {
            "AcquisitionType": "Method",
            "AcquisitionParam": "default.meth"
        }
        '''
        config = {
            "AcquisitionType": "LimitedByTime",
            "AcquisitionParam": "5"
        }'''
        
        #await inst_cont.subscribe_to_scans()
        await inst_cont.configure_acquisition(config)
        await inst_cont.listen_for_scans()
        
    def run_async_as_sync(self, coroutine, args):
        #loop = asyncio.get_event_loop()
        #loop = asyncio.get_running_loop()
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
    client = ThermoMockClient()
    args = client.parse_client_arguments()
    client.logger.info(f'Selected algorithm: {args.alg}')
    client.logger.info(f'Selected sub-command: {args.command}')
    if ('real' == args.command):
        inst_cont = \
            client.set_up_instrument_controller(args.address)
        try:
            result = client.run_async_as_sync(client.config_instrument, 
                                              (inst_cont, args))
        
            if result:
                #loop = asyncio.get_event_loop()
                #loop = asyncio.get_running_loop()
                loop = client.loop
                
                #signals = (signal.SIGTERM, signal.SIGINT)
                #for s in signals:
                #    loop.add_signal_handler(
                #        s, lambda s=s: asyncio.create_task(client.shutdown(loop, signal=s)))
                
                loop.set_exception_handler(client.custom_exception_handler)
                executor = ProcessPoolExecutor(max_workers=1)
                algo_proc = \
                    loop.run_in_executor(executor, client.algorithm.algorithm_body)
                loop.run_until_complete(asyncio.gather(
                                            #inst_cont.listen_for_scans(),
                                            client.start_instrument(inst_cont),
                                            inst_cont.listen_for_scan_requests(),
                                            algo_proc))
                                            
                #client.run_async_as_sync(inst_cont.request_shut_down_server, None)
        except Exception as e:
            traceback.print_exc()
            #client.logger.info(e)
            #inst_cont.terminate_mock_server()
            #loop = asyncio.get_event_loop()
            #loop = asyncio.get_running_loop()
            loop = client.loop
            loop.stop()
    elif ('mock' == args.command):
        client.logger.info(f'Selected raw files: {args.raw_files}')
        client.logger.info(f'Selected scan interval: {args.scan_interval}')
        mock_cont = \
            client.create_mock_server(args.raw_files, args.scan_interval)
        try:
            result = client.run_async_as_sync(client.config_instrument, 
                                              (mock_cont, args))
        
            if result:
                #loop = asyncio.get_event_loop()
                #loop = asyncio.get_running_loop()
                loop = client.loop
                loop.set_exception_handler(client.custom_exception_handler)
                executor = ProcessPoolExecutor(max_workers=1)
                algo_proc = \
                    loop.run_in_executor(executor, client.algorithm.algorithm_body)
                loop.run_until_complete(asyncio.gather(
                                            client.start_mock_instrument(mock_cont),
                                            mock_cont.listen_for_scan_requests(),
                                            algo_proc))
                                            
                client.run_async_as_sync(mock_cont.request_shut_down_server, None)
        except Exception as e:
            client.logger.info(e)
            mock_cont.terminate_mock_server()
            #loop = asyncio.get_event_loop()
            #loop = asyncio.get_running_loop()
            loop = client.loop
            loop.stop()