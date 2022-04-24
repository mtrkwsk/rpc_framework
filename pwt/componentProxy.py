import functools
from inspect import signature, Parameter, Signature
from pwt.command import command
import json
import threading
import queue
import time
import atexit
from collections import deque

MEASUREMENT_QUEUE_MAXLEN=100

class ComponentProxy:

    def __init__(self, name, mqtt_client=None):
        self.name = name
        # self.comm_handler = None
        self.mqtt_client = mqtt_client

        # To be updated by _update_info method
        self.api_info = {}
        self.state = {}
        self.endpoints = {}
        self.parameters = {}
        self.measurements = {}
        self.ip_addr = None

        # self.update()

        # self.measurement_watcher_thread = threading.Thread()
        # self.measurement_watcher_queue = queue.Queue()
        # self.measurement_watcher_shutdown_event = threading.Event()
        # self.last_measurements = []
        # self.start_measurement_watcher()

        self.measurements_queue = deque(maxlen=MEASUREMENT_QUEUE_MAXLEN)

    def __repr__(self):
        return f"ComponentProxy({self.name})"

    def update(self, timeout=0.1):
        """Request (get) update from component, update internal vars. Wait for response for timeout[s]"""
        print(f"Updating component {self.name} proxy...")
        if self.mqtt_client:
            self.send_command("get_api_info")
            self.send_command("get_state")
        else:
            print("ERROR: Component Proxy does not have Communication Handler")
        time.sleep(timeout)
        # self.update_from_api_info(self.api_info)
        # self.update_from_state(self.state)

    def update_from_api_info(self, api_info : dict):
        """Process dict in api_info format and updates internal api_info var."""
        print(f"{self.name} component proxy info updated from remote api_info call.")
        self.api_info = api_info
        self._populate_methods(api_info)

    def update_from_state(self, state : dict):
        """Process state dict in api format and updates internal state var including
        ip_addr, endpoints, parameters and meas """
        self.state = state
        for d, v in state.items():
            if "ip_addr" in v:
                self.ip_addr = v['ip_addr']
            if "endpoints" in v:
                self.endpoints.update(v["endpoints"])
            if "parameters_info" in v:
                self.parameters.update(v["parameters_info"])
                for m in v["parameters_info"]:
                    self.parameters[m]["value"] = v[m]
            if "measurements" in v:
                self.measurements.update(v["measurements"])

    def info(self, get_update=True, hide_drivers_details=['PwtComponent', 'CommDriver']):
        """Requests update (if get_update=True) and prints nicely info about component"""
        if get_update:
            self.update()
        print(f'Component: {self.name} :')
        for d, v in self.state.items():
            print(f'  {d} ({v["dstate"]})')
            if 'ip_addr' in v:
                print(f"   IP: {v['ip_addr']}")
            if d in hide_drivers_details:
                print ("\t... (truncated)")
                continue
            if "endpoints" in v:
                for e, ev in v["endpoints"].items():
                    # print(ev)
                    print(f'\t EP {ev["name"]:15} mode:{ev["mode"]:7} ({ev["status"]:7}) {ev["hostname"]}:{ev["port"]}')
            if "parameters_info" in v:
                for p, pv in v["parameters_info"].items():
                    print(f'\t P  {p:15} {pv["dtype"]:8} {pv["range"]} = {v[p]}')
            if "measurements" in v:
                for m, mv in v["measurements"].items():
                    print(f'\t M  {m:15} {mv["dtype"]:8} {mv["range"]}')
            for c, cv in self.api_info.items():
                if cv["class"] == d:
                    print(f'\t C  {c:15} {list(cv["args"].keys())}  {cv["doc"]}')

    def send_command(self, cmd_name, **kwargs):
        """Sends command as mqtt message in a proper format and on a proper topic"""
        cmd = command(cmd_name, **kwargs)
        if self.mqtt_client:
            self.mqtt_client.publish("components/"+self.name + "/cmd", json.dumps(cmd))
        else:
            print("Send command: No mqtt_client available for component.")

    def get_parameter(self, name):
        return self.parameters[name]["value"]

    # returns setter method for specific parameter of this component
    # usage:
    #   test_setter = self.get_param_setter("test")
    #   test_setter(2) <=> self.set_parameter("test", 2)
    def get_param_setter(self, param):
        def setter(value):
            self.set_parameter(param, value)
        return setter

    def set_parameter(self, name, val):
        # cmd = command()
        self.send_command("set_driver_parameter", name=name, value=val)
        # def set_driver_parameter(self, name: str, value: float, d_name: str = None):

    def update_parameter(self, name, val):
        actual = self.get_parameter(name)
        if actual != val:
            self.set_parameter(name, val)
            return True
        return False

    def close(self):
        """Closes ... nothing now"""
        pass
        # print("Closing watcher threads.")
        # self.log_watcher_shutdown_event.set()
        # self.measurement_watcher_shutdown_event.set()

    # def _update_info(self):
    #     if self.mqtt_client:
    #         self.send_command("get_api_info")
    #         self.send_command("get_state")
    #     else:
    #         print("ERROR: Component Proxy does not have Communication Handler")
    #     return self.api_info, self.state

    def _populate_methods(self, api_info=None):
        ai = api_info or self.api_info
        for cmd, desc in ai.items():
            self._make_method(cmd, desc['args'])

    def _make_method(self, name, params):
        # fp = functools.partial(self._send_command_prototype, _cmd_name=name, _params=params)
        fp = functools.partial(self.send_command, cmd_name=name)
        self.__setattr__(name, fp)
        ps = []
        for pn, pt in params.items():
            if pn == 'kwargs':
                continue
            ps.append(Parameter(pn, Parameter.POSITIONAL_OR_KEYWORD, annotation=pt))
        # print(name + "  " + str(Signature(ps)))
        self.__getattribute__(name).__signature__ = Signature(ps)
        # self.__getattribute__(name).__doc__ = "aaa"




    # def _send_command_prototype(self, _cmd_name, _params, **kwargs):
    #     # print(_cmd_name + 'SC: ', kwargs, self.comm_handler)
    #     # self.comm_handler.send_command(self.name, _cmd_name, **kwargs)
    #     # print(_params)
    #     # print(kwargs)
    #     self.send_command(_cmd_name,**kwargs)

    # def record_measurements(self, output_widget=None, verbose=False):
    #     """Starts thread which gets component log from server"""
    #     if not self.measurement_watcher_thread.is_alive():
    #         topic = "components/" + self.name + "/measurements/"
    #         args = (topic,
    #                 self.measurement_watcher_queue,
    #                 self.measurement_watcher_shutdown_event)
    #
    #         with self.measurement_watcher_queue.mutex:
    #             self.measurement_watcher_queue.queue.clear()
    #
    #         self.measurement_watcher_shutdown_event.clear()
    #         self.measurement_watcher_thread = threading.Thread(
    #             target=self.comm_handler.subscribe_and_put,
    #             args=args,
    #             kwargs={'output_widget': output_widget, 'verbose': verbose},
    #             daemon=False)
    #         self.measurement_watcher_thread.start()
    #     else:
    #         print('measurement watcher is already working!')
    #
    # def stop_measurements(self):
    #     if self.measurement_watcher_thread.is_alive():
    #         self.measurement_watcher_shutdown_event.set()
    #         self.measurement_watcher_thread.join()
    #         print(f"Collected {self.measurement_watcher_queue.qsize()} measurements.")
    #
    #     else:
    #         print('Measurement thread is not working!')

    def add_measurement(self, m):
        # print(m)
        self.measurements_queue.append(m)
        return True

    def get_measurements(self, n=0):
        """returns the last n(default=all) measurements"""
        return list(self.measurements_queue)[-n:]

    def clear_measurements(self):
        self.measurements_queue.clear()

    def parameter_slider(self, name=None):
        import ipywidgets as widgets

        def f(pn, x):
            print(x)
            self.set_parameter(pn, x)

        p = self.parameters[name]
        if p['range']:
            r = p['range']
        else:
            r = (-10, 30)

        if 'int' in p['dtype']:
            w = widgets.interactive(f, pn=widgets.fixed(name),
                                x=widgets.IntSlider(min=r[0], max=r[1], step=1, value=p['value'],
                                                    continuous_update=False))
        elif 'float' in p['dtype']:
            w = widgets.interactive(f, pn=widgets.fixed(name),
                                    x=widgets.FloatSlider(min=r[0], max=r[1], step=0.01, value=p['value'],
                                                          continuous_update=False))
        return(w)




    #
    # def params_sliders(self):







