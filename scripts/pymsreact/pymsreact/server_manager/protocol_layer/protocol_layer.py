#import ..transport_layer.transport_layer
from enum import IntEnum

class ProtocolLayer:
    """
    Abstract class for protocols

    ...

    Attributes
    ----------
    PROTOCOL_VERSION : string
        Contains the version of the protocol in "vX.Y" format
    MessageIDs : IntEnum
        Enumerates the implemented messages in this version of the protocol. 
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
    
    PROTOCOL_VERSION = 'v0.0'
    
    class MessageIDs(IntEnum):
        GET_VERSION             = 1
    
    def __init__(self, transport_layer):
        self.tl = transport_layer
        
    async def send_message(self, msg, payload = None):
        pass
    
    async def receive_message(self):
        msg = None
        payload = None     
        return (msg, payload)