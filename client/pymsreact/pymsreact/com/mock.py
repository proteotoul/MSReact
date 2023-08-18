import logging
import time
import os
import subprocess
from subprocess import Popen, CREATE_NEW_CONSOLE
from .instrument import InstrumentClient

class MockClient(InstrumentClient):
    '''
    This module is responsible for creating and managing a mock server through 
    the protocol. 

    ...

    Attributes
    ----------
    protocol: BaseProtocol
        Protocol to use for the communication with the server
        
    app_cb : func
        Callback function to forward messages to the application from the 
        InstrumentClient
    
    '''
    DEFAULT_URI = f'ws://localhost:4649/SWSS'
    DEFAULT_RAW_FILE_LIST = '\\data\\small2.raw'
    DEFAULT_SCAN_INTERVAL = 1
    # TODO - The path to the executable should be updated once the pulling of 
    #        latest server executable is implemented.
    MOCK_SERVER_PATH = '\\tools\\mock\\net48\\MSReactServer.exe'

    def __init__(self, 
                 protocol,
                 app_cb):
        """
        Parameters
        ----------
        protocol: BaseProtocol
            Protocol to use for the communication with the server.
        app_cb : func
            Callback function to forward messages to the application from the 
            InstrumentClient.
        """         
                 
        self.raw_file_list = None
        self.scan_interval = None
        super().__init__(protocol, app_cb)
        self.logger = logging.getLogger(__name__)
        # Continue updating MockClient so it is implementing a full
        # instrument controller too
        
    def create_mock_server(self,
                           raw_file_list = None,
                           scan_interval = DEFAULT_SCAN_INTERVAL):
        """Creates a mock server with the given parameters.

        Parameters
        ----------
        raw_file_list : list
            List of strings with the full path and name of the raw files to
            "replayed" by the mock.
        scan_interval : int
            Interval in milliseconds between two transmitted scans from the 
            mock server.
        """
        curent_dir = os.getcwd()
        self.raw_file_list = ([curent_dir + self.DEFAULT_RAW_FILE_LIST] 
                              if raw_file_list is None else raw_file_list)
        self.scan_interval = scan_interval
        
        mock_server_path = curent_dir + self.MOCK_SERVER_PATH
        msg = [mock_server_path] + ['mock'] + \
              [", ".join(self.raw_file_list)] + \
              [str(self.scan_interval)]
        self.mock_proc = Popen(msg, creationflags=CREATE_NEW_CONSOLE)
        
    def terminate_mock_server(self):
        """Terminates the mock server. Note: This shuts down the process that 
           runs the mock server."""
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
        """Requests the mock server to send only ms scans that are within the 
           given scan_level_range.

        Parameters
        ----------
        scan_level_range : list
            List of integers. The mock server will transfer scans from the raw 
            file that are within the scan level range. E.g.: If scan_level_range
            is [1,2], the mock server will transfer scans that are MS1 and MS2. 
            If the scan_level_range is [1,1] the mock server will transfer only
            MS1 scans to the client.
        """
        if scan_level_range[0] <= scan_level_range[1]:
            if scan_level_range[0] != scan_level_range[1]:
                self.logger.info('Setting ms scan transfer interval to between ' 
                            f'MS{scan_level_range[0]} and MS{scan_level_range[1]}')
            else:
                self.logger.info(f'Setting ms scan transfer level to MS{scan_level_range[0]}')
            await self.proto.send_message(self.proto.MessageIDs.SET_MS_SCAN_LVL_CMD,
                                          scan_level_range)
    
    async def request_shut_down_server(self):
        """Requests to shut down the mock server by transmitting a shut down 
           request to the mock."""
        self.logger.info('Shutting down mock server')
        await self.proto.send_message(self.proto.MessageIDs.SHUT_DOWN_MOCK_SERVER_CMD)