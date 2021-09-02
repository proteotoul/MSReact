import asyncio
import websockets as ws
import ws_iface_exception as wsie
from transport import Transport
from transport_layer import TransportLayer
from ws_iface import WebSocketInterface

async def main():
    uri = f'ws://localhost:4649/SWSS'
    custom_scan = {"Precursor_mz" : "753.8076782226562"}
    
    async with WebSocketInterface(uri) as ws_iface:
        transport = Transport(ws_iface)
        # Get possible parameters
        
        await transport.send_command(transport.Commands.GET_POSSIBLE_PARAMS)
        print('Get params message was sent')
        cmd, payload = await transport.receive_command()
        print(f'Command: {cmd.name}\nPayload:{payload}')

        # Send start command
        await transport.send_command(transport.Commands.START_SCAN_TX)
        rx_in_progress = True
        while rx_in_progress:
            try:
                cmd, payload = await transport.receive_command()
                await transport.send_command(transport.Commands.CUSTOM_SCAN, custom_scan)
                if ((payload != None) and (payload['CentroidCount'] == 0)):
                    print('Received MS2 scan.')
                    print(f'Command: {cmd.name}\nPayload:{payload}')
                if (transport.Commands.FINISHED_SCAN_TX == cmd):
                    await transport.send_command(transport.Commands.SHUT_DOWN_SERVER)
                    print('Shutting down server...')
            except ws.exceptions.ConnectionClosed:
                print('WebSocket connection closed. '
                      'Shutting down application....')
                rx_in_progress = False
                


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())