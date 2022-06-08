from algorithm import Algorithm
from algorithm_list import AlgorithmList
from request_test_algo import RequestTestAlgorithm
from receive_test_algo import ReceiveTestAlgorithm
from perm_acq_test_algo import PermAcqTestAlgorithm

class AlgorithmTestList(AlgorithmList):
    ALGO_LIST = [RequestTestAlgorithm,
                 ReceiveTestAlgorithm,
                 PermAcqTestAlgorithm]
    
    def __init__(self):
        pass