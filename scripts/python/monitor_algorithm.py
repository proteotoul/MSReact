from algorithm import Algorithm
from acquisition import Acquisition, AcquisitionStatusIds
from tribid_instrument import ThermoTribidInstrument
import logging
import time

class MonitorAcquisition(Acquisition):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = 'Monitor_algo_first_acquisition'
        self.instrument = ThermoTribidInstrument()
        
    def pre_acquisition(self):
        self.logger.info('Executing pre-acquisition steps.')
        
    def intra_acquisition(self):
        self.logger.info('Executing intra-acquisition steps.')
        while AcquisitionStatusIds.ACQUISITION_RUNNING == self.get_acquisition_status():
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
    """
    Algorithm implementing simple monitoring

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

        field_names = ['CentroidCount', 'Centroids', 'DetectorName', 'MSScanLevel', 
                  'PrecursorCharge', 'PrecursorMass', 'ScanNumber']
                  
        #with open('FusionTrial.csv', 'w') as csvfile:
        with open('FusionTrial.json', 'w') as fp:
            #writer = csv.DictWriter(csvfile, fieldnames = field_names)
            #writer.writeheader()
            
            self.start_acquisition()
            
            while True:
                status, scan = self.fetch_received_scan()
                if (self.AcquisitionStatus.acquisition_finished == status):
                    break
                elif (self.AcquisitionStatus.scan_available == status):
                    try:
                        #writer.writerow(scan)
                        json.dump(scan, fp, indent=2, sort_keys=True)
                    except Exception as e:
                        self.logger.error(e)
                else:
                    # No scan was available
                    pass
        self.logger.info(f'Exited algorithm loop')
                