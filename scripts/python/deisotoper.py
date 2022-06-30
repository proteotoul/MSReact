import logging
from abc import abstractmethod

class BaseDeisitoper:
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    @abstractmethod
    def deisotope_peaks(self, centroids, config):
        pass
        