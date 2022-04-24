from pwt.mqttHandler import MqttHandler
from pwt.command import command
from pwt.componentProxy import ComponentProxy
from pwt.tools.smart_find import smart_find
import pwt_config
import json
import time
from typing import List, Dict, Union
import queue
import threading
import paho.mqtt.client as mqtt
import random
from pprint import pprint

client_id = f'pwtapi-python-{random.randint(0, 100)}'

def mqtt_on_message(client, userdata, msg):
    # print(f"{client} MSG received: (" + msg.topic + ") " + str(msg.payload))
    pwt = userdata
    pwt.process_message_queue.put(msg)


class PwtApi():
    instance = None
    mqtt_client = None

    def __init__(self, hostname=None, port=None,
                 username=None, password=None,
                 verbose=False,
                 log_level="ERROR"):

        # if type(self).instance is None:
        #     # Initialization
        #     type(self).instance = self
        # else:
        #     raise RuntimeError("Only one instance of 'Foo' can exist at a time")


        self.process_message_shutdown = threading.Event()
        self.process_message_queue = queue.Queue()

        self.hostname = hostname or pwt_config.mqtt_host
        self.port = port or pwt_config.mqtt_port
        self.username = username or pwt_config.mqtt_username
        self.password = password or pwt_config.mqtt_password
        # self.comm_handler = MqttHandler(hostname=self.hostname, port=self.port,
        #                                 username=self.username, password=self.password, verbose=verbose,
        #                                 msg_queue=self.process_message_queue)

        if PwtApi.mqtt_client is not None:
            PwtApi.mqtt_client.disconnect()

        self.mqtt_client = mqtt.Client(client_id, clean_session=True)
        PwtApi.mqtt_client = self.mqtt_client

        mqtt_connection_thread = threading.Thread(target=self._mqtt_connection_loop, kwargs={'userdata': self})
        mqtt_connection_thread.start()

        process_messages_thread = threading.Thread(target=self._process_message_loop)
        process_messages_thread.start()
        # ComponentProxy.comm_handler = self.comm_handler
        # self.close_components()
        self.components: Dict[str, Union[ComponentProxy, None]] = {}

        # self.log_watcher_thread = None
        # self.log_watcher_queue = queue.Queue()
        # self.log_watcher_shutdown_event = threading.Event()
        self.parameters = {}

        # self.start_log_watcher(log_level=log_level)

        self.verbose = verbose

    def close(self):
        self._mqtt_disconnect()
        self.process_message_shutdown.set()
        time.sleep(1)
        print("PWT closed.")

    def _mqtt_connection_loop(self, userdata):
        # self.msg_queue = msg_queue or queue.Queue()
        self.mqtt_client.user_data_set(userdata)
        self.mqtt_client.username_pw_set(self.username, self.password)
        self.mqtt_client.on_message = mqtt_on_message

        try:
            self.mqtt_client.connect(self.hostname, self.port)
        except Exception as e:
            print (e)
            return False
        # self.mqtt_client.subscribe("lobby/components")
        self.mqtt_client.subscribe("#")
        print(f"Connected to MQTT on {self.hostname}")

        self.mqtt_client.loop_forever(retry_first_connection=False)
        print('MQTT: loop_forever finished.')

    def _mqtt_disconnect(self):
        self.mqtt_client.disconnect()

    def _process_message(self, msg : mqtt.MQTTMessage):
        p = msg.payload.decode()
        try:
            jl = json.loads(p)
        except json.JSONDecodeError:
            jl = p

        output_line = ''
        if "log" in msg.topic:
            # Otrzymano log
            output_line = f"[LOG] {msg.topic.split('/')[1]}: {jl['level_name']} {jl['message']}"
            print(f"{msg.topic.split('/')[1]} \x1b[31m {jl['level_name']} \x1b[0m : {jl['message']}")
        elif "measurement" in msg.topic:
            # Otrzymano pomiar
            output_line = f"[ M ] {msg.topic.split('/')[1]}: {jl}"
            component_name = msg.topic.split('/')[1]
            # print(f"!! {component_name}")
            c = self.get_component_by_name(component_name)
            c.add_measurement(jl)

        elif "lobby/components" in msg.topic:
            output_line = f"[LOBBY] {msg.topic}: "

            if type(jl) == str:
                # Otrzymano nazwe komponentu po przywitaniu na lobby
                output_line += str(jl)
                self.add_component(name=jl)
            elif type(jl) == dict:
                # Otrzymano api_info:
                component_name = msg.topic.split('/')[-1]
                output_line += f"{component_name} api_info (truncated)"
                c = self.get_component_by_name(component_name)
                c.update_from_api_info(jl)
                # pprint(jl)
            else:
                print('Process Message: different format.')
        elif "lobby" in msg.topic:
            # Otrzymano cos na ogolnym lobby
            output_line = f"[LOBBY-ALL] {msg.topic}: "
            output_line += str(jl) if len(str(jl)) < 20 else "api_info (truncated)"
        elif "state" in msg.topic:
            # Otrzymano zmiane STATE
            output_line = f"[S] {msg.topic.split('/')[1]}: State Received (truncated)"
            if type(jl) == dict:
                component_name = msg.topic.split('/')[1]
                c = self.get_component_by_name(component_name)
                c.update_from_state(jl)
            else:
                print('Process Message: different format.')
        if self.verbose:
            print(output_line)
        # print(jl)

    def _process_message_loop(self):
        while not self.process_message_shutdown.is_set():
            try:
                msg = self.process_message_queue.get(timeout=0.2)
                self._process_message(msg)
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                print('Kbd break')
                break
        pass

    def discover_components(self, timeout=0.5):
        """Retrives component list from server, populates internal component list and returns it."""
        # self.close_components()
        # self.components = []
        self.mqtt_client.publish("lobby", "hello")
        time.sleep(timeout)
        pprint(self.components)
        for c in self.components.values():
            c.update()

        # components = self.comm_handler.publish_and_receive("lobby", "hello", "lobby/components", timeout=1)
        # for c in components:
        #     self.components.append(self.get_component_proxy(c))
        # print(f"Components: {self.components}")
        # return self.components

    def add_component(self, name):
        if name in self.components:
            print(f"Component {name} already on the list.")
        else:
            self.components[name] = ComponentProxy(name=name, mqtt_client=self.mqtt_client)
        return self.components[name]


    def close_components(self):
        if hasattr(self, "components"):
            for c in self.components:
                c.close()

    def get_component_proxy(self, c_name : str, **kwargs):
        """Returns component proxy object for desired component name. Doesn't update internal compnent list."""
        return ComponentProxy(c_name, self.comm_handler, **kwargs)

    def connect_client(self, c : ComponentProxy, hostname, port):
        c.send_command("connect_endpoint", port=port, hostname=hostname)


    def connect_components(self, c_send : ComponentProxy, c_recv : ComponentProxy):
        # TODO: Automat do dobierania odpowiednich endpointow

        ep_send_info = None
        ep_recv_info = None
        for e in c_send.endpoints.values():
            if e['mode'] == 'server':
                ep_send_info = e
                break

        for e in c_recv.endpoints.values():
            if e['mode'] == 'client':
                ep_recv_info = e
                break

        print(f"send_ep of {c_send.name}: {ep_send_info['name']}")
        print(f"recv_ep of {c_recv.name}: {ep_recv_info['name']}")

        if not (ep_send_info or ep_recv_info):
            print("Unable to match endpoints!")
            return

        print(f"Connecting {c_recv.name} {ep_recv_info['name']} to {c_send.name}: {ep_send_info['name']} - "
              f"{c_send.ip_addr}:{ep_send_info['port']}")

        c_recv.send_command("connect_endpoint", port=ep_send_info['port'], hostname=c_send.ip_addr)

        # if send_comp_ep_name and recv_comp_ep_name:
        #     print(f"Send component {c_send} ep: {send_comp_ep_name}")
        #     print(f"Recv component {c_recv} ep: {recv_comp_ep_name}")
        #     c_send.connect_endpoint(name=send_comp_ep_name, port=3003)
        #     c_recv.connect_endpoint(name=recv_comp_ep_name, port=3003, hostname=c_send.ip_addr)


    def connect_endpoints(self, ep_send : str, ep_receive : str):
        pass

    def connect_rf(self):
        pass

    def start_log_watcher(self, log_level='ERROR', output_widget=None):
        """Starts thread which gets component log from server"""
        if not self.log_watcher_thread:
            topic = "components/" + "*" + "/log/"
            args = (topic,
                    self.log_watcher_queue,
                    self.log_watcher_shutdown_event)
            # if output_widget:
            #     args += (output_widget, )

            self.log_watcher_thread = threading.Thread(
                target=self.comm_handler.subscribe_and_put,
                args=args,
                kwargs={'output_widget': output_widget, 'log_level': log_level},
                daemon=False)
            self.log_watcher_thread.start()
        else:
            print('Log watcher is already working!')

    def get_component_by_name(self, name):
        c = smart_find(list(self.components.keys()), name)
        if c:
            # print(f"Component found: {self.components[c]}")
            return self.components[c]
        else:
            print(f"Component {name} not found in discovered components.")

        print("Adding it anyway...")
        self.add_component(name=name)
        self.components[name].update()
        return self.components[name]

    # creates API parameter
    # and bounds (on change) methods - defines what methods needs to be executed when parameter is modified
    # methods must have only one argument - "value"
    def register_parameter(self, name, methods):
        self.parameters[name] = {"methods": methods, 'value': None}

    # sets value of API parameter
    # and executes bounded methods with value argument
    def set_parameter(self, name, value):
        self.parameters[name]['value'] = value
        for method in self.parameters[name]['methods']:
            method(value)

    def update_parameter(self, name, value):
        if self.parameters[name]['value'] != value:
            self.set_parameter(name, value)
            return True
        return False

    # returns API parameter value
    def get_parameter(self, name):
        return self.parameters[name]['value']


if __name__ == "__main__":
    pwt = PwtApi()
    components = pwt.discover_components()
    print(components)
    components[0].send_command('get_api_info')

    components[1].register_driver(driver_name="PythonDriverTx2", sample_rate=10_000_000)
    components[0].register_driver(driver_name="PythonDriverRx2")
    components[1].set_driver_parameter(name="sample_rate", value=30_000_000)
    time.sleep(6)
    pwt.connect_components(components[1], components[0])
    # components[0].register_driver(driver_name="TestDriver")

    time.sleep(2)
    # c.info()
    components[0].get_log()
    components[1].get_log()