import random
import time
from pwt.dynamicAPI import api_command
from pwt.drivers.driver import Driver, threaded

import logging

import ntplib
import pwt_config
logger = logging.getLogger("pwt")


class NtpSyncDriver(Driver):
    def __init__(self, cmd_out_queue, hostname=None, port=123, **kwargs):
        super(NtpSyncDriver, self).__init__(cmd_out_queue, **kwargs)
        self.hostname = hostname or self.parent_state["comm_hostname"]
        self.port = port

    @api_command
    def synchronize_time(self, hostname : str =None, port : int =None):
        """Requests a time offset from NTP server and sets component time offset"""
        logger.debug(f"Current time offset: {self.parent_state['time_offset']}, current time: {time.ctime()}")
        c = ntplib.NTPClient()
        try:
            r = c.request(host=hostname or self.hostname, port=port or self.port)
        except Exception as e:
            logger.error(f"Time sync error: {e}")
            return

        logger.info(f"Time sync from NTP {self.hostname}:{self.port} offset: {r.offset}, corrected time: {time.ctime(time.time()+r.offset)}")
        self.parent_state['time_offset'] = r.offset



