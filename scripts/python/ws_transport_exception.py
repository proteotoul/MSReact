import logging

class WebSocketTransportException(Exception):
    def __init__(self, message, errors):
        super().__init__(message)
        self.errors = errors
        self.logger = logging.getLogger(__name__)
        self.logger.error(f'Errors:{self.errors}')