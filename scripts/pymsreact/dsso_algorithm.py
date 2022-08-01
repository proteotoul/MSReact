import csv
import operator
import pandas as pd
import time
import keras
from algorithm import Algorithm
from enum import IntEnum
from ProteomicsDev.dsso_study.DSSO_study_v2.DSSO_function import DSSO_utilities

import traceback


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
    TRANSMITTED_SCAN_LEVEL = [2, 2]
    
    DEFAULT_NN_MODEL_DIR = '../default_nn_model'
    
    COMPARE_MASS_DIFF_TOL = 0.02
    
    DEBUG = 0
    
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
        self.grouped_dsso_list = []
        
        self.dsso_scored = pd.DataFrame(columns=['id', 
                                                 'res_valid_isotope', 
                                                 'scan_number', 
                                                 'charge', 
                                                 'mz_list', 
                                                 'intensity_list'])
                                                 
        self.dsso_link_buf = \
            pd.DataFrame(columns=['scan_number', 
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
        
    def algorithm_body(self):
        # This is temporary until the handling of sequence and methods are figured out
        print(f'Algorithm started')
        num_of_acquisitions = len(self.acquisition_methods)
        
        self.model_int = \
            keras.models.load_model(self.DEFAULT_NN_MODEL_DIR + 
                                    self.DSSO_util.MODEL_INTENSITY_PREDICTION)
        self.model_val = \
            keras.models.load_model(self.DEFAULT_NN_MODEL_DIR + 
                                    '/' + self.DSSO_util.MODEL_VALIDE_ISOTOPES)
        self.start_acquisition()
        
        while True:
            status, scan = self.fetch_received_scan()
            if (self.AcquisitionStatus.acquisition_finished == status):
                num_of_acquisitions = num_of_acquisitions - 1
                print('Acquisition ' +
                      f'{len(self.acquisition_methods) - num_of_acquisitions}' +
                      ' finished...')
                if (1 == num_of_acquisitions):
                    #self.steps_after_first_acquisition()
                    self.steps_after_second_acquisition()
                    self.start_acquisition()
                elif (0 == num_of_acquisitions):
                    #self.steps_after_second_acquisition()
                    break
            elif (self.AcquisitionStatus.scan_available == status):
                #print(int(scan["ScanNumber"]))
                if (2 == num_of_acquisitions):
                    #self.steps_during_first_acquisition(scan)
                    if (2 == int(scan['MSScanLevel'])):
                        self.steps_during_second_acquisition(scan)
                    elif (2 == int(scan['MSScanLevel'])):
                        print(f'Received MS3 scan with precursor mass: {scan["PrecursorMass"]}!')
                    pass
                elif (1 == num_of_acquisitions):
                    #self.steps_during_second_acquisition(scan)
                    pass
            else:
                # No scan was available
                pass
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
        self.convert_scan_to_dsso_link_data(scan, False)
                
    def steps_after_first_acquisition(self):
        try:
            # Format and save dsso_link_data
            dsso_link = self.format_dsso_link_data(True)
            
            file_name = "dsso_isotopic_patterns3_refactored_thermo_mock.tsv"
            with open(file_name, "w+", newline="") as f:
                writer = csv.writer(f, delimiter='\t')
                writer.writerow(['scan_number', 'charge',
                                 'mz_list', 'intensity_list'])
                filter_dsso = self.DSSO_util.filter_dsso_output(dsso_link)
                for i in range(len(filter_dsso)):
                    filter_dsso[i][0] = int(filter_dsso[i][0])
                    filter_dsso[i][1] = int(filter_dsso[i][1])
                filter_dsso = sorted(filter_dsso, key=operator.itemgetter(0))

                for dsso in filter_dsso:
                    writer.writerow([dsso[0], dsso[1],
                                     ';'.join(map(str, dsso[2])),
                                     ';'.join(map(str, dsso[3]))])
            
            self.DSSO_util.dsso_classifier_training(filter_dsso, 
                                                    self.DEBUG,
                                                    self.DEFAULT_NN_MODEL_DIR)
            
            #self.model = keras.models.load_model(self.DEFAULT_NNMODEL_DIR + 
            #                                     self.DSSO_util.MODEL_INTENSITY_PREDICTION)
            
            # Clear the dsso_link_data buffer
            self.dsso_link_data.clear()
        except Exception as e:
            traceback.print_exc()
    
    def steps_during_second_acquisition(self, scan):
        try:
            self.convert_scan_to_dsso_link_data(scan, True)
            self.dsso_link = self.format_dsso_link_data(False)
            filter_dsso = self.filter_dsso_data(self.dsso_link)
            if filter_dsso:
                scored_dsso = \
                    self.DSSO_util.dsso_classifier_prediction_with_NN_modified(filter_dsso,
                                                                                self.DEBUG,
                                                                                self.model_int,
                                                                                self.model_val)
                self.dsso_scored = \
                    self.dsso_scored.append(scored_dsso, ignore_index=True)
                self.dsso_link_buf = \
                    self.dsso_link_buf.append(self.dsso_link, ignore_index=True)
                    
                grouped_dsso = \
                    self.DSSO_util.group_dsso_entries_per_scan(self.dsso_link,
                                                               scored_dsso)
                if grouped_dsso is not None:
                    
                    self.request_dsso_ms3_scan(grouped_dsso)
                    self.grouped_dsso_list.append((grouped_dsso[0]))
                    self.grouped_dsso_list.append((grouped_dsso[1]))
                        
        except Exception as e:
            traceback.print_exc()
    
    def steps_after_second_acquisition(self):
        try:
            self.dsso_scored['id'] = self.dsso_scored.index
            filename = 'dsso_scored_patterns2_' + \
                       f'{self.DSSO_util.deisotoping_ppm_tol}.tsv'
            self.dsso_scored.to_csv(filename, sep='\t', index=False)
            #print(type(self.dsso_link_buf['scan_number'][0]))
            #dsso_entries = self.DSSO_util.group_dsso_entries(self.dsso_link_buf,
            #                                                 self.dsso_scored)
            #dsso_entries_df = pd.DataFrame(dsso_entries)
            
            dsso_entries_df = pd.DataFrame(self.grouped_dsso_list)
            dsso_entries_df = dsso_entries_df.rename(columns={'scan_number_x':'scan_number'})
            
            # dsso_entries_df = dsso_entries_df.drop('scan_number_y',1)
            # print(f'dsso_entries_df{dsso_entries_df}')
            dsso_entries_df.to_csv('../data/grouped_dsso_entries_refactored.tsv',sep= '\t',index = False)
            
            verified_data = pd.read_csv('../data/210615_test_new_DSSO_PK_1_CSMs_OFPBB210611_06.tsv', sep='\t')
            # print(f'verified_data{verified_data}')
            comparison_list = \
                self.DSSO_util.compare_dsso_output(verified_data,
                                                   dsso_entries_df,
                                                   self.COMPARE_MASS_DIFF_TOL)
            # print(f'comparison_list{comparison_list}')
            comparison_list_df = pd.DataFrame(comparison_list)
            comparison_list_df.to_csv("../data/dssoNotFoundWithNN_refactored.tsv",sep='\t',index=False)
            
            print(f'Average prediction time is: {self.DSSO_util.total_time / self.DSSO_util.num_calls}')
        except Exception as e:
            traceback.print_exc()
        
    def convert_scan_to_dsso_link_data(self, scan, clear):
        if clear:
            self.dsso_link_data.clear()
        if self.are_all_scan_elements_available(scan):
            scan_number = int(scan["ScanNumber"])
            centroid_count = int(scan["CentroidCount"])
            masses = []
            intensities = []
            for centroid in scan["Centroids"]:
                masses.append(round(float(centroid["Mz"]),7))
                intensities.append(round(float(centroid["Intensity"]),10))
            centroids = [masses, intensities]
            precursor_charge = int(scan["PrecursorCharge"])
            precursor_mass = \
                ((round(float(scan["PrecursorMass"]), 7) * precursor_charge) -
                 (precursor_charge * self.DSSO_util.proton_mass))

            self.dsso_link_data = \
                self.DSSO_util.find_dsso_links(centroids,
                                               centroid_count,
                                               precursor_charge,
                                               precursor_mass,
                                               scan_number,
                                               self.dsso_link_data)

                                               
    def format_dsso_link_data(self, save):
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
        dsso_link['scan_charge'] = \
            pd.to_numeric(dsso_link['scan_charge'], downcast='integer')
        dsso_link['compound_charge'] = \
            pd.to_numeric(dsso_link['compound_charge'], downcast='integer')
        if save:
            dsso_link.to_csv('dsso_link_all_charges_refactored_thermo_mock.tsv', 
                             sep="\t", index=False)
        return dsso_link
        
    def filter_dsso_data(self, dsso_link):
        filtered_dsso = self.DSSO_util.filter_dsso_output(dsso_link)
        if filtered_dsso:
            for i in range(len(filtered_dsso)):
                filtered_dsso[i][0] = int(filtered_dsso[i][0])
            filtered_dsso = sorted(filtered_dsso,
                                   key=operator.itemgetter(0))
        return filtered_dsso
        
    def request_dsso_ms3_scan(self, dsso_pairs):
        #print(dsso_pairs[0])
        #print(dsso_pairs[1])
        self.request_scan({"Precursor_mz" : str(dsso_pairs[0]['peak1_mz'])})
        self.request_scan({"Precursor_mz" : str(dsso_pairs[0]['peak2_mz'])})
        self.request_scan({"Precursor_mz" : str(dsso_pairs[1]['peak1_mz'])})
        self.request_scan({"Precursor_mz" : str(dsso_pairs[1]['peak2_mz'])})