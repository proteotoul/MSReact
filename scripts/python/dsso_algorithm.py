import sys
sys.path.insert(0, './ProteomicsDev/dsso_study/DSSO_study_v2')

import csv
import operator
import pandas as pd
import time
from algorithm import Algorithm
from enum import IntEnum
from DSSO_function import DSSO_utilities


class DSSOAlgorithm(Algorithm):
    """
    DSSO algorithm

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
    #DEFAULT_ACQUISITION_METHODS = {"METHOD_PLACEHOLDER1"}
    DEFAULT_ACQUISITION_METHODS = {"METHOD_PLACEHOLDER1", "METHOD_PLACEHOLDER2"}
    """Sequence - TODO: Create default method based on real method."""
    DEFAULT_ACQUISITION_SEQUENCE = {}
    """Cycle interval - TODO: This is only for mock."""
    CYCLE_INTERVAL = 10
    """Name of the algorithm. This is a mandatory field for the algorithms"""
    ALGORITHM_NAME = 'dsso'
    '''Level of MS scans that are transferred from the mock server.
       eg. - 1 means only MS scans are transferred from the mock server. 
           - 2 means MS and MS2 scans are transferred from the mock server
       Note - In case of custom scan requests the requested scan will be 
              transferred from the mock server not regarding the scan level,
              if it's available in the raw file.
       Note2 - This could be different in each acquisition.'''
    TRANSMITTED_SCAN_LEVEL = 1
    
    DEFAULT_NN_MODEL_DIR = '../default_nn_model'
    
    DEBUG = 1
    
    class DSSOAlgorithmState(IntEnum):
        UNINITIALIZED = 0
        INITIALIZING = 1
        DATA_COLLECTING = 2
        TRAINING = 3
        PREDICTING = 4
        REPORTING = 5
    
    def __init__(self):
        self.acquisition_methods = self.DEFAULT_ACQUISITION_METHODS
        self.acquisition_sequence = self.DEFAULT_ACQUISITION_SEQUENCE
        
        self.DSSO_util = DSSO_utilities()
        self.dsso_link_data = []
        
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
        #self.acquisition_methods = methods
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
        print(f'Algorithm started')
        num_of_acquisitions = len(self.acquisition_methods)
        self.start_acquisition()
        
        #print_once = True
        #pepmasses = []
        #printed_dataframe = pd.DataFrame(columns = ['Masses', 'Intensities', 'CentroidCount', 'Charge', 'Mass', 'ScanNumber'])
        
        while True:
            status, scan = self.fetch_received_scan()
            if (self.AcquisitionStatus.acquisition_finished == status):
                num_of_acquisitions = num_of_acquisitions - 1
                print('Acquisition ' +
                      f'{len(self.acquisition_methods) - num_of_acquisitions}' +
                      ' finished...')
                if (1 == num_of_acquisitions):
                    self.steps_after_first_acquisition()
                    self.start_acquisition()
                elif (0 == num_of_acquisitions):
                    break
            elif (self.AcquisitionStatus.scan_available == status):
                    #print(int(scan["ScanNumber"]))
                if (2 == num_of_acquisitions):
                    self.steps_during_first_acquisition(scan)
                    pass
                elif (1 == num_of_acquisitions):
                    self.steps_during_second_acquisition(scan)
            else:
                # No scan was available
                pass
        '''
        pepmass_file = open('pepmasses_thermomock.csv', 'w+', newline ='') 
        with pepmass_file:
            write = csv.writer(pepmass_file)
            write.writerows(pepmasses)
        printed_dataframe.to_csv('dsso_link_data_going_into_find_dsso_links_thermomock.tsv', sep="\t", index=False)
        '''
        print(f'Exited algorithm loop')
                
    def safe_int(input_str):
        return (False, -1) if (input_str is None) else (True, int(input_str))
        
    def safe_float(input_str):
        return (False, -1) if (input_str is None) else (True, float(input_str))
        
    def are_all_scan_elements_available(self, scan):
        return ((scan["ScanNumber"] is not None) and
                (scan["CentroidCount"] is not None) and
                (scan["Centroids"] is not None) and
                (scan["PrecursorCharge"] is not None) and
                (scan["PrecursorMass"]))
    
    def steps_during_first_acquisition(self, scan):
        if self.are_all_scan_elements_available(scan):
            scan_number = int(scan["ScanNumber"])
            centroid_count = int(scan["CentroidCount"])
            masses = []
            intensities = []
            for centroid in scan["Centroids"]:
                masses.append(round(float(centroid["Mz"]),7))
                intensities.append(round(float(centroid["Intensity"]),10))
            centroids = [masses, intensities]
            #if (len(centroids[0]) != centroid_count):
            #    print(f'Scan number: {scan_number}')
            precursor_charge = int(scan["PrecursorCharge"])
            
            #pepmasses.append([round(float(scan["PrecursorMass"]), 12)])
            
            precursor_mass = \
                ((round(float(scan["PrecursorMass"]), 7) * precursor_charge) -
                 (precursor_charge * self.DSSO_util.proton_mass))
            '''
            if print_once:
                print(f'Centroids: {type(centroids)}')
                print(f'Mass: {type(centroids[0][0])}')
                print(f'Intensity: {type(centroids[1][0])}')
                print(f'Centroid count: {type(centroid_count)}')
                print(f'Precursor charge {type(precursor_charge)}')
                print(f'Precursor mass: {type(precursor_mass)}')
                print(f'Scan number: {type(scan_number)}')
                print(f'Dsso link data: {type(self.dsso_link_data)}')
                print_once = False 
            printed_dataframe.loc[len(printed_dataframe.index)] = \
                [';'.join(map(str, masses)), 
                 ';'.join(map(str, intensities)), 
                 centroid_count, 
                 precursor_charge, 
                 precursor_mass, 
                 scan_number]'''
            self.dsso_link_data = \
                self.DSSO_util.find_dsso_links(centroids,
                                               centroid_count,
                                               precursor_charge,
                                               precursor_mass,
                                               scan_number,
                                               self.dsso_link_data)
        '''else:
            missing_values = ''
            if (scan["Centroids"] is None):
                missing_values += 'centroids ' 
            if (scan["CentroidCount"] is None):
                missing_values += 'centroid_count '
            if (scan["PrecursorCharge"] is None):
                missing_values += 'precursor_charge '
            if (scan["PrecursorMass"] is None):
                missing_values += 'precursor_mass '
            if (scan["ScanNumber"] is None):
                missing_values += 'scan_number '
            #print(f'Scan {scan["ScanNumber"]} has a missing value of {missing_values}')'''
                
    def steps_after_first_acquisition(self):
        #print_once = True
        
        dsso_link = \
            pd.DataFrame(self.dsso_link_data, columns=['scan_number', 
                                                       'scan_charge', 
                                                       'scan_mass', 
                                                       'peak1_mz', 
                                                       'peak2_mz',
                                                       'peak_mz_distance', 
                                                       'compound_charge', 
                                                       'compound_mass',
                                                       'matching_compound_mass',
                                                       'peak1_intensity',
                                                       'peak2_intensity'])
        dsso_link.to_csv('dsso_link_all_charges_refactored_thermo_mock.tsv', 
                         sep="\t", index=False)
        
        file_name = "dsso_isotopic_patterns3_refactored_thermo_mock.tsv"
        with open(file_name, "w+", newline="") as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(['scan_number', 'charge',
                             'mz_list', 'intensity_list'])
            filter_dsso = self.DSSO_util.filter_dsso_output(dsso_link)
            for i in range(len(filter_dsso)):
                filter_dsso[i][0] = int(filter_dsso[i][0])
            filter_dsso = sorted(filter_dsso, key=operator.itemgetter(0))

            for dsso in filter_dsso:
                '''if print_once:
                    print(f'DSSO 0 type: {type(dsso[0])}')
                    print(f'DSSO 1 type: {type(dsso[1])}')
                    print(f'DSSO 2 type: {type(";".join(map(str, dsso[2])))}')
                    print(f'DSSO 3 type: {type(";".join(map(str, dsso[3])))}')
                    print_once = False'''
                writer.writerow([dsso[0], dsso[1],
                                 ';'.join(map(str, dsso[2])),
                                 ';'.join(map(str, dsso[3]))])
        
        self.DSSO_util.dsso_classifier_training(filter_dsso, 
                                                self.DEBUG,
                                                self.DEFAULT_NN_MODEL_DIR)
                                                
    def steps_during_second_acquisition(self, scan):
        pass
        