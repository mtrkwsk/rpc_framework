import sys
sys.path.append('../../')

import random
import time
from pwt.dynamicAPI import api_command
from pwt.drivers.driver import Driver, threaded

import logging

logger = logging.getLogger("pwt")


class TestDriver(Driver):
    def __init__(self, cmd_out_queue, multiplier=3, **kwargs):
        super(TestDriver, self).__init__(cmd_out_queue, **kwargs)
        self.state["multiplier"] = self.register_parameter(2, "multiplier", float, (0,1000))
        self.state["param2"] = self.register_parameter(0.5, "param2", float, (0.2, 1.))

        self.parity_counter = self.register_state('parity_counter', 0)
        self.parity_counter.set(0)

        self.register_measurement("multiplier_result",
                                  dtype=float,
                                  range=(0, 50),
                                  label="multiplier result")
        self.register_measurement("parity",
                                  dtype=bool,
                                  label="meas parity")


    def shutdown(self):
        super().shutdown()

    @api_command
    def hello(self):
        """Says hello and send it to logger"""
        print("Hello")
        logger.info("Hello from testDriver!")
        logger.warning("Warning from testDriver!")
        logger.error("ERROR from testDriver!")

    @api_command
    def multiply(self, number: float):
        """Multiplies number by 'multiplier' ONCE and send result as a SINGLE measurement"""
        result = number * self.state["multiplier"]
        self.send_measurement(name="multiplier_result", value=result)

    @threaded
    @api_command
    def multiply_loop(self, number: float, interval : int = 1, shutdown_event=None):
        """Multiplies number by 'multiplier' and send result as measurement in a loop ("""
        logger.info("Threaded multiply")
        self.state["run_loop"] = True
        self.state["parity_counter"] = 0
        while not shutdown_event.is_set():
            result = number * self.state["multiplier"] * random.random()
            if int(result) % 2 == 1:
                logger.warning("Odd number! (an exemplary debug warning here)")
                self.send_measurement(name="parity", value=True)
            else:
                self.parity_counter.set(self.parity_counter.get() + 1)
            self.send_measurement(name="multiplier_result", value=result)
            shutdown_event.wait(interval)

    # @threaded
    # @api_command
    # def socket_perf_send_test(self, n : int, buf_size : int, shutdown_event=None):
    #     """Sends n samples to data socket"""
    #     logger.info('Threaded socket send')
    #     buffer = b'\0' * (1000 * 1000)  # 1 megabyte
    #     buffer = b'\0' * (1000 * 1) # 1 kB
    #     buffer = b'\0' * 1472  # default buffer for uhd driver
    #     buffer = b'\0' * 4 * buf_size
    #     # print(f"send {self.data_pipe_in.fileno()} {self.data_pipe_out.fileno()}")
    #     self.state['run_loop'] = True
    #     for i in range(n):
    #         self.send_data(buffer)
    #         # self.data_pipe_out.send_bytes(buffer)
    #         # time.sleep(0.5)
    #     self.state['run_loop'] = False

    # @api_command
    # def stop_loop(self):
    #     """Stops multiply loop"""
    #     self.state["run_loop"] = False
