import logging
import com.instrument as instrument
from abc import abstractmethod

class CustomApp:

    '''Name of the custom app. This is a mandatory field for custom apps'''
    APP_NAME = 'abstract_app'
    def __init__(self, protocol, address, loop):
        self.protocol = protocol
        self.address = address
        self.loop = loop 
        
        self.inst_serv_man = \
            instrument.InstrumentClient(self.protocol,
                                        self.instrument_client_cb)
        self.logger = logging.getLogger(__name__)
        
    @abstractmethod
    def instrument_client_cb(self, msg_id, args = None):
        pass
        
    @abstractmethod    
    def run_app(self):
        pass