import asyncio
import websockets as ws
import ws_transport_exception as wste
from protocol import Protocol
from transport_layer import TransportLayer
from ws_transport import WebSocketTransport

async def main():
    uri = f'ws://localhost:4649/SWSS'
    custom_scan = {"Precursor_mz" : "753.8076782226562"}
    
    async with WebSocketTransport(uri) as ws_transport:
        protocol = Protocol(ws_transport)
        
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
                await protocol.send_command(protocol.Commands.CUSTOM_SCAN, custom_scan)
                if ((payload != None) and (payload['CentroidCount'] == 0)):
                    print('Received MS2 scan.')
                    print(f'Command: {cmd.name}\nPayload:{payload}')
                if (protocol.Commands.FINISHED_SCAN_TX == cmd):
                    await protocol.send_command(protocol.Commands.SHUT_DOWN_SERVER)
                    print('Shutting down server...')
            except ws.exceptions.ConnectionClosed:
                print('WebSocket connection closed. '
                      'Shutting down application....')
                rx_in_progress = False
                


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())