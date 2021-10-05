import msgpack
import transport_layer
from enum import IntEnum

class Transport:
    """
    A class providing transport functionalities, including transport protocol,
    serializing and deserializing messages.

    ...

    Attributes
    ----------
    transport_layer : TransportLayer
       TransportLayer type to use for communication with the server
        
    Methods
    -------
    connect_to_uri(uri)
        Connects to a uri using WebSocket protocol
    disconnect_from_uri()
        Disconnects from uri
    listen()
        Listens for messages over the WebSocket protocol
    send(message)
        Sends messages over the WebSocket protocol
    """
    class Commands(IntEnum):
        START_SCAN_TX           = 1
        STOP_SCAN_TX            = 2
        SCAN_TX                 = 3
        FINISHED_SCAN_TX        = 4
        SHUT_DOWN_SERVER        = 5
        CUSTOM_SCAN             = 6
        GET_POSSIBLE_PARAMS     = 7
        POSSIBLE_PARAMS         = 8
        SUBSCRIBE_TO_SCANS      = 9
        UNSUBSCRIBE_FROM_SCANS  = 10
    
    def __init__(self, transport_layer):
        self._tl = transport_layer
        if (self._tl.state == self._tl.TL_STATE_DISCONNECTED):
            self._tl.connect(self._tl.uri)
        
    async def send_command(self, cmd, payload = None):
        
        if (cmd in self.Commands):
            if (None == payload):
                await self._tl.send(cmd.to_bytes(1, 'big'))
            else:
                msg = cmd.to_bytes(1, 'big') + msgpack.packb(payload)
                await self._tl.send(msg)
        else:
            #TODO - Exception
            pass
    
    async def receive_command(self):
        msg = await self._tl.receive()
        # Parse commands
        cmd = self.Commands(msg[0])
        payload = None
        if ((self.Commands.SCAN_TX == cmd) or
            (self.Commands.POSSIBLE_PARAMS == cmd)):
            payload = msgpack.unpackb(msg[1:])
            
        return (cmd, payload)