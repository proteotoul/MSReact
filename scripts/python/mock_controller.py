import time
import os
import subprocess
from subprocess import Popen, CREATE_NEW_CONSOLE
from instrument_controller import InstrumentController

class MockController(InstrumentController):
    DEFAULT_URI = f'ws://localhost:4649/SWSS'
    DEFAULT_RAW_FILE_LIST = ["D:\\dev\\thermo-mock\\ThermoMock\\ThermoMockTest\\Data\\Excluded\\OFPBB210611_06.raw"]
    DEFAULT_SCAN_INTERVAL = 1
    MOCK_SERVER_PATH = ['D:\\dev\\thermo-mock\\ThermoMock\\ThermoMock\\bin\\Debug\\net5.0\\ThermoMock.exe ']

    def __init__(self, 
                 protocol,
                 algo_sync,
                 acq_cont,
                 uri=DEFAULT_URI,
                 raw_file_list = DEFAULT_RAW_FILE_LIST, 
                 scan_interval = DEFAULT_SCAN_INTERVAL):
        self.uri = uri
        self.raw_file_list = raw_file_list
        self.scan_interval = scan_interval
        super().__init__(protocol, algo_sync, acq_cont)
        # Continue updating MockController so it is implementing a full instrument controller too
        
    def create_mock_server(self):
        msg = self.MOCK_SERVER_PATH + ['mock'] + \
              [", ".join(self.raw_file_list)] + \
              [str(self.scan_interval)]
        self.mock_proc = Popen(msg, creationflags=CREATE_NEW_CONSOLE)
        
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
    
    async def set_ms_scan_tx_level(self, scan_level_range):
        if scan_level_range[0] <= scan_level_range[1]:
            if scan_level_range[0] != scan_level_range[1]:
                print('Setting ms scan transfer level to between ' 
                      f'MS{scan_level_range[0]} and MS{scan_level_range[1]}')
            else:
                print(f'Setting ms scan transfer level to MS{scan_level_range[0]}')
            await self.proto.send_message(self.proto.MessageIDs.SET_MS_SCAN_LVL,
                                          scan_level_range)
    
    async def request_shut_down_server(self):
        print('Shutting down mock server')
        await self.proto.send_message(self.proto.MessageIDs.SHUT_DOWN_MOCK_SERVER)

if __name__ == "__main__":
    mock_controller = MockController()
    mock_controller.create_mock_server()
    time.sleep(5)
    mock_controller.terminate_mock_server()