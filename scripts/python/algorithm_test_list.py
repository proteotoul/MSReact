from algorithm import Algorithm
from algorithm_list import AlgorithmList
from request_test_algo import RequestTestAlgorithm
from receive_test_algo import ReceiveTestAlgorithm
from perm_acq_test_algo import PermAcqTestAlgorithm
from lim_count_acq_test_algo import LimCountAcqTestAlgorithm
from lim_duration_acq_test_algo import LimDurationAcqTestAlgorithm

class AlgorithmTestList(AlgorithmList):
    ALGO_LIST = [RequestTestAlgorithm,
                 ReceiveTestAlgorithm,
                 PermAcqTestAlgorithm,
                 LimCountAcqTestAlgorithm,
                 LimDurationAcqTestAlgorithm]
    
    def __init__(self):
        pass