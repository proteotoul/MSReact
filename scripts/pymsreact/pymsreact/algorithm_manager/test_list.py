from .test_algorithms.algorithm_test_list import AlgorithmTestList
from .custom_tests.custom_test_list import CustomTestList

class TestList: 
    def __init__(self):
        self.algorithm_test_list = AlgorithmTestList()
        self.custom_test_list = CustomTestList()
        
    def get_available_names(self):
        names = (self.algorithm_test_list.get_available_names() +
                 self.custom_test_list.get_available_names())
        return sorted(names)
        
    def find_algorithm_test_by_name(self, name):
        return self.algorithm_test_list.find_by_name(name)
        
    def find_custom_test_by_name(self, name):    
        return self.custom_test_list.find_by_name(name) 