import time
import os
import subprocess
from subprocess import Popen, CREATE_NEW_CONSOLE

class MockController:
    DEFAULT_URI = f'ws://localhost:4649/SWSS'
    DEFAULT_RAW_FILE_LIST = ["D:\\dev\\thermo-mock\\ThermoMock\\ThermoMockTest\\Data\\Excluded\\OFPBB210611_06.raw"]
    DEFAULT_SCAN_INTERVAL = 1
    MOCK_SERVER_PATH = ['D:\\dev\\thermo-mock\\ThermoMock\\ThermoMock\\bin\\Debug\\net5.0\\ThermoMock.exe ']

    def __init__(self, 
                 protocol,
                 uri=DEFAULT_URI,
                 raw_file_list = DEFAULT_RAW_FILE_LIST, 
                 scan_interval = DEFAULT_SCAN_INTERVAL):
        self.uri = uri
        self.raw_file_list = raw_file_list
        self.scan_interval = scan_interval
        self.proto = protocol
        
    def create_mock_server(self):
        print(type(self.raw_file_list))
        cmd = self.MOCK_SERVER_PATH + \
              [", ".join(self.raw_file_list)] + \
              [str(self.scan_interval)]
        self.mock_proc = Popen(cmd, creationflags=CREATE_NEW_CONSOLE)
        
    def terminate_mock_server(self):
        ret_code = self.mock_proc.poll()
        if (ret_code != None):
            print(f'Mock server terminated with return code: {ret_code}')
        else:
            self.mock_proc.terminate()
            ret_code = self.mock_proc.poll()
            if (ret_code == None):
                print(f'Mock server did not terminate properly. \
                       Please close the Mock server window.')
                       
    async def start_scan_tx(self):
        print('Start transferring scans from the raw file by the mock')
        await self.proto.send_command(self.proto.Commands.START_SCAN_TX)
    
    async def stop_scan_tx(self):
        print('Stop transferring scans from the raw file by the mock')
        await self.proto.send_command(self.proto.Commands.STOP_SCAN_TX)
        
    async def request_shut_down_server(self):
        print('Shutting down mock server')
        await self.proto.send_command(self.proto.Commands.SHUT_DOWN_SERVER)

if __name__ == "__main__":
    mock_controller = MockController()
    mock_controller.create_mock_server()
    time.sleep(5)
    mock_controller.terminate_mock_server()