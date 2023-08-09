import enum
import csv
import os
import logging
import traceback

class Algorithm:
    '''A base class for algorithms'''

    '''Method - TODO: Create default method based on real method.'''
    ACQUISITION_METHOD = {}
    '''Sequence - List of Acquisitions'''
    ACQUISITION_SEQUENCE = []
    '''Cycle interval - TODO: This is only for mock.'''
    CYCLE_INTERVAL = 10
    '''Name of the algorithm. This is a mandatory field for the algorithms'''
    ALGORITHM_NAME = 'abstract_algorithm'
    '''Level of MS scans that are transferred from the mock server.
       eg. - 1 means only MS scans are transferred from the mock server. 
           - 2 means MS and MS2 scans are transferred from the mock server
       Note - In case of custom scan requests the requested scan will be 
              transferred from the mock server not regarding the scan level,
              if it's available in the raw file.'''
    TRANSMITTED_SCAN_LEVEL = [1, 2]
    # Title of notes column in Thermo sequence file
    COMMENT_COLUMN = "Comment"
    FILE_NAME_COLUMN = "File Name"
    SAMPLE_ID_COLUMN = "Sample ID"
    
    class AcquisitionStatus(enum.Enum):
        scan_available          = 0
        scan_not_available      = 1
        acquisition_finished    = 2
    
    def __init__(self):
        self.acquisition_method = self.ACQUISITION_METHOD
        self.acquisition_sequence = self.ACQUISITION_SEQUENCE
        self.raw_file_names = [''] * len(self.ACQUISITION_SEQUENCE)
        self.current_acquisition = None
        self.logger = logging.getLogger(__name__)

    def set_acquisition_sequence(self, exported_seq_file):
        success = False
        
        if os.path.isfile(exported_seq_file):
            with open(exported_seq_file, 'r') as seq_file:
                # Check the format of the exported sequence file. If the first 
                # row is not a header skip to the second line.
                has_header = csv.Sniffer().has_header(seq_file.read())
                seq_file.seek(0)
                if not has_header:
                    seq_file.readline()

                sequence = csv.DictReader(seq_file)
                acq_raw_files = []
                acq_sample_ids = []
                acq_task_seq = []
                row_count = 0
                for row in sequence:
                    row_count = row_count + 1
                    try:
                        acquisition = row[self.COMMENT_COLUMN]
                        for acq_class in self.acquisition_sequence:
                            if acquisition == acq_class.__name__:
                                acq_task_seq.append(acq_class)
                                success = True
                                break
                        if row_count != len(acq_task_seq):
                            success = False
                            error_print = ("Could not resolve the following sequence input from user:"
                                           + "\n\t{0:>{length}}    {1:>{length}}    {2:>{length}}".format(self.FILE_NAME_COLUMN, 
                                                                                                          self.SAMPLE_ID_COLUMN, 
                                                                                                          self.COMMENT_COLUMN, length=20)
                                           + "\n\t{0:>{length}}    {1:>{length}}    {2:>{length}}".format(row[self.FILE_NAME_COLUMN],
                                                                                                          row[self.SAMPLE_ID_COLUMN],
                                                                                                          row[self.COMMENT_COLUMN], length=20))
                            self.logger.error(error_print)
                        else:
                            acq_raw_files.append(row[self.FILE_NAME_COLUMN])
                            acq_sample_ids.append(row[self.SAMPLE_ID_COLUMN])
                        # Alternative solution for lookup
                        #acq_class = getattr(sys.modules[self.__module__], acquisition)
                        #acquisition_seq.append(acq_class)
                        #success = True
                    except Exception as e:
                        self.logger.error(f"Could not resolve sequence input from user.")
                        self.logger.error(e)
                        traceback.print_exc()
                        success = False
                        break
        
                if success:
                    self.acquisition_sequence = acq_task_seq
                    self.raw_file_names = acq_raw_files
                    seq_info_print = "Dynamic acquisition sequence set by user:\n"
                    seq_info_print = (seq_info_print 
                                      + "\t{0:>{length}}    {1:>{length}}    {2:>{length}}".format(self.FILE_NAME_COLUMN, 
                                                                                                   self.SAMPLE_ID_COLUMN, 
                                                                                                   self.COMMENT_COLUMN, length=20))
                    for i in range(len(acq_task_seq)):
                        line = "\t{0:>{length}}    {1:>{length}}    {2:>{length}}".format(acq_raw_files[i],
                                                                                          acq_sample_ids[i],
                                                                                          acq_task_seq[i].__name__, length=20)

                        seq_info_print = seq_info_print + '\n' + line
                    self.logger.info(seq_info_print)
        
        return success
                    
                