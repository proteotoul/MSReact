import asyncio
from protocol import Protocol

class InstrumentController:
    '''
    Parameters
    ----------
    
    '''
    def __init__(self, protocol, process_scan):
        self.proto = protocol
        self.process_scan = process_scan
        self.listening_for_scans = False
        
    async def get_protocol_version(self):
        print('Getting protocol version')
        await self.proto.send_command(self.proto.Commands.GET_VERSION)
        cmd, payload = await self.proto.receive_command()
        if (self.proto.Commands.VERSION == cmd):
            print(f'Received version: {payload}')
        else:
            # Raise exception
        return payload
        
    async def get_possible_params(self):
        print('Getting possible parameters for requesting scans...')
        await self.proto.send_command(self.proto.Commands.GET_POSSIBLE_PARAMS)
        cmd, payload = await self.proto.receive_command()
        if (self.proto.Commands.POSSIBLE_PARAMS == cmd):
            print(f'Possible parameters:\n{payload}')
        else:
            # TODO - raise exception
            pass
        return payload
        
    async def request_scan(self, parameters):
        print(f'Requesting scans with the following parameters:\n{parameters}')
        await self.proto.send_command(self.proto.Commands.CUSTOM_SCAN, 
                                      parameters)
        
    async def subscribe_to_scans(self):
        print('Subscribing for scans.')
        await self.proto.send_command(self.proto.Commands.SUBSCRIBE_TO_SCANS)
        
    async def unsubscribe_from_scans(self):
        print('Unsubscribing from scans.')
        await self.proto.send_command(self.proto.Commands.UNSUBSCRIBE_FROM_SCANS)
        
    async def start_listening_for_scans(self):
        print('Start listening for scans')
        self.listening_for_scans = True
        while self.listening_for_scans:
            cmd, payload = await self.proto.receive_command()
            if (self.proto.Commands.FINISHED_SCAN_TX == cmd):
                self.listening_for_scans = False
            elif (self.proto.Commands.SCANT_TX == cmd):
                self.process_scan(payload)
            else:
                # TODO - raise exception
                pass
    
    # This might be better moved to the mock controller    
    async def mock_start_scan_tx(self):
        print('Start transferring scans from the raw file by the mock')
        await self.proto.send_command(self.proto.Commands.START_SCAN_TX)
        
    async def mock_stop_scan_tx(self):
        print('Stop transferring scans from the raw file by the mock')
        await self.proto.send_command(self.proto.Commands.STOP_SCAN_TX)
        
    async def mock_shut_down_server(self):
        print('Shutting down mock server')
        await self.proto.send_command(self.proto.Commands.SHUT_DOWN_SERVER)
        
    