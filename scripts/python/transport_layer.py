class TransportLayer:
    
    TL_STATE_DISCONNECTED = 0
    TL_STATE_CONNECTED = 1
    TL_STATE_RECEIVE = 2
    TL_STATE_SEND_MSG = 3

    def __init__(self, uri):
        self.state = TL_STATE_DISCONNECTED
        self.uri = uri
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    async def connect(self, uri):
        pass
    async def disconnect(self):
        pass
    async def send(self, msg):
        pass
    async def receive(self):
        pass