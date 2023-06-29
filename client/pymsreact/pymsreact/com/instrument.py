import asyncio
import csv
import logging
import multiprocessing
import time
import os
import requests
from enum import Enum
from multiprocessing import Queue
from queue import Empty, Full

class InstrMsgIDs(Enum):
    SCAN = 1
    FINISHED_ACQUISITION = 2
    ERROR = 3

class InstrumentClient:
    '''
    This module is responsible for managing the instrument server through the 
    protocol. 

    ...

    Attributes
    ----------
    protocol: BaseProtocol
        Protocol to use for the communication with the server
        
    app_cb : func
        Callback function to forward messages to the application from the 
        InstrumentClient
    
    '''
    
    def __init__(self, protocol, app_cb): 
        """
        Parameters
        ----------
        protocol: BaseProtocol
            Protocol to use for the communication with the server.
        app_cb : func
            Callback function to forward messages to the application from the 
            InstrumentClient.
        """
        
        # Store inputs
        self.proto = protocol
        self.app_cb = app_cb
        
        # Initialise address and synchronisation components
        self.address = None
        self.acq_running = False
        self.acq_lock = asyncio.Lock()
        self.resp_cond = asyncio.Condition()
        self.resp = None
        
        # Initialise logger
        self.logger = logging.getLogger(__name__)
        
        
    async def connect_to_server(self, address = None):
        """Connects to server with a given address.

        Parameters
        ----------
        address : str
            IP address of the server to connect to eg. "172.18.160.1".

        Returns
        -------
        bool
            True if the connection was successful and False if it failed.
        """
    
        success = False
        
        if address is not None:
            self.address = address
            success = await self.proto.connect(self.address)
        else:
            success = await self.proto.connect()
        
        return success
        
    async def disconnect_from_server(self):
        """ Disconnects from the server to which the client is currently 
        connected. """
        self.address = None
        await self.proto.disconnect()
        
    async def get_protocol_version(self):
        """Retrieves the protocol version of the server that is currently 
        connected to the client.

        Returns
        -------
        str
            The protocol version of the server.
        """
        self.logger.info('Getting protocol version')

        await self.proto.send_message(self.proto.MessageIDs.GET_SERVER_PROTO_VER_CMD)
        msg, payload = await self.__wait_for_response()
        if (self.proto.MessageIDs.SERVER_PROTO_VER_RSP == msg):
            self.logger.info(f'Received protocol version: {payload}')
        else:
            pass
            # Raise exception
        return payload
        
    async def get_server_version(self):
        """Retreives the software version of the server that is currently 
        connected to the client.

        Returns
        -------
        str
            The software version of the server.
        """
        self.logger.info('Getting server software version')
        
        await self.proto.send_message(self.proto.MessageIDs.GET_SERVER_SW_VER_CMD)
        msg, payload = await self.__wait_for_response()
        if (self.proto.MessageIDs.SERVER_SW_VER_RSP == msg):
            self.logger.info(f'Received server software version: {payload}')
        else:
            pass
        return payload
        
    async def get_available_instruments(self):
        """Retreives the list of available instruments from the server.

        Returns
        -------
        list
            The list of available instruments.
        """
        self.logger.info('Getting available instruments')
        
        await self.proto.send_message(self.proto.MessageIDs.GET_AVAILABLE_INSTR_CMD)
        msg, payload = await self.__wait_for_response()
        if (self.proto.MessageIDs.AVAILABLE_INSTR_RSP == msg):
            # TODO: Process the payload into a list.
            self.logger.info(f'Available instruments: {payload}')
        else:
            pass
        return payload
        
    async def get_instrument_info(self, instrument):
        """Retreives information about a selected instrument.

        Parameters
        ----------
        instrument : int
            The id of the instrument.
            
        Returns
        -------
        str
            Information about the selected instrument.
        """
    
        self.logger.info(f'Requesting info about instrument {instrument}')
        
        await self.proto.send_message(self.proto.MessageIDs.GET_INSTR_INFO_CMD,
                                      instrument)
        msg, payload = await self.__wait_for_response()
        if (self.proto.MessageIDs.AVAILABLE_INSTR_RSP == msg):
            self.logger.info(f'Instrument info:\n{payload}')
        else:
            pass
        return payload
        
    async def get_instrument_state(self, instrument):
        """Retreives the state of a selected instrument.

        Parameters
        ----------
        instrument : int
            The id of the instrument.
            
        Returns
        -------
        str
            State of the selected instrument.
        """
    
        self.logger.info(f'Get instrument state of instrument: {instrument}')
        
        await self.proto.send_message(self.proto.MessageIDs.GET_INSTR_STATE_CMD,
                                      instrument)
        msg, payload = await self.__wait_for_response()
        if (self.proto.MessageIDs.INSTR_STATE_RSP == msg):
            self.logger.info(f'Instrument state:\n{payload}')
        else:
            pass
        return payload
        
    async def select_instrument(self, instrument):
        """Selects instrument to run acquisition/algorithm on.

        Parameters
        ----------
        instrument : int
            The id of the instrument.
            
        """
        self.logger.info('Selecting instrument.')
        await self.proto.send_message(self.proto.MessageIDs.SELECT_INSTR_CMD,
                                      instrument)
        msg, payload = await self.__wait_for_response()
        if (self.proto.MessageIDs.OK_RSP != msg):
            self.logger.error("Problem with instrument selection.")
            raise Exception("Problem with instrument selection.")
        
    async def get_possible_params(self):
        """Retreives possible parameters that can be used for requesting scans 
        from an instrument.

        Returns
        -------
        list
            List of possible parameters where each item in the list is a 
            dictionary with keys: "Name", "Selection", "DefaultValue" "Help".
        """
        self.logger.info('Getting possible parameters for requesting scans...')
        await self.proto.send_message(self.proto.MessageIDs.GET_POSSIBLE_PARAMS_CMD)
        msg, payload = await self.__wait_for_response()
        if (self.proto.MessageIDs.POSSIBLE_PARAMS_RSP != msg):
            # TODO - raise exception
            self.logger.error("Response was not POSSIBLE_PARAMS message.")
            quit()
        else:
            field_names = ['Name', 'Selection', 'DefaultValue', 'Help']
                  
            #with open('output\\PossibleParams.csv', 'w', newline='') as csvfile:
            #    writer = csv.DictWriter(csvfile, fieldnames = field_names)
            #    writer.writeheader()
                #self.logger.info(payload)
            #    for v in payload:
            #        writer.writerow(v)
        return payload
        
    async def request_scan(self, parameters):
        """Requests custom scan from the previously selected instrument with the
           given parameters.

        Parameters
        ----------
        parameters : dict
            String-string dictionary of parameters, where a given key has to be
            one of the names of the possible parameters. 
            See :func:`~instrument.InstrumentClient.get_possible_params`.
            
        """
        #self.logger.info(f'Requesting scans with the following parameters:\n{parameters}')
        await self.proto.send_message(self.proto.MessageIDs.REQ_CUSTOM_SCAN_CMD,
                                      parameters)
        #msg, payload = await self.proto.receive_message()
        #if (self.proto.MessageIDs.OK_RSP != msg):
        #    self.logger.error("Problem with custom scan request.")
        #    raise Exception("Problem with custom scan request.")
        
    async def cancel_custom_scan(self):
        """Cancels the previously requested custom scan."""
        await self.proto.send_message(self.proto.MessageIDs.CANCEL_CUSTOM_SCAN_CMD)
        
    async def request_repeating_scan(self, parameters):
        """Requests a custom scan that is being acquired repeateadly by the
           instrument until the repeating scan request is cancelled.

        Parameters
        ----------
        parameters : dict
            String-string dictionary of parameters, where a given key has to be
            one of the names of the possible parameters. 
            See :func:`~instrument.InstrumentClient.get_possible_params`.
            
        """
        await self.proto.send_message(self.proto.MessageIDs.SET_REPEATING_SCAN_CMD,
                                      parameters)
                                      
    async def cancel_repeating_scan(self):
        """Cancels the previously requested repeating scan."""
        await self.proto.send_message(self.proto.MessageIDs.CLEAR_REPEATING_SCAN_CMD)
        
    async def subscribe_to_scans(self):
        """Subscribes to scans on the selected instrument, i.e. the server will 
        transmit the scans acquired by the instrument to the client."""
        self.logger.info('Subscribing for scans.')
        await self.proto.send_message(self.proto.MessageIDs.SUBSCRIBE_TO_SCANS_CMD)
        msg, payload = await self.__wait_for_response()
        if (self.proto.MessageIDs.OK_RSP != msg):
            self.logger.error("Problem with subscribing to scans.")
            raise Exception("Problem with subscribing to scans.")
    
    async def unsubscribe_from_scans(self):
        """Unsubscribes from scans on the selected instrument, i.e. the server will
        stop transmitting the scans acquired by the instrument to the client."""
        self.logger.info('Unsubscribing from scans.')
        await self.proto.send_message(self.proto.MessageIDs.UNSUBSCRIBE_FROM_SCANS_CMD)
        msg, payload = await self.__wait_for_response()
        if (self.proto.MessageIDs.OK_RSP != msg):
            self.logger.error("Problem with unsubscribing from scans.")
            raise Exception("Problem with unsubscribing from scans.")
        
    async def configure_acquisition(self, config):
        """Configures acquisition with a given set of parameters.

        Parameters
        ----------
        parameters : dict
            String-string dictionary of parameters:
            "AcquisitionType" : TODO - Link to reference
            "AcquisitionParam" : TODO - Link to reference
            "RawFileName" : TODO - Link to reference
            "SampleName" : TODO - Link to reference
            "Comment" : TODO - Link to reference
            "SingleProcessingDelay" : TODO - Link to reference
            "WaitForContactClosure" : TODO - Link to reference"""
        self.logger.info('Configure the acquisition')
        await self.proto.send_message(self.proto.MessageIDs.CONFIG_ACQ_CMD, config)
        msg, payload = await self.__wait_for_response()
        if (self.proto.MessageIDs.OK_RSP != msg):
            self.logger.error("Problem with configuring acquisition.")
            raise Exception("Problem with configuring acquisition.")
        
    async def start_acquisition(self):
        """Requests the start of an acquisition from server."""
        self.logger.info('Start receiving scans from the instrument')
        await self.proto.send_message(self.proto.MessageIDs.START_ACQ_CMD)
        msg, payload = await self.__wait_for_response()
        if (self.proto.MessageIDs.OK_RSP != msg):
            self.logger.error("Problem with starting acquisition.")
            raise Exception("Problem with starting acquisition.")
            
    async def stop_acquisition(self):
        """Requests the stop of the current acquisition from server."""
        self.logger.info('Stop receiving scans from the instrument')
        await self.proto.send_message(self.proto.MessageIDs.STOP_ACQ_CMD)
        msg, payload = await self.__wait_for_response()
        if (self.proto.MessageIDs.OK_RSP != msg):
            self.logger.error("Problem with stopping acquisition.")
            raise Exception("Problem with stopping acquisition.")
            
    async def update_default_scan_params(self, params):
        """Update default scan parameters. When a custom scan is requested, 
           only the scan parameters that are specified in the request are 
           updated, the rest of the parameters stay the default values. With
           this request the default parameters can be overwritten, so they 
           don't need to be specified at each request if they stay the same."""
        self.logger.info('Update default scan parameters to the following: ' +
                         f'{params}')
        await self.proto.send_message(self.proto.MessageIDs.UPDATE_DEF_SCAN_PARAMS_CMD, params)
        msg, payload = await self.__wait_for_response()
        if (self.proto.MessageIDs.OK_RSP != msg):
            self.logger.error("Problem with updating default scan parameters.")
            raise Exception("Problem with updating default scan parameters.")
            
    async def request_raw_file_name(self):
        """Requests the name of the current acquisitions raw file"""
        self.logger.info('Requesting raw file name from the instrument.')
        raw_file_id = ""
        await self.proto.send_message(self.proto.MessageIDs.GET_ACQ_RAW_FILE_NAME)
            
        if (self.proto.MessageIDs.ACQ_RAW_FILE_NAME_RSP != msg):
            self.logger.error("Problem with getting raw file name!")
            raise Exception("Problem with getting raw file name!")
        else:
            raw_file_id = payload
        return raw_file_id
        
    async def request_last_acquisition_file(self):
        """Requests the raw file of the last acquisition"""
        self.logger.info('Request latest acquisition raw file from server.')
        await self.proto.send_message(self.proto.MessageIDs.GET_LAST_ACQ_FILE_CMD)
        time.sleep(1)
        msg, payload = await self.__wait_for_response()
        if (self.proto.MessageIDs.LAST_ACQ_FILE_RSP == msg):
            self.__download(payload, ".//")
        else:
            self.logger.error("Problem with getting last acquisition raw file.")
            raise Exception("Problem with getting last acquisition raw file.")
        
    async def setup_instrument_connection(self, inst_num):
        # Start listening from messages from the client
        loop = asyncio.get_running_loop()
        self.listening_task = \
            loop.create_task(self.listen_for_messages())
            
        # Select instrument TODO - This should be instrument discovery
        await self.select_instrument(inst_num)
        
        # Collect possible parameters for requesting custom scans
        possible_params = await self.get_possible_params()
        
    async def instrument_clean_up(self):
        self.logger.info("Unsubscribe from scans.")
        await self.unsubscribe_from_scans()
        self.logger.info("Stop the listening loop.")
        self.listening_task.cancel()
        self.logger.info("Disconnect from server.")
        await self.disconnect_from_server()
        
    async def listen_for_messages(self):
        """Listens for messages from the server."""
        self.listening = True
        self.logger.info('Listening for messages started.')
        while self.listening:
            msg, payload = await self.proto.receive_message()
            self.listening = await self.__dispatch_message(msg, payload)
        self.logger.info('Exited listening for messages loop.')
    
    async def __dispatch_message(self, msg, payload):
        no_error = True
        msg_type = msg.name[-3:]
        if ('RSP' == msg_type):
            async with self.resp_cond:
                self.resp = (msg, payload)
                self.resp_cond.notify()
        elif ('EVT' == msg_type):
            if (self.proto.MessageIDs.FINISHED_ACQ_EVT == msg):
                self.logger.info('Finish message received in instrument server manager')
                self.app_cb(InstrMsgIDs.FINISHED_ACQUISITION, None)
            elif (self.proto.MessageIDs.SCAN_EVT == msg):
                self.app_cb(InstrMsgIDs.SCAN, payload)
            elif (self.proto.MessageIDs.ERROR_EVT == msg):
                self.app_cb(InstrMsgIDs.ERROR, None)
                no_error = False
        else:
            pass
            # That is an error situation
        return no_error
        
    async def __wait_for_response(self):
        async with self.resp_cond:
            await self.resp_cond.wait()
            received_resp, resp_payload = self.resp
            self.resp = None
        self.logger.info(f'Response: {received_resp.name}')
        return received_resp, resp_payload
            
    def __download(self, url: str, dest_folder: str):
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)  # create folder if it does not exist

        filename = url.split('/')[-1].replace(" ", "_")  # be careful with file names
        file_path = os.path.join(dest_folder, filename)

        r = requests.get(url, stream=True)
        if r.ok:
            self.logger.info(f"Saving to {os.path.abspath(file_path)}")
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024 * 8):
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        os.fsync(f.fileno())
        else:  # HTTP status code 4XX/5XX
            self.logger.info(f"Download failed: status code {r.status_code}\n{r.text}")
        
    
   