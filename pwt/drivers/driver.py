import multiprocessing as mp
import threading
import os
import queue
import atexit
import time
import random
import functools
from typing import Any
from traceback import format_exc

from pwt.logs import config_logger
from pwt.command import command, parse_command
from pwt.dynamicAPI import api_command
import pwt_config

# from iq_streaming.endpoint import Endpoint
# from iq_streaming.endpointManager import EndpointManager
# if pwt_config.ENDPOINT_VERSION == 2:
#     from pwt.endpoint.endpointManager import EndpointManager
# else:
#     from iq_streaming.endpointManager import EndpointManager

import logging

logger = logging.getLogger("pwt")


class DState:
    LOADED = "LOADED"
    INIT = "INIT"
    REGISTERED = "REGISTERED"
    RUNNING = "RUNNING"
    BUSY = "BUSY"
    SHUTDOWN = "SHUTDOWN"


# TODO: Dodac Eventy do shutdownu watkow (jako argument funkcji)
def threaded(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        kwargs["shutdown_event"] = None
        # print(kwargs)
        if not "shutdown_event" in kwargs:
            logger.warning("No shutdown_event in @threaded command")
            func(*args, **kwargs)
            return
        # else:
        if issubclass(args[0].__class__, Driver):
            args[0].run_in_thread(func, *args, **kwargs)
        else:
            func(*args, **kwargs)
            return

    return wrapper

class PwtState():
    mp_state = None
    set_callback = None
    mp_manager = None
    def __init__(self, name, value):
        self._value = value
        self.name = name
        PwtState.mp_state[self.name] = value

    def set(self, value):
        print(f"Setting state {self.name} to {value}")
        self._value = value
        PwtState.mp_state[self.name] = value
        PwtState.set_callback()

    def get(self):
        """Zwraca lokalna wartosc weflug zalozenia, ze state i tak nie moze byc zmieniany z zewnatrz"""
        return self._value

class Driver(mp.Process):
    def __init__(self, cmd_out_queue, cmd_in_queue=None, component_id=None, parent_state=None, port=None, **kwargs):
        super(Driver, self).__init__()
        self.name = self.__class__.__name__
        self.cmd_out_queue = cmd_out_queue
        self.cmd_in_queue = cmd_in_queue or mp.Queue()
        self.component_id = component_id

        self.parent_state = parent_state

        self.process_shutdown = mp.Event()

        mp_manager = mp.Manager()


        self.threads = []
        self.state = mp_manager.dict({})
        PwtState.mp_state = self.state
        PwtState.set_callback = self.update_state
        self.measurements = mp_manager.dict({})
        self.parameters_info = mp_manager.dict({})
        self.endpoints_info = mp_manager.dict({})
        self.dstate = self.register_state('dstate', DState.INIT)
        # self.dstate.set(DState.INIT)

        # self.state["dstate"] = DState.INIT
        self.dstate = "bleble"
        print(mp_manager.list())
        # self.endpoints = mp.Manager().dict()
        # self.endpointManager = EndpointManager(endpoints_out=self.endpoints)
        # self.endpointManager = EndpointManager(port_pool=port,
        #                                        endpoints_info=self.endpoints_info,
        #                                        change_callback=self.update_state,
        #                                        driver_shutdown_event=self.process_shutdown)
        # self.busy_lock = mp.Condition()
        # self.shutdown_finished_event = mp.Event()

        self.new_config_event = mp.Event()

        self.measurements_local = {}

        self.thread_last_timestamps = {}

        # atexit.register(self.clean_up)

    def before_shutdown(self):
        pass

    @api_command
    def shutdown(self):
        """
        Shuts driver down by setting process_shutdown event.
        """
        logger.info(f"{self.name} shutting down")
        # self.shutdown_finished_event.clear()
        # self.state["dstate"] = DState.SHUTDOWN
        # self.endpointManager.stop()
        for t in self.threads:
            logger.debug(f"Thread: shutdown event to {t[0]}")
            t[1].set()
        for t in self.threads:
            # print(f" THR ALIVE: {t[0].is_alive()}")
            logger.debug(f"Thread: Waiting for {t[0]}")
            t[0].join()
            if t[0].is_alive():
                logger.error(f"Thread {t} didnt join in 3sec and became zombie!")
            else:
                logger.debug(f"Thread {t} gracefully finished.")
        # self.data_pipe_in.close()
        # self.data_pipe_out.close()
        self.process_shutdown.set()
        # logger.debug(f"{self.name} cleanup. Driver clean_up")
        # self.shutdown()
        # self.state["dstate"] = DState.REGISTERED
        # self.shutdown_finished_event.set()

        # self.terminate()
        try:
            self.before_shutdown()
        except AttributeError:
            print("No before_shutdown method")

        logger.debug(f"{self.name} finished.")

    def before_run(self):
        PwtState.mp_state = self.state
        PwtState.set_callback = self.update_state
        pass

    def run_in_thread(self, f, *args, **kwargs):
        logger.debug(f"Running method {f.__name__} in a thread.")
        shutdown_event = mp.Event()
        kwargs["shutdown_event"] = shutdown_event
        t = threading.Thread(target=f, args=args, kwargs=kwargs)
        t.name = "T_"+self.name+"_"+str(random.randint(0,9999))
        t.start()
        self.threads.append((t, shutdown_event))

    def run(self):
        # config_logger(self.component_id, logger)
        logger.info(
            f"Running {self.name} process... PID: {os.getpid()}",
        )

        self.before_run()
        # self.endpointManager.start_all()
        self.measurements_local = dict(self.measurements)
        self.state["dstate"] = DState.RUNNING
        while not self.process_shutdown.is_set():
            try:
                cmd = self.cmd_in_queue.get(timeout=1)
                cmd = parse_command(cmd)
                if pwt_config.VERBOSE_COMMAND_DEBUG:
                    logger.debug(
                    f"{self.name}: cmd on queue: {str(cmd)}", extra={"cid": cmd["cid"], "cmd_name": cmd["cmd"]}
                    )

                self.call_command(cmd)
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                self.shutdown()
        # self.shutdown()
        logger.debug('Exiting run routine.')
        # self.clean_up()

    def call_command(self, cmd: dict):
        if pwt_config.VERBOSE_COMMAND_DEBUG:
            logger.debug(f"Calling command {cmd}", extra={"cid": cmd["cid"], "cmd_name": cmd["cmd"]})
        if "cmd" not in cmd:
            logger.error("This is not a command!", extra={"cid": cmd["cid"]})
            return
        try:
            kwargs = {}
            if "args" in cmd:
                kwargs = cmd["args"]
            getattr(self, cmd["cmd"])(**kwargs)
        except TypeError as e:
            # raise Exception('Command ' + str(cmd['cmd']) + ' has wrong arguments!' + str(e))
            logger.debug(format_exc())
            logger.error(
                f'Command {cmd["cmd"]} has wrong arguments! {str(e)}',
                extra={"cid": cmd["cid"], "cmd_name": cmd["cmd"]},
            )
        except Exception as e:
            raise e
        pass

    @threaded
    def put_command_delayed(self, cmd, delay=0, shutdown_event=None):
        """Thread put command on command queue after [delay] seconds. """
        if isinstance(cmd, list): #Jesli mamy liste komend a nie jedna komende
            for e in cmd: # To dla kazdej pozycji w liscie
                if isinstance(e, tuple): # sprawdza czy to tuple
                    shutdown_event.wait(e[1]) # i wtedy przyjmuje ze 2 wartosc w tuple to delay
                    self.cmd_in_queue.put(e[0]) # a pierwsza to komenda
                else: # jesli nie tuple to po prostu komenda
                    shutdown_event.wait(delay) # i wtedy czeka staly delay podany w parametrze
                    self.cmd_in_queue.put(e)
        else: # jak nie lista to po prostu czeka i odpala komende
            shutdown_event.wait(delay)
            self.cmd_in_queue.put(cmd)

    def put_command(self, cmd):
        if isinstance(cmd, list):
            for e in cmd:
                self.cmd_in_queue.put(e)
        else:
            self.cmd_in_queue.put(cmd)

    def send_measurement(self, name, value, **kwargs):
        if self.parent_state and 'time_offset' in self.parent_state:
            offset = self.parent_state['time_offset']
        else:
            offset = 0

        t = time.time() + offset
        j = {"driver": self.name,
             "measurement": name,
             "value": value,
             "timestamp": t,
             "component_id": self.component_id}
        try:
            j.update(self.measurements_local[name])
        except KeyError:
            logger.warning(f"Measurement {name} not registered!")
        j.update(kwargs)
        logger.debug(f"M {j['measurement']}: {j['value']}")
        cmd = command("send_measurement", measurement=j)
        if self.cmd_out_queue:
            self.cmd_out_queue.put(cmd)

    def register_state(self, name, value):
        return PwtState(name=name, value=value)


    # def register_endpoint_send(self, name):
    #     """Registers SEND (server) data endpoint in driver. Starts the thread."""
    #     self.endpointManager.add_endpoint(name=name, type='server')


    # def register_endpoint_recv(self, name):
    #     """Registers RECEIVING (client) data endpoint in driver. Starts the thread."""
    #     self.endpointManager.add_endpoint(name=name, type='client')

    #
    # def send_measurement_endpoint_stats(self):
    #     pass

    def update_state(self):
        """Wysyla polecenie wyslania calego state'a"""
        cmd = command("get_state")
        if self.cmd_out_queue:
            self.cmd_out_queue.put(cmd)

    # @api_command
    # def list_endpoints(self):
    #     """returns comma-separated list of endpoint names"""
    #     # them = ",".join(map(str, self.endpointManager.endpoints.keys()))
    #     them = self.endpointManager.get_list()
    #     return them

    # @api_command
    # def update_endpoint_info(self):
    #     """Gets info from endpoints and update the status. SHOULD BE REMOVED"""
    #     self.endpointManager.get_info()

    # @threaded
    # def connect_endpoint(self, hostname: str, port: int, endpoint_name: str = None):
    #     """Connects to client socket data endpoint to server"""
    #     logger.info(f"EP: Driver {self.name} ep {endpoint_name} connecting to {hostname}:{port}...")

    #     try:
    #         self.endpointManager.connect_client(hostname, port, endpoint_name)

    #     except Exception as e:
    #         logger.error(f"EP: Driver {self.name} ep {endpoint_name} {hostname}:{port} connection failed! {e}")

    # def disconnect_endpoint(self, endpoint_name: str = None):
    #     """Disconnects client endpoint"""
    #     logger.info(f"EP: Driver {self.name} ep {endpoint_name} disconnect.")
    #     try:
    #         self.endpointManager.disconnect_client(endpoint_name)
    #     except Exception as e:
    #         logger.error(f"EP: Driver {self.name} ep {endpoint_name} disconnect failed! {e}")

    # def data_send(self, data, endpoint_name: str = None):
    #     """Sends data by server endpoint"""
    #     return self.endpointManager.data_send(data, endpoint_name)

    # def data_recv(self, count : int=None, endpoint_name: str = None):
    #     """Receive data from endpoint"""
    #     return self.endpointManager.data_recv(count, endpoint_name)

    def register_measurement(self, name, dtype, range=None, active=True, **kwargs):
        """Registers measurement and returns the handler to send it"""
        logger.debug(f"Registering measure {name} ({dtype}) range: {range}, active={active}")
        if name in self.measurements:
            logger.warning(f"Measurement already registered! What now???")
        d = {
            "dtype": str(dtype),
            "range": range,
            "active": active,
        }
        d.update(kwargs)
        self.measurements[name] = d

    def register_parameter(self, val, name, dtype=None, range=None, **kwargs):
        """Registers new parameter along with its info and returns default value"""
        logger.debug(f"Registering parameter {name} ({dtype}) range: {range}")
        if not dtype:
            dtype = type(val)
        if name in self.parameters_info:
            logger.warning(f"Parameter already registered! What now???")
        d = {
            "dtype": str(dtype),
            "range": range,
        }
        d.update(kwargs)
        self.parameters_info[name] = d
        self.state[name] = val
        return val

    def set_parameter(self, name, val):
        """Not in multiprocess! Sets parameter value"""
        logger.info(f"Setting param {name} to {val}.")
        try:
            self.state[name] = val
            # NEW: Measurement feedback!!! TODO: wlaczac/wylaczac te funkcjonalnosc
            self.send_measurement(name=name, value=val)
            print('setting new config event')
            self.new_config_event.set()
        except KeyError:
            logger.error(f"Parameter {name} not found in driver {self.name}!")

    def time_passed(self, t):
        """Returns true if (t)s passed since last function call"""
        # print(threading.currentThread().name)
        # print(self.thread_last_timestamps)

        last_timestamp = self.thread_last_timestamps.get(threading.currentThread().name, 0)
        if time.time() >= last_timestamp + t:
            # print(threading.currentThread().name)
            self.thread_last_timestamps[threading.currentThread().name] = time.time()
            return True
        else:
            return False





