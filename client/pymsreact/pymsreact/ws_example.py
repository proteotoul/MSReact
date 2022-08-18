import asyncio
import time
import websockets


class WebSocketExample:

    END_OF_BROADCAST = "END OF BROADCAST"
    def __init__(self, port):
        self.port = port
        self.listening = False
        self.start_time = 0

    async def connect_and_listen(self):
        uri = f'ws://localhost:{self.port}/SWSS'
        async with websockets.connect(uri) as websocket:
            print('Connection succeeded')
            self.listening = True
            # self.start_time = time.time()
            counter = 0
            while self.listening:
                # await websocket.send(f'Round {counter}')
                message = await websocket.recv()
                print(f'< {message} >')
                # counter += 1
                # time.sleep(0.5)
                # if ((time.time() - self.start_time) > 30):
                    # self.listening = False

                if (message == self.END_OF_BROADCAST):
                    self.listening = False

if __name__ == "__main__":

    ws_example = WebSocketExample(4649)
    asyncio.get_event_loop().run_until_complete(ws_example.connect_and_listen())
