# Entry point for pymsreact

import asyncio
import msreact_client
import pathlib
import traceback

def main():
    # Create output and log folder if it doesn't exist yet
    pathlib.Path('.\\output\\log').mkdir(parents=True, exist_ok=True)
    client = msreact_client.MSReactClient()
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

if __name__ == "__main__":
    main()