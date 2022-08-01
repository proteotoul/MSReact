import logging
from instrument_server_manager import InstrumentServerManager
from abc import abstractmethod

class CustomTest:

    '''Name of the custom test. This is a mandatory field for custom tests'''
    TEST_NAME = 'abstract_test'
    def __init__(self, protocol, address, loop):
        self.protocol = protocol
        self.address = address
        self.loop = loop 
        
        self.inst_serv_man = \
            InstrumentServerManager(self.protocol,
                                    self.instrument_server_manager_cb)
        self.logger = logging.getLogger(__name__)
        
    @abstractmethod
    def instrument_server_manager_cb(self, msg_id, args = None):
        pass
        
    @abstractmethod    
    def run_test(self):
        pass