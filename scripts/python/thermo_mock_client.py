import argparse
import asyncio
import websockets as ws
import ws_transport_exception as wste
from protocol import Protocol
from transport_layer import TransportLayer
from ws_transport import WebSocketTransport
from algorithm import Algorithm
from algorithm_list import algorithm_list
from mock_controller import MockController
from instrument_controller import InstrumentController

VERSION = 'v0.1'

class ThermoMockClient:

    DEFAULT_MOCK_URI = f'ws://localhost:4649/SWSS'
    def __init__(self):
        pass
        
    def parse_client_arguments(self):
        # Top level parser
        parser = argparse.ArgumentParser(description='ThermoMock python client')
        parser.add_argument('-v', '--version', action='version', 
                            version = VERSION,
                            help='prints the version of the application')
        algorithm_choices = \
            [Algorithm.ALGORITHM_NAME for Algorithm in algorithm_list]
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
        

    async def main_real(self, args):
        print(f'Entered address: {args.address}')
        
    async def main_mock(self, args):
        print(f'Selected raw files: {args.raw_files}')
        print(f'Selected scan interval: {args.scan_interval}')
        
        mock_controller = MockController(raw_file_list = args.raw_files,
                                         scan_interval = args.scan_interval)
                                         
        mock_controller.run_mock_nonblock()

        async with WebSocketTransport(self.DEFAULT_MOCK_URI) as ws_transport:
            protocol = Protocol(ws_transport)
            inst_cont = InstrumentController()
            
            # Get possible parameters
            await protocol.send_command(protocol.Commands.GET_POSSIBLE_PARAMS)
            print('Get params message was sent')
            cmd, payload = await protocol.receive_command()
            print(f'Command: {cmd.name}\nPayload:{payload}')

            # Subscribe for scans
            await protocol.send_command(protocol.Commands.SUBSCRIBE_TO_SCANS)
            
            # Send start command
            await protocol.send_command(protocol.Commands.START_SCAN_TX)
            rx_in_progress = True
            while rx_in_progress:
                try:
                    cmd, payload = await protocol.receive_command()
                    if (protocol.Commands.FINISHED_SCAN_TX == cmd):
                        await protocol.send_command(protocol.Commands.SHUT_DOWN_SERVER)
                        print('Shutting down server...')
                except ws.exceptions.ConnectionClosed:
                    print('WebSocket connection closed. '
                          'Shutting down application....')
                    rx_in_progress = False
        

if __name__ == "__main__":
    client = ThermoMockClient()
    args = client.parse_client_arguments()
    print(f'Selected algorithm: {args.alg}')
    print(f'Selected sub-command: {args.command}')
    if ('real' == args.command):
        main = client.main_real
    elif ('mock' == args.command):
        main = client.main_mock
    asyncio.get_event_loop().run_until_complete(main(args))