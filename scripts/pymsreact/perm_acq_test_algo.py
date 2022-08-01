from algorithm import Algorithm
from acquisition import Acquisition, AcquisitionStatusIds
from tribid_instrument import ThermoTribidInstrument
import acquisition_workflow as aw
import json
import logging
import time
import csv

# Acquisition settings
ACQUISITION_WORKFLOW = aw.Permanent
ACQUISITION_PARAMETER = None
SINGLE_PROCESSING_DELAY = 0
WAIT_FOR_CONTACT_CLOSURE = False
RAW_FILE_NAME = "permanent_test.RAW"
SAMPLE_NAME = "-"
COMMENT = "This test is checking whether permanent acquisition " + \
          "can be initiated and terminated from MSReactor."
          
# Acquisition duration in seconds
ACQUISITION_DURATION = 3

# Sleep interval between checking if acquisition is stopped in seconds
SLEEP_INTERVAL = 0.1

# Timeout on waiting for acquisition to finish in seconds
ACQUISITION_STOP_TIMEOUT = 5

class TestPermanentAcquisition(Acquisition):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = 'Test_permanent_acquisition'
        self.instrument = ThermoTribidInstrument()
        
    def pre_acquisition(self):
        self.logger.info('Executing pre-acquisition steps.')
        # It is fine to update the settings in the pre_acquisition 
        # since the settings are forwarded to the server between
        # pre and intra acquisition.
        datetime = time.strftime("%Y_%m_%d_%H_%M_")
        self.settings.update_settings(workflow = ACQUISITION_WORKFLOW,
                                      workflow_param = ACQUISITION_PARAMETER,
                                      single_processing_delay = SINGLE_PROCESSING_DELAY,
                                      wait_for_contact_closure = WAIT_FOR_CONTACT_CLOSURE,
                                      raw_file_name = datetime + RAW_FILE_NAME,
                                      sample_name = SAMPLE_NAME,
                                      comment = COMMENT)
        
    def intra_acquisition(self):
        self.logger.info('Executing intra-acquisition steps.')
        start_time = time.time()
        
        while (((time.time() - start_time) < ACQUISITION_DURATION) and
               (AcquisitionStatusIds.ACQUISITION_RUNNING == self.get_acquisition_status())):
            scan = self.fetch_received_scan()
            if (scan is not None):
                self.logger.info('Received scan with scan number: ' + 
                                 f'{scan["ScanNumber"]} Centroid count :' + 
                                 str(scan["CentroidCount"]))
            else:
                pass
                
        if (AcquisitionStatusIds.ACQUISITION_RUNNING == self.get_acquisition_status()):
            self.logger.info('Request acquisition finish')
            self.request_acquisition_stop()
            
            success = True
            start_time = time.time()
            while AcquisitionStatusIds.ACQUISITION_RUNNING == self.get_acquisition_status():
                time.sleep(SLEEP_INTERVAL)
                if time.time() - start_time > ACQUISITION_STOP_TIMEOUT:
                    success = False
                    break
            if success:
                self.logger.info('Permanent acquisition test succeeded.')
            else:
                self.logger.info('Permanent acquisition test failed: ' +
                                 'Acquisition did not stop within ' +
                                 f'{ACQUISITION_STOP_TIMEOUT} seconds from requesting it.')
        else:
            self.logger.info('Permanent acquisition test failed: ' + 
                             'Acquisition finished before the planned acquisition duration.')
        self.logger.info('Finishing intra acquisition.')
    
    def post_acquisition(self):
        self.logger.info('Executing post-acquisition steps.')

class PermAcqTestAlgorithm(Algorithm):

    """Method - TODO: Create default method based on real method."""
    DEFAULT_ACQUISITION_METHODS = {}
    """Sequence - TODO: Create default method based on real method."""
    DEFAULT_ACQUISITION_SEQUENCE = {}
    """Cycle interval - TODO: This is only for mock."""
    CYCLE_INTERVAL = 10
    """Name of the algorithm. This is a mandatory field for the algorithms"""
    ALGORITHM_NAME = 'perm_acq_test'
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
        self.acquisition_sequence = [ TestPermanentAcquisition ]
        self.logger = logging.getLogger(__name__)
        
if __name__ == "__main__":
    algo = PermAcqTestAlgorithm()
    algo.pre_acquisition()
    algo.intra_acquisition()
    algo.post_acquisition()