import argparse
import asyncio
import websockets as ws
import ws_iface_exception as wsie
from transport import Transport
from transport_layer import TransportLayer
from ws_iface import WebSocketInterface
from algorithm import Algorithm
from algorithm_list import algorithm_list

VERSION = 'v0.1'

async def main(args):

    print('The entered arguments are:')
    print(f'Selected algorithm: {args.alg}')
    print(f'Selected sub-command: {args.command}')
    if ('real' == args.command):
        print(f'Entered address: {args.address}')
    elif ('mock' == args.command):
        print(f'Selected raw files: {args.raw_files}')
        print(f'Selected scan interval: {args.scan_interval}')
    

if __name__ == "__main__":
    
    # Top level parser
    parser = argparse.ArgumentParser(description='ThermoMock python client')
    parser.add_argument('-v', '--version', action='version', version = VERSION,
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
    # TODO - This won't be an input, but will be retreived from the middleware
    parser_real.add_argument('address',
                             help='address to the MSReactor server')
    
    # Parser for sub-command "mock"
    parser_mock = \
        subparsers.add_parser('mock', 
                              help='command to use mock instrument instead \
                              of a real instrument')
    parser_mock.add_argument('raw_files', nargs='+',
                             help='full path and name of the raw files to use \
                                   for the simulated acquisition in the \
                                   sequence of the real acquisition')
    parser_mock.add_argument('scan_interval',
                             help='interval between scans transmissions in \
                                   [ms], the time the algorithm has between \
                                   each scans to analyse the scan and decide \
                                   if it requests a custom scan')

    args = parser.parse_args()
    asyncio.get_event_loop().run_until_complete(main(args))