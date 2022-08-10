from algorithms.manager.algorithm import Algorithm
from algorithms.manager.acquisition import Acquisition, AcquisitionStatusIds
from algorithms.manager.ms_instruments.tribid_instrument import ThermoTribidInstrument
import algorithms.manager.acquisition_workflow as aw
import json
import logging
import time
import csv
# imports for deisotoping
from utils.deisotoper_openms import DeisitoperOpenMS
from utils.deisotoper_msdeisotope import DeisitoperMSDeisotope
#import ms_deisotope
#from pyopenms import MSSpectrum, Deisotoper

# Acquisition settings
ACQUISITION_WORKFLOW = aw.Listening
ACQUISITION_PARAMETER = None

#ACQUISITION_WORKFLOW = aw.Method
# That location should be on the server computer for the moment
# TODO: Think about how to transfer file through websocket
#ACQUISITION_PARAMETER = 'D:\\dev\\ms-reactor\\top_n_test.meth'
SINGLE_PROCESSING_DELAY = 0
WAIT_FOR_CONTACT_CLOSURE = False
RAW_FILE_NAME = "top_n_test.RAW"
SAMPLE_NAME = "-"
COMMENT = "This test is checking whether top N method " + \
          "can be initiated and managed from MSReactor."

MZ_TOLERANCE = 0.0001 # Tolerance for the exclusion
NUMBER_OF_PEAKS = 15 # Number of precursors to select for MS2
EXCLUSION_TIME = 0.3333 # Exclusion time in minutes

class TopNAcquisition(Acquisition):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = 'Test_TopN_acquisition'
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
        scans = []
        deisotoper = DeisitoperOpenMS()
        # Alternatively other deisotoper can be selected as well
        # deisotoper = DeisitoperMSDeisotope()
        
        exclusion_list = []
        num_requests = 0
        num_received = 0
        
        while AcquisitionStatusIds.ACQUISITION_RUNNING == self.get_acquisition_status():
            scan = self.fetch_received_scan()
            
            if ((scan is not None) and (2 == scan["MSScanLevel"])):
                num_received = num_received + 1
            if ((scan is not None) and (1 == scan["MSScanLevel"])):
                self.logger.info(f'Received/Requested ratio = {num_received}/{num_requests}')
                num_received = 0
                num_requests = 0
                
                # Get current time
                current_retention_time = scan["RetentionTime"]
                
                # Remove expired centroids from the exclusion list
                cutoff = 0 # This assignment is necessary in case of empty exclusion list.
                for cutoff in range(len(exclusion_list)):
                    if abs(current_retention_time - exclusion_list[cutoff]["ExclusionTime"]) < EXCLUSION_TIME:
                        break
                exclusion_list = exclusion_list[cutoff:]
                        
                # Get centroids from the scan
                centroids = scan["Centroids"]
                
                # Do deisotoping
                centroids = deisotoper.deisotope_peaks(centroids)
                
                # Sort centroids by their intensity
                centroids.sort(key=lambda i: i["Intensity"], reverse=True)
                
                # TODO: This code might be written nicer and shorter with some list comprehension
                i = 0
                excl_list_buffer = []
                while ((i < len(centroids)) and (len(excl_list_buffer) != NUMBER_OF_PEAKS)):
                    not_excluded = True
                    for centroid_excl in exclusion_list:
                        if MZ_TOLERANCE > abs(centroids[i]["Mz"] - centroid_excl["Mz"]):
                            not_excluded = False # it is excluded
                            break
                    if not_excluded:            
                        self.request_custom_scan({"PrecursorMass": str(centroids[i]["Mz"]),
                                                  "ScanType": "MSn"})
                        centroid = centroids[i] | {"ExclusionTime" : current_retention_time}
                        excl_list_buffer.append(centroid)
                        num_requests = num_requests + 1
                    i = i + 1
                exclusion_list = exclusion_list + excl_list_buffer
                self.logger.info(f'Exclusion list length: {len(exclusion_list)}')
            else:
                pass    
        
        self.logger.info('Finishing intra acquisition.')
    
    def post_acquisition(self):
        self.logger.info('Executing post-acquisition steps.')
        

class TopNTestAlgorithm(Algorithm):

    """Method - TODO: Create default method based on real method."""
    DEFAULT_ACQUISITION_METHODS = {}
    """Sequence - TODO: Create default method based on real method."""
    DEFAULT_ACQUISITION_SEQUENCE = {}
    """Cycle interval - TODO: This is only for mock."""
    CYCLE_INTERVAL = 10
    """Name of the algorithm. This is a mandatory field for the algorithms"""
    ALGORITHM_NAME = 'top_n_test'
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
        self.acquisition_methods = self.DEFAULT_ACQUISITION_METHODS
        self.acquisition_sequence = [ TopNAcquisition ]
        self.logger = logging.getLogger(__name__)
        
if __name__ == "__main__":
    algo = TopNTestAlgorithm()
    algo.pre_acquisition()
    algo.intra_acquisition()
    algo.post_acquisition()