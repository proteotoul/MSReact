import asyncio
import websockets as ws
import ws_iface_exception as wsie
from transport import Transport
from transport_layer import TransportLayer
from ws_iface import WebSocketInterface

async def main():
    uri = f'ws://localhost:4649/SWSS'
    async with WebSocketInterface(uri) as ws_iface:
        transport = Transport(ws_iface)
        await transport.send_command(transport.Commands.START_SCAN_TX)
        rx_in_progress = True
        while rx_in_progress:
            try:
                cmd, payload = await transport.receive_command()
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