import pwt_config
import multiprocessing as mp
import argparse
import importlib
import time
import socket
from traceback import format_exc
from inspect import getfullargspec
from typing import Any
# Any.__name__ = 'Any'

from pwt.dynamicAPI import api_command, api_info
from pwt.drivers.driver import Driver, command, threaded, DState
from pwt.logs import config_logger, init_logger

logger = init_logger()




class PwtComponent(Driver):
    def __init__(self, _id=pwt_config.component_id, comm_hostname=pwt_config.mqtt_host):
        print(pwt_config.component_id)
        self.cmd_sink_queue = mp.Queue()
        self.drivers = {}
        super(PwtComponent, self).__init__(cmd_out_queue=None,
                                           cmd_in_queue=self.cmd_sink_queue,
                                           component_id=_id)
        # To usunalem bo byly podwojne logi, jest juz w run()
        # config_logger(logger, hostname=comm_hostname)
        # self.register_driver_lock = mp.Lock()

        self.state["ip_addr"] = pwt_config.get_ip_as_to_mqtt()
        self.state["time_offset"] = 0
        self.state["comm_hostname"] = comm_hostname

        # self.register_driver("CommDriver", autostart=True, hostname=comm_hostname)
        # self.register_driver("NtpSyncDriver", autostart=True)

    def before_run(self):
        self.register_driver("CommDriver", autostart=True,
                             hostname=self.state["comm_hostname"])
        config_logger(self.component_id, logger)
        super().before_run()



    @api_command
    def shutdown(self):
        """Shuts component down"""
        for driver_name in self.drivers:
            self.drivers[driver_name].shutdown()
            self.drivers[driver_name].join()
        # self.process_shutdown.wait(2)

        super().shutdown()


    def start_drivers(self):
        for n, driver in self.drivers.items():
            if not driver.is_alive():
                driver.start()

    def join_drivers(self):
        for n, driver in self.drivers.items():
            pass
            # driver.join()

    def dispatch_command(self, cmd):
        if pwt_config.VERBOSE_COMMAND_DEBUG:
            logger.debug(f"Dispatch: {cmd['cmd']}", extra={'cid': cmd['cid'], 'cmd_name': cmd['cmd']})
        cmd_name = cmd['cmd']
        try:
            driver = api_command.dispatch[cmd_name]
            if pwt_config.VERBOSE_COMMAND_DEBUG:
                logger.debug(f"Found {cmd['cmd']} in driver: {driver}")
        except KeyError:
            logger.error(f"{cmd_name} not found in API!",
                         extra={'cid': cmd['cid'], 'cmd_name': cmd_name})
            return

        # Jesli command jest w pwtComponent, to uruchom bezposrednio:
        if driver == 'PwtComponent':
            super().call_command(cmd)
        else:
            try:
                self.drivers[driver].put_command(cmd)
            except KeyError:
                logger.error(f"Driver {driver} not registered!",
                             extra={'cid': cmd['cid'], 'cmd_name': cmd_name})
                return

    def call_command(self, cmd: dict):
        self.dispatch_command(cmd)

    def start(self):
        self.start_drivers()
        logger.info("Listening to the commands...")
        super().run()
        self.join_drivers()

    @api_command
    def get_state(self):
        """Sends state of the component to the broker"""
        logger.debug('get_state command received.')
        s = {}
        s["PwtComponent"] = self.state.copy()
        for n, driver in self.drivers.items():
            # driver.put_command(command('update_state'))
            s[n] = driver.state.copy()
            s[n]["measurements"]=dict(driver.measurements)
            s[n]["parameters_info"] = dict(driver.parameters_info)
            # driver.update_endpoint_info()
            s[n]["endpoints"] = dict(driver.endpoints_info)
            # s[n]["endpoints"] = dict({})
        # print(s)
        cmd = command('send_state', state=s)
        self.put_command(cmd)

    @api_command
    def get_api_info(self):
        """Sends dynamicAPI data to the broker"""
        logger.debug('get_api_info command received.')
        ai = api_info(api_command)
        cmd = command('send_api_info', ai=ai)
        self.put_command(cmd)
        # print(ai)

    @api_command
    def register_driver(self, driver_name: str, autostart: bool = True, **kwargs: dict):
        """Imports and registers a driver in component"""
        logger.info(f'Registering {driver_name} with args {kwargs} autostart is {autostart}')
        # self.register_driver_lock.acquire()
        module_name = driver_name[0].lower() + driver_name[1:]
        try:
            if driver_name in self.drivers:
                logger.warning(f"Driver {driver_name} already registered! Shutting down...")
                self.shutdown_driver(driver_name=driver_name)

                #self.drivers[driver_name].shutdown()
                # raise ValueError
            module = importlib.import_module('pwt.drivers.' + module_name)
            importlib.reload(module)
            driver_class = getattr(module, driver_name)
            self.drivers[driver_name] = driver_class(cmd_out_queue=self.cmd_sink_queue,
                                                     component_id=self.component_id,
                                                     parent_state=self.state,
                                                     **kwargs)
        except ValueError:
            logger.debug(format_exc())
            logger.error(f"Driver {driver_name} already registered! Shut it down first.")
            return
        except ModuleNotFoundError:
            logger.debug(format_exc())
            logger.error(f'Module {module_name} for driver {driver_name} not found!')
            return
        except AttributeError:
            logger.debug(format_exc())
            logger.error(f"Class for driver {driver_name} not found in {module_name}!")
            return
        except TypeError:
            logger.debug(format_exc())
            logger.error(f"Wrong arguments for init {driver_name}: {kwargs}")
            return
        except Exception as e:
            logger.debug(format_exc())
            logger.error(f"Unexpected exception in registering {driver_name}: {kwargs} : {format_exc()}")
            return



        if autostart:
            self.drivers[driver_name].start()
            while True:
                if self.drivers[driver_name].state["dstate"] == DState.RUNNING:
                    logger.debug(f"Running driver ack {driver_name}")
                    self.get_api_info()
                    break

        # self.register_driver_lock.release()


    @api_command
    def shutdown_driver(self, driver_name: str):
        """Sets process_shutdown event"""
        logger.debug(f"shutdown_driver {driver_name}...")
        try:

            # self.drivers[driver_name].busy_lock.acquire()

            self.drivers[driver_name].shutdown()
            logger.debug("Waiting for process to join()...")
            # self.drivers[driver_name].shutdown_finished_event.wait()
            self.drivers[driver_name].join(timeout=3)
            if self.drivers[driver_name].exitcode is None:
                logger.error(f"{driver_name} didnt join in 3sec and became zombie!")
            else:
                logger.debug(f"{driver_name} gracefully exited with code {self.drivers[driver_name].exitcode}.")
            self.drivers.pop(driver_name)
        except KeyError:
            logger.error(f"Shutdown_driver: {driver_name} not found (not registered?)")

    # @api_command
    # def connect_endpoint(self, hostname : str, port : int, name  : str = None):
    #     """Connects endpoint of the driver (searches for the right name)"""
    #     logger.info(f"Connecting endpoint {name} on {hostname}:{port} ")

    #     # Wylistowanie wszystich ep:
    #     endpoints_client_all = {}
    #     for dn, driver in self.drivers.items():
    #         for ep_name, ep in driver.endpoints_info.items():
    #             if ep['mode'] == 'server':
    #                 continue
    #             else:
    #                 endpoints_client_all[ep_name] = ep
    #                 endpoints_client_all[ep_name]['driver'] = dn


    #     print(endpoints_client_all)
    #     if len(endpoints_client_all) < 1:
    #         print("No endpoint clients found!")
    #         return

    #     if name is not None:
    #         if name in endpoints_client_all:
    #             print(f"EP {name} found in {endpoints_client_all[name]['driver']}")
    #         else:
    #             print(f"EP {name} NOT found in {endpoints_client_all[name]['driver']}")
    #             return
    #     else:
    #         # znajdz pierwszy ep klient do polaczenia
    #         ep = list(endpoints_client_all.values())[0]
    #         print(f"Connect for the first client EP available... {ep['name']}")

    #         self.drivers[ep['driver']].put_command(command('connect_endpoint',
    #                                                        endpoint_name=ep['name'],
    #                                                        port=port,
    #                                                        hostname=hostname))



    #         # print(f"eps: {endpoints_info}")
    #             # if name is None:
    #             #     if len(driver.endpoints_info) > 0:
    #             #         name = list(driver.endpoints_info.keys())[0]
    #             # if name in driver.endpoints_info:
    #             #     driver.put_command(
    #             #         command('connect_endpoint',
    #             #                 endpoint_name=name,
    #             #                 port=port,
    #             #                 hostname=hostname))
    #             #     matched = True
    #             #     break
    #     #
    #     # if not matched:
    #     #     logger.warning(f"Endpoint {name} not found!")


    # @api_command
    # def disconnect_endpoint(self, name : str = None):
    #     """Disconnects endpoint. Finds by name and execute driver's command."""
    #     logger.debug(f"Disconnecting endpoint {name} ")
    #     matched = False
    #     for dn, driver in self.drivers.items():
    #         if name is None:
    #             if len(driver.endpoints_info) > 0:
    #                 name = list(driver.endpoints_info.keys())[0]
    #         if name in driver.endpoints_info:
    #             driver.put_command(
    #                 command('disconnect_endpoint', endpoint_name=name)
    #             )
    #             matched = True
    #             break
    #     if not matched:
    #         logger.warning(f"Endpoint {name} not found!")


    @api_command
    def set_driver_parameter(self, name : str, value : float, d_name : str = None):
        """Sets parameter of a driver. If name of driver not provided, it searchs for a proper one."""
        if d_name:
            self.drivers[d_name].put_command(command("set_parameter", name=name, val=value))
                # self.drivers[d_name].set_parameter(n, v)
        else:
            for dn, driver in self.drivers.items():
                s = driver.parameters_info.copy()
                # print(s)
                if name in s:
                    driver.put_command(command("set_parameter", name=name, val=value))
                    # driver.set_parameter(n, v)

    @api_command
    def set_time_offset(self, value : float):
        """Sets time offset of measurement timestamp field"""
        self.state['time_offset'] = value
        return

    # @api_command
    # def set_measurement(self):
    #     pass
