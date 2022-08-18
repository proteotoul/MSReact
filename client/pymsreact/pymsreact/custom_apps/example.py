import logging
from .app import CustomApp

class ExampleCustomApp(CustomApp):

    '''Name of the custom app. This is a mandatory field for custom apps'''
    APP_NAME = 'example'
    def __init__(self, *args):
        super().__init__(*args)
        
    def instrument_client_cb(self, msg_id, args = None):
        pass
         
    def run_app(self):
        self.logger.info('This is just an example of a custom app.')