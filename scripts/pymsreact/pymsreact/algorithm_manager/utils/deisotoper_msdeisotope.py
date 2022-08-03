# OpenMS deisotoper
from .deisotoper import BaseDeisitoper
import logging
import time
import ms_deisotope

class DeisitoperMSDeisotope(BaseDeisitoper):
    
    def __init__(self):
        super().__init__()
        
    def deisotope_peaks(self, centroids, config = {}):
        
        # Extract configuration from the config dictionary
        self.__extract_config(config)
        
        # Get only mz values                 
        peaks = [(centroid['Mz'], centroid["Intensity"]) for centroid in centroids]
        self.logger.info(f'Do deisotoping on {len(centroids)} centroids.')
        tick = time.time()
        deconvoluted_peaks, _ = \
            ms_deisotope.deconvolute_peaks(peaks, averagine=ms_deisotope.peptide,
                                           scorer=ms_deisotope.MSDeconVFitter(10.))
        duration = abs(time.time() - tick)
        centroids = [{"Intensity" : peak.intensity, "Mz" : peak.mz} for peak in deconvoluted_peaks]                
        self.logger.info(f'Finished deisotoping, new number of centroids: {len(centroids)}, duration: {duration}')
        
        return cetroids
                
    def __extract_config(self, config):
        # Extract configuration
        pass