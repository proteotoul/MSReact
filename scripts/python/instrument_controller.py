import asyncio
from multiprocessing import Queue
from protocol import Protocol

class InstrumentController:
    '''
    Parameters
    ----------
    
    '''
    def __init__(self, transport, protocol, received_scan_queue, requested_scan_queue):
        self.transport = transport
        self.proto = protocol
        self.rec_scan_q = received_scan_queue
        self.req_scan_q = requested_scan_queue
        self.listening_for_scans = False
        
    async def connect_to_instrument(self, uri):
        await self.transport.connect(uri)
        
    async def disconnect_from_instrument():
        await self.transport.disconnect()
        
    async def get_protocol_version_async(self):
        print('Getting protocol version')
        await self.proto.send_command(self.proto.Commands.GET_VERSION)
        cmd, payload = await self.proto.receive_command()
        if (self.proto.Commands.VERSION == cmd):
            print(f'Received version: {payload}')
        else:
            pass
            # Raise exception
        return payload
        
    async def get_possible_params_async(self):
        print('Getting possible parameters for requesting scans...')
        await self.proto.send_command(self.proto.Commands.GET_POSSIBLE_PARAMS)
        cmd, payload = await self.proto.receive_command()
        if (self.proto.Commands.POSSIBLE_PARAMS != cmd):
            # TODO - raise exception
            print("Response was not POSSIBLE_PARAMS command.")
        return payload
        
    async def request_scan_async(self, parameters):
        print(f'Requesting scans with the following parameters:\n{parameters}')
        await self.proto.send_command(self.proto.Commands.CUSTOM_SCAN, 
                                      parameters)
        
    async def subscribe_to_scans_async(self):
        print('Subscribing for scans.')
        await self.proto.send_command(self.proto.Commands.SUBSCRIBE_TO_SCANS)
    
    async def unsubscribe_from_scans_async(self):
        print('Unsubscribing from scans.')
        await self.proto.send_command(self.proto.Commands.UNSUBSCRIBE_FROM_SCANS)
        
    async def start_listening_for_scans(self):
        print('Start listening for scans')
        self.listening_for_scans = True
        while self.listening_for_scans:
            cmd, payload = await self.proto.receive_command()
            if (self.proto.Commands.FINISHED_SCAN_TX == cmd):
                self.listening_for_scans = False
            elif (self.proto.Commands.SCAN_TX == cmd):
                self.rec_scan_q.put(payload)
            else:
                # TODO - raise exception
                pass
    
    # This might be better moved to the mock controller    
    async def mock_start_scan_tx_async(self):
        print('Start transferring scans from the raw file by the mock')
        await self.proto.send_command(self.proto.Commands.START_SCAN_TX)
    
    async def mock_stop_scan_tx_async(self):
        print('Stop transferring scans from the raw file by the mock')
        await self.proto.send_command(self.proto.Commands.STOP_SCAN_TX)
        
    async def mock_shut_down_server_async(self):
        print('Shutting down mock server')
        await self.proto.send_command(self.proto.Commands.SHUT_DOWN_SERVER)
        
    def run_async_as_sync(self, coroutine):
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(coroutine())
        return result
        
    