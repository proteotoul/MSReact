from algorithm import Algorithm
from acquisition import Acquisition, AcquisitionStatusIds
from tribid_instrument import ThermoTribidInstrument
import acquisition_workflow as aw
import json
import logging
import time
import csv

# Acquisition settings
ACQUISITION_WORKFLOW = aw.Method
# That location should be on the server computer for the moment
# TODO: Think about how to transfer file through websocket
ACQUISITION_PARAMETER = 'D:\\dev\\ms-reactor\\top_n_test.meth'
SINGLE_PROCESSING_DELAY = 0
WAIT_FOR_CONTACT_CLOSURE = False
RAW_FILE_NAME = "top_n_test.RAW"
SAMPLE_NAME = "-"
COMMENT = "This test is checking whether top N method " + \
          "can be initiated and managed from MSReactor."

MZ_TOLERANCE = 0.0001
NUMBER_OF_SCANS = 15
EXCLUSION_TIME = 3


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
        exclusion_list = []
        while AcquisitionStatusIds.ACQUISITION_RUNNING == self.get_acquisition_status():
            scan = self.fetch_received_scan()
            if ((scan is not None) and (1 == scan["MSScanLevel"])):
                # Get current time
                current_time = time.time()
                
                # Remove expired centroids from the exclusion list
                cutoff = 0
                for cutoff in range(len(exclusion_list)):
                    if abs(current_time - exclusion_list[cutoff]["ExclusionTime"]) < EXCLUSION_TIME:
                        break
                exclusion_list = exclusion_list[cutoff:]
                        
                # Get centroids from the scan
                centroids = scan["Centroids"]
                # Sort certroids by their intensity
                centroids.sort(key=lambda i: i["Intensity"], reverse=True)
                # Take first n element of the list
                top_n_centroids = centroids[0:(NUMBER_OF_SCANS if len(centroids) >= NUMBER_OF_SCANS else len(centroids))]
                
                # TODO: This code might be written nicer and shorter with some list comprehension
                excl_list_buffer = []
                for centroid in top_n_centroids:
                    not_excluded = True
                    for centroid_excl in exclusion_list:
                            if MZ_TOLERANCE < abs(centroid["Mz"] - centroid_excl["Mz"]):
                                excluded = False
                                break
                    if not_excluded:            
                        self.request_custom_scan({"PrecursorMass": str(centroid["Mz"]),
                                                  "ScanType": "MSn"})
                        centroid["ExclusionTime"] = current_time
                        excl_list_buffer.append(centroid)
                exclusion_list = exclusion_list + excl_list_buffer
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
    TRANSMITTED_SCAN_LEVEL = [1, 2]
    
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