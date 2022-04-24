#connecting RabbitMQ
import paho.mqtt.client as mqtt
import time
import random
import json
import queue
import threading
from threading import Event

def on_message(client, userdata, msg):
    # if userdata['verbose']:
    #     print(f"{client} MSG received: (" + msg.topic + ") " + str(msg.payload))
    p = msg.payload.decode()
    try:
        jl = json.loads(p)
    except Exception:
        jl = p
    output_line = "?"
    if "log" in msg.topic:
        # TODO:
        # tutaj mamy zmienna userdata.get('log_level') w ktorej zapisany jest slownie
        # level do ktorego powinnismy wyswietlac. Zrobic sprawdzenie tego levelu i wyswietlac
        output_line = f"[LOG] {msg.topic.split('/')[1]}: {jl['level_name']} {jl['message']}"
    elif "measurement" in msg.topic:
        output_line = f"[ M ] {msg.topic.split('/')[1]}: {jl}"
    elif "lobby" in msg.topic:
        output_line = f"[ LOBBY ] {msg.topic}: "
        output_line += str(jl) if len(str(jl))<20 else "api_info (truncated)"
    elif "state" in msg.topic:
        output_line = f"[ S ] {msg.topic.split('/')[1]}: State Received (truncated)"
    # messages
    else:
        pass
        # output_line = f"[ ? ] {msg.topic.split('/')[1]}: {p}"
    if userdata.get('output_widget') is not None:
        userdata['output_widget'].append_display_data(output_line)
        # with userdata['output_widget']:
        #     print(output_line)
    else:
        if userdata['verbose']:
            print(output_line)

    

    userdata['queue'].put(jl)


class MqttHandler():
    client_id = f'python-mqtt-{random.randint(0, 100)}'
    def __init__(self, hostname, port, username, password, verbose=False, msg_queue=None):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.verbose = verbose

        self.new_msg_event = Event()

        self.client = mqtt.Client(self.client_id)
        self.msg_queue = msg_queue or queue.Queue()
        userdata = {'queue': self.msg_queue,
                    'verbose': self.verbose,
                    'new_msg_event': self.new_msg_event}
        self.client.user_data_set(userdata)
        self.connect()

        self.port_pool = [6000,6002,6003,6004,6005]



    def connect(self, c=None):
        client = c or self.client
        client.username_pw_set(self.username, self.password)
        try:
            client.connect(self.hostname, self.port)
        except Exception as e:
            print (e)
            return False

        print(f"Connected to MQTT on {self.hostname}")
        return client


    def publish_and_receive(self, p_topic, p_msg, r_topic, timeout=1):
        self.client.reconnect()
        # if not self.client.is_connected():
        #     self.connect()

        self.client.subscribe(r_topic)
        self.client.on_message = on_message
        if type(p_msg) is dict:
            p_msg = json.dumps(p_msg)
        message_info = self.client.publish(p_topic, p_msg)
        while not message_info.is_published():
            self.client.loop()
        self.client.loop_start()
        time.sleep(timeout)
        self.client.loop_stop()
        self.client.unsubscribe(r_topic)
        msgs = []
        while not self.msg_queue.empty():
            msgs.append(self.msg_queue.get(timeout=0))
        return msgs


    def send_command(self, component_id, cmd, **kwargs):
        self.client.reconnect()
        # if not self.client.is_connected():
        #     self.connect()
        if type(cmd) is dict:
            cmd_d = cmd
        else:
            cmd_d = {'cmd': cmd,
                     'args': kwargs}
        print(f'Sending {cmd_d} to {component_id}')
        message_info = self.client.publish("components/" + component_id + "/cmd", json.dumps(cmd_d), qos=2)
        # !!! wazne:
        while not message_info.is_published():
            self.client.loop()
        # self.client.loop_start()
        time.sleep(0.1)
        # self.client.loop_stop()
        # self.client.loop(timeout=0.2)

    def subscribe_and_put(self, topic, q : queue, shutdown_event : threading.Event, **kwargs):
        """BLOCKING loop, creates a new client, subscribes on topic and msgs to the q queue"""
        print(f'Subscribing to {topic}')
        client = mqtt.Client('q_watcher'+topic)
        client = self.connect(client)
        client.on_message = on_message
        client.subscribe(topic)
        userdata = {'queue': q,
              'verbose': self.verbose}
        userdata.update(kwargs)
        client.user_data_set(userdata)
        try:
            while not shutdown_event.is_set():
                # client.loop(timeout=0.1)
                shutdown_event.wait(0.1)
                client.loop()
        except (KeyboardInterrupt, SystemExit):
            shutdown_event.set()
        client.on_message=None
        client.disconnect()
        print(f"Subscriber {'q_watcher' + topic} ended.")






    # def connect_components(self, server_id, client_id):
    #     port = self.port_pool.pop(random.randrange(len(self.port_pool)))
    #     print (f'Connecting {server_id} and {client_id} on port {port}')
    #     self.send_command(server_id, 'sock_server_start', port=port)
    #     self.send_command(client_id, "sock_client_send", port=port)

    # def get_api_info(self, component_id):
    #     global ai
    #     def on_message(client, userdata, msg):
    #         global ai
    #         print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
    #         ai = msg.payload.decode()
    #
    #     client = self.connect()
    #     client.subscribe("lobby/components/"+component_id)
    #     client.on_message = on_message
    #     self.send_command(component_id, 'get_api_info')
    #     client.loop_start()
    #     time.sleep(1)
    #     client.loop_stop()
    #     return(ai)
    #
    # def get_state(self, component_id):
    #     global ai
    #     def on_message(client, userdata, msg):
    #         global ai
    #         print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
    #         ai = msg.payload.decode()
    #
    #     client = self.connect()
    #     client.subscribe("components/"+component_id+"/state")
    #     client.on_message = on_message
    #     self.send_command(component_id, 'get_state')
    #     client.loop_start()
    #     time.sleep(1)
    #     client.loop_stop()
    #     return(ai)
    #


    # def discover_components(self):
    #     components = []
    #     def on_message(client, userdata, msg):
    #         print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
    #         components.append(msg.payload.decode())
    #
    #     client = self.connect()
    #     client.subscribe("lobby/components")
    #     client.on_message = on_message
    #     client.publish("lobby", "hello")
    #     client.loop_start()
    #     time.sleep(1)
    #     client.loop_stop()
    #     print(components)
    #     return components