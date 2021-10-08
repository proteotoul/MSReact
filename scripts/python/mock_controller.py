import asyncio
import os
from subprocess import Popen, CREATE_NEW_CONSOLE

class MockController:
    DEFAULT_URI = f'ws://localhost:4649/SWSS'
    DEFAULT_RAW_FILE_LIST = ["D:\\dev\\thermo-mock\\ThermoMock\\ThermoMockTest\\Data\\Excluded\\OFPBB210611_06.raw"]
    DEFAULT_SCAN_INTERVAL = 1
    MOCK_CMD_BEGIN = \
        'start /wait cmd /c D:\\dev\\thermo-mock\\ThermoMock\\ThermoMock\\bin\\Debug\\net5.0\\ThermoMock.exe '
    MOCK_NON_BLOCK_CMD_BEGIN = \
        ['cmd', '/c', 'D:\\dev\\thermo-mock\\ThermoMock\\ThermoMock\\bin\\Debug\\net5.0\\ThermoMock.exe ']

    def __init__(self, 
                 uri=DEFAULT_URI, 
                 raw_file_list = DEFAULT_RAW_FILE_LIST, 
                 scan_interval = DEFAULT_SCAN_INTERVAL):
        self.uri = uri
        self.raw_file_list = raw_file_list
        self.scan_interval = scan_interval 
        
    def run_mock(self):
        cmd = self.MOCK_CMD_BEGIN + ' '.join(raw_file_list) + str(scan_interval)
        os.system(cmd)
        
    def run_mock_nonblock(self):
        cmd = self.MOCK_NON_BLOCK_CMD_BEGIN + self.raw_file_list + [str(self.scan_interval)]
        return Popen(cmd, creationflags=CREATE_NEW_CONSOLE)
        
    async def run_mock_async(self):
    # TODO - This is not working yet
        cmd = self.MOCK_CMD_BEGIN + ' '.join(raw_file_list) + str(scan_interval)
        proc = await asyncio.create_subprocess_shell(
            cmd,
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