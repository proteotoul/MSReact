import time
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

        # Subscribe for scans
        await transport.send_command(transport.Commands.SUBSCRIBE_TO_SCANS)
        
        # Send start command
        rx_in_progress = True
        keep_being_notified = True
        i = 0
        while rx_in_progress:
            try:
                cmd, payload = await transport.receive_command()
                print(f'Command: {cmd.name}\n')
                if (i <  5):
                    i += 1
                elif keep_being_notified:
                    keep_being_notified = False
                    await transport.send_command(transport.Commands.UNSUBSCRIBE_FROM_SCANS)
                else:
                    pass
            except ws.exceptions.ConnectionClosed:
                print('WebSocket connection closed. '
                      'Shutting down application....')
                rx_in_progress = False
                


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())