import msgpack
import transport_layer
from enum import IntEnum
from protocol_layer import ProtocolLayer

class Protocol(ProtocolLayer):
    """
    A class providing protocol functionalities, including message protocol,
    serializing and deserializing messages.

    ...

    Attributes
    ----------
    PROTOCOL_VERSION : string
        Contains the version of the protocol in "vX.Y" format
    Commands : IntEnum
        Enumerates the implemented commands in this version of the protocol. 
        IMPORTANT: The GET_VERSION command always has to be implemented
    transport_layer : TransportLayer
       TransportLayer type to use for communication with the server
        
    Methods
    -------
    send_command(message)
        Sends messages over the WebSocket protocol
    receive_command()
        Waits for a command to be received
    """
    PROTOCOL_VERSION = 'v0.1'
    
    class Commands(IntEnum):
        GET_VERSION             = 1
        VERSION                 = 2
        START_SCAN_TX           = 3
        STOP_SCAN_TX            = 4
        SCAN_TX                 = 5
        FINISHED_SCAN_TX        = 6
        SHUT_DOWN_SERVER        = 7
        CUSTOM_SCAN             = 8
        GET_POSSIBLE_PARAMS     = 9
        POSSIBLE_PARAMS         = 10
        SUBSCRIBE_TO_SCANS      = 11
        UNSUBSCRIBE_FROM_SCANS  = 12
    
    def __init__(self, transport_layer):
        self.tl = transport_layer
        
    async def send_command(self, cmd, payload = None):
        if (cmd in self.Commands):
            if (None == payload):
                await self.tl.send(cmd.to_bytes(1, 'big'))
            else:
                msg = cmd.to_bytes(1, 'big') + msgpack.packb(payload)
                await self.tl.send(msg)
        else:
            #TODO - Exception
            pass
    
    async def receive_command(self):
        msg = await self.tl.receive()
        # Parse commands
        cmd = self.Commands(msg[0])
        payload = None
        if ((self.Commands.SCAN_TX == cmd) or
            (self.Commands.POSSIBLE_PARAMS == cmd)):
            payload = msgpack.unpackb(msg[1:])
            
        return (cmd, payload)