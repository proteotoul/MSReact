from algorithm import Algorithm
from acquisition import Acquisition, AcquisitionStatusIds
from tribid_instrument import ThermoTribidInstrument
import logging
import time

class RequestTestAcquisition(Acquisition):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = 'Request_test_algo_first_acquisition'
        self.instrument = ThermoTribidInstrument()
        
    def pre_acquisition(self):
        self.logger.info('Executing pre-acquisition steps.')
        
    def intra_acquisition(self):
        self.logger.info('Executing intra-acquisition steps.')
        while AcquisitionStatusIds.ACQUISITION_RUNNING == self.get_acquisition_status():
            scan = self.fetch_received_scan()
            if ((scan is not None) and (1 == scan["MSScanLevel"])):
                selectedCentroid = scan["Centroids"][0]
                for centroid in scan["Centroids"]:
                    selectedCentroid = \
                        selectedCentroid if (selectedCentroid["Intensity"] > centroid["Intensity"]) else centroid
                        
                self.request_custom_scan({"PrecursorMass": str(selectedCentroid["Mz"]),
                                          "ScanType": "MSn"})
                time.sleep(0.1)
            else:
                pass
        self.logger.info('Finishing intra acquisition.')
    
    def post_acquisition(self):
        self.logger.info('Executing post-acquisition steps.')

class RequestTestAlgorithm(Algorithm):
    """
    Algorithm for testing scan requests functionality of the client

    ...

    Attributes
    ----------
    scan_request_action : function
        A function that the algorithm can call when it would like to request a 
        custom scan
    received_scan_format : dict
        The format in which the scans will be received from the Mass 
        Spectrometer instrument
    requested_scan_format : dict
        The format in which a scan can be requested from the Mass 
        Spectrometer instrument
    acquisition_method : Method
        The acquisition method to validate and update the default method to
    acquisition_sequence : Sequence
            The acquisition sequence to validate and update the default 
            sequence to
            
    Methods
    -------
    consume_scan(scan)
        Consumes a scan that was received from the Mass Spectrometer Instrument
    validate_methods_and_sequence(methods, sequence):
        Validates that the acquisition method(s) and sequence is appropriate
        for the algorithm and updates the algorithm's default method(s) and 
        sequence for that validated method(s) and sequences.
    algorithm_body():
        The body of the algorithm that will be executed
    """

    """Method - TODO: Create default method based on real method."""
    DEFAULT_ACQUISITION_METHODS = {}
    """Sequence - TODO: Create default method based on real method."""
    DEFAULT_ACQUISITION_SEQUENCE = {}
    """Cycle interval - TODO: This is only for mock."""
    CYCLE_INTERVAL = 10
    """Name of the algorithm. This is a mandatory field for the algorithms"""
    ALGORITHM_NAME = 'request_test'
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
        self.acquisition_sequence = [ RequestTestAcquisition ]
        self.logger = logging.getLogger(__name__)
    
        
    def algorithm_body(self):
        # This is temporary until the handling of sequence and methods are figured out
        ''''
        num_of_acquisitions = len(self.acquisition_methods) if (self.acquisition_methods is not None) else 1
        while True:
            status, scan = self.fetch_received_scan()
            if (self.AcquisitionStatus.acquisition_finished == status):
                num_of_acquisitions = num_of_acquisitions - 1
                self.logger.info(f'Acquisition {num_of_acquisitions} finished...')
                if (0 == num_of_acquisitions):
                    break
            elif (self.AcquisitionStatus.scan_available == status):
                    mass = 0
                    for centroid in scan['Centroids']:
                        if mass < centroid['Mz']:
                            mass = centroid['Mz']
                    #self.request_scan({"Precursor_mz" : str(mass)})
                    #c_count = scan['CentroidCount']
                    #self.logger.info(f'Centroid count: {c_count}')
                    #time.sleep(0.001)
            else:
                # No scan was available
                pass
                    
        self.logger.info(f'Exited algorithm loop')      
'''
            
        self.start_acquisition()
        
        while True:
            status, scan = self.fetch_received_scan()
            if (self.AcquisitionStatus.acquisition_finished == status):
                break
            elif (self.AcquisitionStatus.scan_available == status):
                if (2 == scan["MSScanLevel"]):
                    time.sleep(0.4)
                    self.request_scan({"Precursor_mz": str(scan["PrecursorMass"])})
            else:
                # No scan was available
                pass
        self.logger.info(f'Exited algorithm loop')
                