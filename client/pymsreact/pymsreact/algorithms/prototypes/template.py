from algorithms.manager.algorithm import Algorithm
from algorithms.manager.acquisition import Acquisition, AcqStatIDs, ScanFields, CentroidFields
import algorithms.manager.ms_instruments.mock_instrument as mi
import algorithms.manager.ms_instruments.tribrid_instrument as ti
import algorithms.manager.acquisition_workflow as aw
import json
import logging
import time
from datetime import datetime
import csv

# Acquisition settings
ACQUISITION_WORKFLOW = aw.Listening
ACQUISITION_PARAMETER = None
SINGLE_PROCESSING_DELAY = 0
WAIT_FOR_CONTACT_CLOSURE = True
RAW_FILE_NAME = "template.RAW"
SAMPLE_NAME = "-"
COMMENT = "This a template acquisition."

class YourAcquisition(Acquisition):
    # Define on which instrument to use the acquisition on.
    instruments = [mi.MockInstrument, ti.ThermoTribridInstrument]
    
    def __init__(self, *args):
        super().__init__(*args)
        self.name = 'Your_Acquisition'
        
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
        while AcqStatIDs.ACQUISITION_RUNNING == self.get_acquisition_status():
            time.sleep(1)
        self.logger.info('Finishing intra acquisition. steps')
    
    def post_acquisition(self):
        self.logger.info('Executing post-acquisition steps.')

        

class YourAlgorithm(Algorithm):

    """Method - TODO: Create default method based on real method."""
    ACQUISITION_METHOD = {}
    """Sequence - TODO: Create default method based on real method."""
    ACQUISITION_SEQUENCE = [ YourAcquisition ]
    """Cycle interval - TODO: This is only for mock."""
    CYCLE_INTERVAL = 10
    """Name of the algorithm. This is a mandatory field for the algorithms"""
    ALGORITHM_NAME = 'your_algorithm'
    '''Level of MS scans that are transferred from the mock server.
       eg. - 1 means only MS scans are transferred from the mock server. 
           - 2 means MS and MS2 scans are transferred from the mock server
       Note - In case of custom scan requests the requested scan will be 
              transferred from the mock server not regarding the scan level,
              if it's available in the raw file.
       Note2 - This could be different in each acquisition.'''
    TRANSMITTED_SCAN_LEVEL = [1, 1]
    
    def __init__(self):
        super().__init__()
        self.acquisition_methods = self.ACQUISITION_METHOD
        self.acquisition_sequence = [ YourAcquisition ]
        self.configs = [ None ]
        self.logger = logging.getLogger(__name__)
        