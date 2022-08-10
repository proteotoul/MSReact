# OpenMS deisotoper
from .deisotoper import BaseDeisitoper
import logging
import time
from pyopenms import MSSpectrum, Deisotoper

class DeisitoperOpenMS(BaseDeisitoper):
    
    DEFAULT_FRAG_TOLERANCE = 10
    DEFAULT_FRAG_UNIT_PPM = True
    DEFAULT_MIN_CHARGE = 2
    #DEFAULT_MAX_CHARGE = 6
    DEFAULT_MAX_CHARGE = 10
    DEFAULT_ONLY_DEISO = True
    DEFAULT_MIN_ISO = 3
    DEFAULT_MAX_ISO = 10
    #DEFAULT_SINGLE_CHARGE = True
    DEFAULT_SINGLE_CHARGE = False
    DEFAULT_ANNOT_CHARGE = True
    DEFAULT_ANNOT_PEAK_COUNT = True
    DEFAULT_DECREASE_MOD = True
    #DEFAULT_START_INT_CHECK = 3
    DEFAULT_START_INT_CHECK = 1
    DEFAULT_ADD_UP_INT = False
    
    
    def __init__(self):
        super().__init__()
        
    def deisotope_peaks(self, centroids, config = {}):
        
        # Extract configuration from the config dictionary
        self.__extract_config(config)
        
        self.logger.info(f'Do deisotoping on {len(centroids)} centroids.')
        tick = time.time()
        spectrum = MSSpectrum()
        mzs = [centroid['Mz'] for centroid in centroids]
        intensities = [centroid['Intensity'] for centroid in centroids]
        spectrum.set_peaks([mzs, intensities])
        # Documentation for the deisotopeAndSingleCharge to be found:
        # https://abibuilder.informatik.uni-tuebingen.de/archive/openms/Documentation/nightly/html/classOpenMS_1_1Deisotoper.html
        Deisotoper.deisotopeAndSingleCharge(spectrum,
                                            self.fragment_tolerance,
                                            self.fragment_unit_ppm,
                                            self.min_charge,
                                            self.max_charge,
                                            self.keep_only_deisotoped,
                                            self.min_isotopes,
                                            self.max_isotopes,
                                            self.make_single_charged,
                                            self.annotate_charge, 
                                            self.annotate_iso_peak_count,
                                            self.use_decreasing_model, 
                                            self.start_intensity_check, 
                                            self.add_up_intensity)
        duration = abs(time.time() - tick)
        
        centroids = [{"Intensity" : peak.getIntensity(), "Mz" : peak.getMZ()} for peak in spectrum]                
        self.logger.info(f'Finished deisotoping, new number of centroids: {len(centroids)}, duration: {duration}')
        
        return centroids
                
    def __extract_config(self, config):       
        # Extract configuration
        
        # The tolerance used to match isotopic peaks
        self.fragment_tolerance = \
            config['fragment_tolerance'] if 'fragment_tolerance' in config else self.DEFAULT_FRAG_TOLERANCE
        # Whether ppm or m/z is used as tolerance
        self.fragment_unit_ppm = \
            config['fragment_unit_ppm'] if 'fragment_unit_ppm' in config else self.DEFAULT_FRAG_UNIT_PPM
        # The minimum charge considered
        self.min_charge = \
            config['min_charge'] if 'min_charge' in config else self.DEFAULT_MIN_CHARGE
        # The maximum charge considered
        self.max_charge = \
            config['max_charge'] if 'max_charge' in config else self.DEFAULT_MAX_CHARGE
        # Only monoisotopic peaks of fragments with isotopic pattern are retained
        self.keep_only_deisotoped = \
            config['keep_only_deisotoped'] if 'keep_only_deisotoped' in config else self.DEFAULT_ONLY_DEISO
        # The minimum number of isotopic peaks (at least 2) required for an isotopic cluster
        self.min_isotopes = \
            config['min_isotopes'] if 'min_isotopes' in config else self.DEFAULT_MIN_ISO
        # The maximum number of isotopic peaks (at least 2) considered for an isotopic cluster
        self.max_isotopes = \
            config['max_isotopes'] if 'max_isotopes' in config else self.DEFAULT_MAX_ISO
        # Convert deisotoped monoisotopic peak to single charge
        self.make_single_charged = \
            config['make_single_charged'] if 'make_single_charged' in config else self.DEFAULT_SINGLE_CHARGE
        # Annotate the charge to the peaks in the IntegerDataArray: "charge" (0 for unknown charge)
        self.annotate_charge = \
            config['annotate_charge'] if 'annotate_charge' in config else self.DEFAULT_ANNOT_CHARGE
        # Annotate the number of isotopic peaks in a pattern for each monoisotopic peak in the IntegerDataArray: "iso_peak_count"
        self.annotate_iso_peak_count = \
            config['annotate_iso_peak_count'] if 'annotate_iso_peak_count' in config else self.DEFAULT_ANNOT_PEAK_COUNT
        # Use a simple averagine model that expects heavier isotopes to have less intensity. If false, no intensity checks are applied.
        self.use_decreasing_model = \
            config['use_decreasing_model'] if 'use_decreasing_model' in config else self.DEFAULT_DECREASE_MOD
        # Number of the isotopic peak from which the decreasing model should be applied. 
        # <= 1 will force the monoisotopic peak to be the most intense. 
        # 2 will allow the monoisotopic peak to be less intense than the second peak. 
        # 3 will allow the monoisotopic and the second peak to be less intense than the third, etc. 
        # A number higher than max_isopeaks will effectively disable use_decreasing_model completely.
        self.start_intensity_check = \
            config['start_intensity_check'] if 'start_intensity_check' in config else self.DEFAULT_START_INT_CHECK
        # Sum up the total intensity of each isotopic pattern into the intensity of the reported monoisotopic peak
        self.add_up_intensity = \
            config['add_up_intensity'] if 'add_up_intensity' in config else self.DEFAULT_ADD_UP_INT