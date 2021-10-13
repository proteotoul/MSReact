import argparse
import asyncio
import multiprocessing
import time
import websockets as ws
import ws_transport_exception as wste
from protocol import Protocol
from transport_layer import TransportLayer
from ws_transport import WebSocketTransport
from algorithm import Algorithm
from algorithm_runner import AlgorithmRunner
from algorithm_list import AlgorithmList
from mock_controller import MockController
from instrument_controller import InstrumentController
from concurrent.futures import ProcessPoolExecutor

VERSION = 'v0.1'

class ThermoMockClient:

    DEFAULT_MOCK_URI = f'ws://localhost:4649/SWSS'
    def __init__(self):
        self.algo_list = AlgorithmList()
        self.algorithm = None
        self.scan_queue = multiprocessing.Manager().Queue()
        self.req_queue = multiprocessing.Manager().Queue()
        pass
        
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
        
    async def config_instrument(self, args):
        success = False
        
        self.ws_transport = WebSocketTransport(self.DEFAULT_MOCK_URI)
        self.protocol = Protocol(self.ws_transport)
        self.inst_cont = InstrumentController(self.ws_transport,
                                              self.protocol,
                                              self.scan_queue,
                                              self.req_queue)
        await self.inst_cont.connect_to_instrument(self.DEFAULT_MOCK_URI)
        # TODO - Remove this if it's not necessary
        await asyncio.sleep(1)
        possible_parameters = await self.inst_cont.get_possible_params_async()
        
        await self.inst_cont.subscribe_to_scans_async()
        
        algorithm_type = self.algo_list.find_by_name(args.alg)
        if algorithm_type is not None:
            self.algorithm = algorithm_type()
        if self.algorithm is not None:
            self.algorithm_runner = AlgorithmRunner(self.algorithm, 
                                                    None,
                                                    None,
                                                    self.scan_queue,
                                                    self.req_queue)
            success = \
                self.algorithm_runner.configure_and_validate_algorithm(None, 
                                                                       None,
                                                                       None,
                                                                       possible_parameters)
        return success
        
        
    async def mock_instrument_start(self):
        await self.inst_cont.mock_start_scan_tx_async()
        await self.inst_cont.start_listening_for_scans()
        
    def run_async_as_sync(self, coroutine, args):
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(coroutine(*args))
        return result   
        
if __name__ == "__main__":
    client = ThermoMockClient()
    args = client.parse_client_arguments()
    print(f'Selected algorithm: {args.alg}')
    print(f'Selected sub-command: {args.command}')
    if ('real' == args.command):
        print("Not implemented.")
    elif ('mock' == args.command):
        print(f'Selected raw files: {args.raw_files}')
        print(f'Selected scan interval: {args.scan_interval}')
        
        mock_controller = MockController(raw_file_list = args.raw_files,
                                         scan_interval = args.scan_interval)                                 
        mock_controller.run_mock_nonblock()
    
        result = client.run_async_as_sync(client.config_instrument, (args,))
    
        if result:
            loop = asyncio.get_event_loop()
            executor = ProcessPoolExecutor()
            algo_proc = \
                loop.run_in_executor(executor, client.algorithm.algorithm_body)
            loop.run_until_complete(asyncio.gather(
                                        client.mock_instrument_start(), 
                                        algo_proc))
            mock_controller.terminate_mock_server()