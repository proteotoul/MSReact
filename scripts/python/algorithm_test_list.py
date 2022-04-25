from algorithm import Algorithm
from algorithm_list import AlgorithmList
from request_test_algo import RequestTestAlgorithm
from receive_test_algo import ReceiveTestAlgorithm

class AlgorithmTestList(AlgorithmList):
    ALGO_LIST = [RequestTestAlgorithm, ReceiveTestAlgorithm]
    
    def __init__(self):
        pass