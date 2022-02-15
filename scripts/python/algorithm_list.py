from algorithm import Algorithm
from monitor_algorithm import MonitorAlgorithm
from request_test_algo import RequestTestAlgorithm
from listen_test_algo import ListenTestAlgorithm
#from dsso_algorithm import DSSOAlgorithm

class AlgorithmList:
    #ALGO_LIST = [MonitorAlgorithm, DSSOAlgorithm]
    ALGO_LIST = [MonitorAlgorithm, RequestTestAlgorithm, ListenTestAlgorithm]
    
    def __init__(self):
        pass
    def get_available_names(self):
        return [Algorithm.ALGORITHM_NAME for Algorithm in self.ALGO_LIST]
        
    def find_by_name(self, name):
        found_algorithm = False
        for i in range(len(self.ALGO_LIST)):
            if name == self.ALGO_LIST[i].ALGORITHM_NAME:
                found_algorithm = True
                return self.ALGO_LIST[i]
        if not found_algorithm:
            return None