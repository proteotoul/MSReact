import asyncio
import os
import subprocess
from subprocess import Popen, CREATE_NEW_CONSOLE
import websockets as ws
import ws_iface_exception as wsie
from transport import Transport
from transport_layer import TransportLayer
from ws_iface import WebSocketInterface

class MockController:
    DEFAULT_URI = f'ws://localhost:4649/SWSS'
    START_MOCK_CMD = \
        'start /wait cmd /c D:\\dev\\thermo-mock\\ThermoMock\\ThermoMock\\bin\\Debug\\net5.0\\ThermoMock.exe ' + \
        '"D:\\dev\\thermo-mock\\ThermoMock\\ThermoMockTest\\Data\\Excluded\\OFPBB210611_06.raw" 1'     
    START_MOCK_NON_BLOCK_CMD = \
            ['cmd', '/c', 'D:\\dev\\thermo-mock\\ThermoMock\\ThermoMock\\bin\\Debug\\net5.0\\ThermoMock.exe ',
            "D:\\dev\\thermo-mock\\ThermoMock\\ThermoMockTest\\Data\\Excluded\\OFPBB210611_06.raw", '1']

    def __init__(self, uri=DEFAULT_URI):
        self.uri = uri
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def run_mock(self):
        os.system(self.START_MOCK_CMD)
        
    def run_mock_nonblock(self):
        return Popen(self.START_MOCK_NON_BLOCK_CMD,
                     creationflags=CREATE_NEW_CONSOLE)
        
    async def run_mock_async(self):
    # TODO - This is not working yet
        proc = await asyncio.create_subprocess_shell(
            self.START_MOCK_CMD,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)          
        
        stdout, stderr = await proc.communicate()

        print(f'[ThermoMock exited with {proc.returncode}]')
        if stdout:
            print(f'[stdout]\n{stdout.decode()}')
        if stderr:
            print(f'[stderr]\n{stderr.decode()}')

if __name__ == "__main__":
    mock_controller = MockController()
    mock_controller.run_mock_nonblock()