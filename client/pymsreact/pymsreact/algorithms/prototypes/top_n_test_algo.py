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
from utils.deisotoper_openms import DeisitoperOpenMS
from utils.real_time_mgf import RealTimeMGFWriter

# Acquisition settings
ACQUISITION_WORKFLOW = aw.Listening
ACQUISITION_PARAMETER = None
SINGLE_PROCESSING_DELAY = 0
WAIT_FOR_CONTACT_CLOSURE = True
RAW_FILE_NAME = "top_n_test.RAW"
SAMPLE_NAME = "-"
COMMENT = "This test is checking whether top N method " + \
          "can be initiated and managed from MSReact."

MZ_TOLERANCE = 0.0001 # Tolerance for the exclusion
NUMBER_OF_PEAKS = 15 # Number of precursors to select for MS2
EXCLUSION_TIME = 0.5 # Exclusion time in minutes

class TopNAcquisition(Acquisition):
    instruments = [mi.MockInstrument, ti.ThermoTribridInstrument]
    
    def __init__(self, *args):
        super().__init__(*args)
        self.name = 'Test_TopN_acquisition'
        
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
        
        exclusion_list = []
        num_requests = 0
        num_received = 0
        
        rn = 1
        self.diagnostics = {}
        
        writer = RealTimeMGFWriter("output/test.mgf")
        
        with writer:
            while AcqStatIDs.ACQUISITION_RUNNING == self.get_acquisition_status():
                scan = self.fetch_received_scan()
                
                if ((scan is not None) and (2 == scan[ScanFields.MS_SCAN_LEVEL])):
                    writer.write_scan(scan)
                    num_received = num_received + 1
                if ((scan is not None) and (1 == scan[ScanFields.MS_SCAN_LEVEL])):
                    time_of_algorithm = time.time()
                    self.logger.info(f'Received/Requested ratio = {num_received}/{num_requests}, ' +
                                     f'Last running number: {rn}, ' +
                                     f'Exclusion list length: {len(exclusion_list)}')
                    self.diagnostics.update({scan[ScanFields.SCAN_NUMBER] : {'NumReceived' : num_received,
                                                                             'CentroidCount' : scan[ScanFields.CENTROID_COUNT]}})
                    num_received = 0
                    num_requests = 0
                    
                    # Get current time
                    current_rt = scan[ScanFields.RETENTION_TIME]
                    
                    # Remove expired centroids from the exclusion list
                    cutoff = 0 # This assignment is necessary in case of empty exclusion list.
                    while cutoff < len(exclusion_list):
                        if abs(current_rt - exclusion_list[cutoff]["ExclusionTime"]) < EXCLUSION_TIME:
                            break
                        cutoff = cutoff + 1
                    exclusion_list = exclusion_list[cutoff:]
                            
                    # Get centroids from the scan
                    centroids = scan[ScanFields.CENTROIDS]
                    # Get mzs and intensities from centroids
                    mzs = [centroid[CentroidFields.MZ] for centroid in centroids]
                    intensities = [centroid[CentroidFields.INTENSITY] for centroid in centroids]
                    
                    # Do deisotoping
                    mzs, intensities = deisotoper.deisotope_peaks(mzs, intensities)
                    
                    # Combine the mzs and intensities in to a list of dicts
                    centroids = [{CentroidFields.MZ : mzs[i], 
                                  CentroidFields.INTENSITY: intensities[i] } 
                                 for i in range(len(mzs))]

                    
                    # Sort centroids by their intensity
                    centroids.sort(key=lambda i: i[CentroidFields.INTENSITY], reverse=True)
                    
                    # TODO: This code might be written nicer and shorter with some list comprehension
                    i = 0
                    excl_list_buffer = []
                    while ((i < len(centroids)) and (len(excl_list_buffer) != NUMBER_OF_PEAKS)):
                        not_excluded = True
                        for centroid_excl in exclusion_list:
                            if MZ_TOLERANCE > abs(centroids[i][CentroidFields.MZ] - centroid_excl[CentroidFields.MZ]):
                                not_excluded = False # it is excluded
                                break
                        if not_excluded:
                            self.request_custom_scan({"PrecursorMass": str(centroids[i][CentroidFields.MZ]),
                                                      "ScanType": "MSn",
                                                      "AGCTarget": "100000",
                                                      "MaxIT": "50",
                                                      "IsolationMode": "Quadrupole",
                                                      "ActivationType": "HCD",
                                                      "FirstMass": "100",
                                                      "LastMass": "2000",
                                                      "IsolationWidth": "1",
                                                      "CollisionEnergy": "30",
                                                      "REQUEST_ID": "_".join([str(scan[ScanFields.SCAN_NUMBER]), str(rn)]),
                                                      })
                                                      
                            centroid = centroids[i] | {"ExclusionTime" : current_rt}
                            excl_list_buffer.append(centroid)
                            num_requests = num_requests + 1
                            rn = rn + 1
                        i = i + 1
                    exclusion_list = exclusion_list + excl_list_buffer
                    algo_time = time.time() - time_of_algorithm
                    self.diagnostics[scan[ScanFields.SCAN_NUMBER]].update({"AlgoTime" : algo_time,
                                                                           "NumRequests" : num_requests,
                                                                           "ExclusionListLen" : len(exclusion_list),
                                                                           "CentroidCountDeisotoped" : len(centroids)})
                else:
                    pass
        
        self.logger.info('Finishing intra acquisition.')
    
    def post_acquisition(self):
        self.logger.info('Executing post-acquisition steps.')
        now = datetime.now()
        with open(f'output/diagnostics_{now.strftime("%Y%m%d_%H%M")}.csv', 'w') as f:
            f.write("ScanNum,NumReceived,CentroidCount,AlgoTime,NumRequests,ExclusionListLen,CentroidCountDeisotoped\n")
            for key in self.diagnostics.keys():
                line = f"{key},"
                for subkey in self.diagnostics[key]:
                    line += f'{self.diagnostics[key][subkey]},'
                f.write(line + '\n')
        

class TopNTestAlgorithm(Algorithm):

    """Method - TODO: Create default method based on real method."""
    ACQUISITION_METHOD = {}
    """Sequence - TODO: Create default method based on real method."""
    ACQUISITION_SEQUENCE = [ TopNAcquisition ]
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
        self.acquisition_methods = self.ACQUISITION_METHOD
        self.acquisition_sequence = [ TopNAcquisition ]
        self.configs = [ None ]
        self.logger = logging.getLogger(__name__)
        