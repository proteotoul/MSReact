from .custom_test import CustomTest
from .example_custom_test import ExampleCustomTest

class CustomTestList:
    CUSTOM_TEST_LIST = [ExampleCustomTest]
    
    def __init__(self):
        pass
    def get_available_names(self):
        return [CustomTest.TEST_NAME for CustomTest in self.CUSTOM_TEST_LIST]
        
    def find_by_name(self, name):
        found_test = False
        for i in range(len(self.CUSTOM_TEST_LIST)):
            if name == self.CUSTOM_TEST_LIST[i].TEST_NAME:
                found_test = True
                return self.CUSTOM_TEST_LIST[i]
        if not found_test:
            return None