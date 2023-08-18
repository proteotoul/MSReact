from algorithms.manager.algorithm import Algorithm
from algorithms.manager.acquisition import Acquisition, AcqStatIDs
import algorithms.manager.ms_instruments.mock_instrument as mi
import algorithms.manager.ms_instruments.tribrid_instrument as ti
import logging
import time

class MonitorAcquisition(Acquisition):
    instruments = [mi.MockInstrument, ti.ThermoTribridInstrument]
    
    def __init__(self, *args):
        super().__init__(*args)
        self.name = 'Monitor_algo_first_acquisition'
        
    def pre_acquisition(self):
        self.logger.info('Executing pre-acquisition steps.')
        
    def intra_acquisition(self):
        self.logger.info('Executing intra-acquisition steps.')
        while AcqStatIDs.ACQUISITION_RUNNING == self.get_acquisition_status():
            scan = self.fetch_received_scan()
            if (scan is not None):
                self.logger.info('Received scan with scan number: ' + 
                                 f'{scan["ScanNumber"]} Centroid count :' + 
                                 str(scan["CentroidCount"]))
            else:
                pass
        self.logger.info('Finishing intra acquisition.')
    
    def post_acquisition(self):
        self.logger.info('Executing post-acquisition steps.')

class MonitorAlgorithm(Algorithm):
    """Algorithm implementing simple monitoring"""

    """Method - TODO: Create default method based on real method."""
    DEFAULT_ACQUISITION_METHODS = {}
    """Sequence - TODO: Create default method based on real method."""
    DEFAULT_ACQUISITION_SEQUENCE = {}
    """Cycle interval - TODO: This is only for mock."""
    CYCLE_INTERVAL = 10
    """Name of the algorithm. This is a mandatory field for the algorithms"""
    ALGORITHM_NAME = 'monitor'
    '''Level of MS scans that are transferred from the mock server.
       eg. - 1 means only MS scans are transferred from the mock server. 
           - 2 means MS and MS2 scans are transferred from the mock server
       Note - In case of custom scan requests the requested scan will be 
              transferred from the mock server not regarding the scan level,
              if it's available in the raw file.
       Note2 - This could be different in each acquisition.'''
    TRANSMITTED_SCAN_LEVEL = [1, 2]
    
    def __init__(self):
        super().__init__()
        self.acquisition_methods = self.DEFAULT_ACQUISITION_METHODS
        self.acquisition_sequence = [ MonitorAcquisition ]
        self.logger = logging.getLogger(__name__)
                