import logging
from .custom_test import CustomTest

class ExampleCustomTest(CustomTest):

    '''Name of the custom test. This is a mandatory field for custom tests'''
    TEST_NAME = 'example_custom_test'
    def __init__(self, *args):
        super().__init__(*args)
        
    def instrument_server_manager_cb(self, msg_id, args = None):
        pass
         
    def run_test(self):
        self.logger.info('This is just an example of a custom test.')