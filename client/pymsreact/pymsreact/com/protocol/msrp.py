import msgpack
from enum import IntEnum
from .base import BaseProtocol, ProtocolErrors, ProtocolException
from ..transport.base import TransportException
import logging

class MSReactProtocol(BaseProtocol):
    """
    A class providing protocol functionalities, including message protocol,
    serializing and deserializing messages.

    ...

    Attributes
    ----------
    PROTOCOL_VERSION : string
        Contains the version of the protocol in "vX.Y" format
    MessageIDs : IntEnum
        Enumerates the implemented messages in this version of the protocol. 
        IMPORTANT: The GET_VERSION message always has to be implemented
    transport_layer : BaseTransport
       BaseTransport type to use for communication with the server
        
    Methods
    -------
    send_message(message)
        Sends messages over the WebSocket protocol
    receive_message()
        Waits for a message to be received
    """
    PROTOCOL_VERSION = 'v0.1'
    
    class MessageIDs(IntEnum):
    
        # Communication message group
        OK_RSP                      = 0
        ERROR_RSP                   = 1
        ERROR_EVT                   = 2
        GET_SERVER_SW_VER_CMD       = 3
        SERVER_SW_VER_RSP           = 4
        GET_SERVER_PROTO_VER_CMD    = 5
        SERVER_PROTO_VER_RSP        = 6
        GET_ACQ_RAW_FILE_NAME       = 7
        ACQ_RAW_FILE_NAME_RSP       = 8
        
        # Instrument message group
        GET_AVAILABLE_INSTR_CMD     = 20
        AVAILABLE_INSTR_RSP         = 21
        GET_INSTR_TYPE_CMD          = 22
        INSTR_TYPE_RSP              = 23
        GET_INSTR_STATE_CMD         = 24
        INSTR_STATE_RSP             = 25
        SELECT_INSTR_CMD            = 26
        DESELECT_INSTR_CMD          = 27

        # Acquisition message group
        CONFIG_ACQ_CMD              = 100
        START_ACQ_CMD               = 101
        STOP_ACQ_CMD                = 102
        STARTED_ACQ_EVT             = 103
        FINISHED_ACQ_EVT            = 104
        SUBSCRIBE_TO_SCANS_CMD      = 105
        SCAN_EVT                    = 106
        UNSUBSCRIBE_FROM_SCANS_CMD  = 107
        GET_POSSIBLE_PARAMS_CMD     = 108
        POSSIBLE_PARAMS_RSP         = 109
        REQ_CUSTOM_SCAN_CMD         = 110
        CANCEL_CUSTOM_SCAN_CMD      = 111
        SET_REPEATING_SCAN_CMD      = 112
        CLEAR_REPEATING_SCAN_CMD    = 113
        UPDATE_DEF_SCAN_PARAMS_CMD  = 114
        GET_LAST_ACQ_FILE_CMD       = 115
        LAST_ACQ_FILE_RSP           = 116

        # Mock message group 
        SET_MS_SCAN_LVL_CMD         = 200
        SHUT_DOWN_MOCK_SERVER_CMD   = 201
    
    def __init__(self, transport_layer):
        self.tl = transport_layer
        self.logger = logging.getLogger(__name__)
        
    async def connect(self, address = None):
        return await self.tl.connect(address)
        
    async def disconnect(self):
        await self.tl.disconnect()
        
    async def send_message(self, msg, payload = None):
        if (msg in self.MessageIDs):
            try:
                msg_packed = msg.to_bytes(1, 'big')
                if None != payload:
                    msg_packed = msg_packed + msgpack.packb(payload)
                await self.tl.send(msg_packed)
            except TransportException as tex:
                raise ProtocolException("Error while trying to send message.", 
                                        ProtocolErrors.TRANSPORT_ERROR) from tex
            except Exception as ex:
                raise ProtocolException("Error while trying send message.",
                                        ProtocolErrors.MESSAGE_PACKING_ERROR) from ex
        else:
            raise ProtocolException("Sending message failed: Incorrect message ID",
                                    ProtocolErrors.MESSAGE_PACKING_ERROR)
    
    async def receive_message(self):
        msg_id = self.MessageIDs.ERROR_EVT
        payload = None
        try:
            msg = await self.tl.receive()
            # Parse messages
            msg_id = self.MessageIDs(msg[0])
            
            if (1 < len(msg)):
                payload = msgpack.unpackb(msg[1:])
        except TransportException as tex:
            # Do not raise exception, an ERROR_EVT will be propagated to 
            # to the higher level.
            self.logger.error("Error while trying to receive message: " 
                              + f"{tex}")
        except Exception as ex:
            raise ProtocolException("Error while trying parsing received message.",
                                    ProtocolErrors.MESSAGE_PARSING_ERROR) from ex
        return (msg_id, payload)
        