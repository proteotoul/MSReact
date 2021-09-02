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
    
    def __init__(self, transport_layer):
        self._tl = transport_layer
        if (self._tl.state == self._tl.TL_STATE_DISCONNECTED):
            self._tl.connect(self._tl.uri)
        
    async def send_command(self, cmd, payload = None):
        if (self.Commands.START_SCAN_TX == cmd):
            await self._tl.send(cmd.to_bytes(1, 'big'))
        elif (self.Commands.STOP_SCAN_TX == cmd):
            await self._tl.send(cmd.to_bytes(1, 'big'))
        elif (self.Commands.SHUT_DOWN_SERVER == cmd):
            await self._tl.send(cmd.to_bytes(1, 'big'))
        elif (self.Commands.CUSTOM_SCAN == cmd):
            msg = cmd.to_bytes(1, 'big') + msgpack.packb(payload)
            await self._tl.send(msg)
        elif (self.Commands.GET_POSSIBLE_PARAMS == cmd):
            await self._tl.send(cmd.to_bytes(1, 'big'))
        else:
            pass
            # TODO - Throw an exception
    
    async def receive_command(self):
        msg = await self._tl.receive()
        # Parse commands
        cmd = self.Commands(msg[0])
        payload = None
        if (self.Commands.SCAN_TX == cmd):
            payload = msgpack.unpackb(msg[1:])
            
        return (cmd, payload)