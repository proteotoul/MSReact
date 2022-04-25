import logging
import time
import os
import subprocess
from subprocess import Popen, CREATE_NEW_CONSOLE
from instrument_server_manager import InstrumentServerManager

class MockServerManager(InstrumentServerManager):
    DEFAULT_URI = f'ws://localhost:4649/SWSS'
    DEFAULT_RAW_FILE_LIST = ["D:\\dev\\ms-reactor\\ThermoMock\\ThermoMockTest\\Data\\Excluded\\OFPBB210611_06.raw"]
    DEFAULT_SCAN_INTERVAL = 1
    MOCK_SERVER_PATH = ['D:\\dev\\ms-reactor\\ThermoMock\\ThermoMock\\bin\\Debug\\net5.0\\ThermoMock.exe ']

    def __init__(self, 
                 protocol,
                 app_cb,
                 loop):
        self.raw_file_list = None
        self.scan_interval = None
        super().__init__(protocol, app_cb, loop)
        self.logger = logging.getLogger(__name__)
        # Continue updating MockServerManager so it is implementing a full
        # instrument controller too
        
    def create_mock_server(self,
                           raw_file_list = DEFAULT_RAW_FILE_LIST,
                           scan_interval = DEFAULT_SCAN_INTERVAL):
                           
        self.raw_file_list = raw_file_list
        self.scan_interval = scan_interval
        
        msg = self.MOCK_SERVER_PATH + ['mock'] + \
              [", ".join(self.raw_file_list)] + \
              [str(self.scan_interval)]
        self.mock_proc = Popen(msg, creationflags=CREATE_NEW_CONSOLE)
        
    def terminate_mock_server(self):
        self.raw_file_list = None
        self.scan_interval = None
    
        ret_code = self.mock_proc.poll()
        if (ret_code != None):
            self.logger.info(f'Mock server terminated with return code: {ret_code}')
        else:
            self.mock_proc.terminate()
            ret_code = self.mock_proc.poll()
            if (ret_code == None):
                self.logger.info('Mock server did not terminate properly.\n' +
                                 'Please close the Mock server window.')
    
    async def set_ms_scan_tx_level(self, scan_level_range):
        if scan_level_range[0] <= scan_level_range[1]:
            if scan_level_range[0] != scan_level_range[1]:
                self.logger.info('Setting ms scan transfer level to between ' 
                            f'MS{scan_level_range[0]} and MS{scan_level_range[1]}')
            else:
                self.logger.info(f'Setting ms scan transfer level to MS{scan_level_range[0]}')
            await self.proto.send_message(self.proto.MessageIDs.SET_MS_SCAN_LVL_CMD,
                                          scan_level_range)
    
    async def request_shut_down_server(self):
        self.logger.info('Shutting down mock server')
        await self.proto.send_message(self.proto.MessageIDs.SHUT_DOWN_MOCK_SERVER_CMD)

if __name__ == "__main__":
    mock_server_manager = MockServerManager()
    mock_server_manager.create_mock_server()
    time.sleep(5)
    mock_server_manager.terminate_mock_server()