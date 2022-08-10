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
        
        # Get possible parameters
        await protocol.send_message(protocol.MessageIDs.GET_POSSIBLE_PARAMS)
        print('Get params message was sent')
        msg, payload = await protocol.receive_message()
        print(f'Message: {msg.name}\nPayload:{payload}')

        # Subscribe for scans
        await protocol.send_message(protocol.MessageIDs.SUBSCRIBE_TO_SCANS)
        
        # Send start message
        await protocol.send_message(protocol.MessageIDs.START_ACQ)
        rx_in_progress = True
        while rx_in_progress:
            try:
                msg, payload = await protocol.receive_message()
                #await protocol.send_message(protocol.MessageIDs.CUSTOM_SCAN, custom_scan)
                if ((payload != None) and (payload['CentroidCount'] == 0)):
                    print('Received MS2 scan.')
                    print(f'Message: {msg.name}\nPayload:{payload}')
                if (protocol.MessageIDs.FINISHED_ACQ_EVT == msg):
                    await protocol.send_message(protocol.MessageIDs.SHUT_DOWN_MOCK_SERVER_CMD)
                    print('Shutting down server...')
            except ws.exceptions.ConnectionClosed:
                print('WebSocket connection closed. '
                      'Shutting down application....')
                rx_in_progress = False
                


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())