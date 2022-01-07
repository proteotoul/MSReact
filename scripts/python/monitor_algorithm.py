from algorithm import Algorithm
import time

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
        self.acquisition_methods = self.DEFAULT_ACQUISITION_METHODS
        self.acquisition_sequence = self.DEFAULT_ACQUISITION_SEQUENCE
        
    def configure_algorithm(self, 
                            fetch_received_scan, 
                            request_scan,
                            start_acquisition):
        """
        Parameters
        ----------
        scan_req_act : function
            A function that the algorithm can call when it would like to 
            request a custom scan
        """
        self.fetch_received_scan = fetch_received_scan
        self.request_scan = request_scan
        self.start_acquisition = start_acquisition
        
    def validate_methods_and_sequence(self, methods, sequence):
        """
        Parameters
        ----------
        method : Method
            The acquisition method to validate and update the default method to
        sequence : Sequence
            The acquisition sequence to validate and update the default 
            sequence to
        Returns
        -------
        Bool: True if the update and validation of the acquisition method and 
              sequence was successful and False if it failed
        """
        success = True
        self.acquisition_methods = methods
        self.acquisition_sequence = sequence
        return success
        
    def validate_scan_formats(self, rx_scan_format, req_scan_format):
        """
        Parameters
        ----------
        rx_scan_format : Dict
            The acquisition method to validate and update the default method to
        req_scan_format : Dict
            The acquisition sequence to validate and update the default 
            sequence to
        Returns
        -------
        Bool: True if the update and validation of the received scan format and 
              the requested scan format was successful and False if it failed
        """
        success = True
        self.received_scan_format = rx_scan_format
        self.requested_scan_format = req_scan_format
        return success
        
    def algorithm_body(self):
        # This is temporary until the handling of sequence and methods are figured out
        num_of_acquisitions = len(self.acquisition_methods)
        while True:
            status, scan = self.fetch_received_scan()
            if (self.AcquisitionStatus.acquisition_finished == status):
                num_of_acquisitions = num_of_acquisitions - 1
                print(f'Acquisition {num_of_acquisitions} finished...')
                if (0 == num_of_acquisitions):
                    break
            elif (self.AcquisitionStatus.scan_available == status):
                    mass = 0
                    for centroid in scan['Centroids']:
                        if mass < centroid['Mz']:
                            mass = centroid['Mz']
                    #self.request_scan({"Precursor_mz" : str(mass)})
                    #c_count = scan['CentroidCount']
                    #print(f'Centroid count: {c_count}')
                    #time.sleep(0.001)
            else:
                # No scan was available
                pass
                    
        print(f'Exited algorithm loop')            
                