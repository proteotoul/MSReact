import time
import asyncio
import websockets as ws
from msrp import MSReactProtocol
from base import BaseTransport
from websocket import WebSocketTransport

async def main():
    uri = f'ws://localhost:4649/SWSS'
    custom_scan = {"Precursor_mz" : "753.8076782226562"}
    
    async with WebSocketTransport(uri) as ws_transport:
        protocol = MSReactProtocol(ws_transport)

        # Subscribe for scans
        await protocol.send_command(protocol.MessageIDs.SUBSCRIBE_TO_SCANS)
        
        # Send start command
        rx_in_progress = True
        keep_being_notified = True
        i = 0
        while rx_in_progress:
            try:
                msg, payload = await protocol.receive_command()
                print(f'Command: {msg.name}\n')
                if (i <  5):
                    i += 1
                elif keep_being_notified:
                    keep_being_notified = False
                    await protocol.send_command(protocol.MessageIDs.UNSUBSCRIBE_FROM_SCANS)
                else:
                    pass
            except ws.exceptions.ConnectionClosed:
                print('WebSocket connection closed. '
                      'Shutting down application....')
                rx_in_progress = False
                


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())