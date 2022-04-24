import pwt_config
import random
from paho.mqtt import client as mqtt_client
import atexit
import json
import socket
import time
from pwt.dynamicAPI import api_command
from pwt.drivers.driver import Driver

import logging
logger = logging.getLogger('pwt')


class CommDriver(Driver):

    def __init__(self, component_id = None, cmd_out_queue = None, hostname=None, **kwargs):
        super(CommDriver, self).__init__(cmd_out_queue, **kwargs)

        self.hostname = hostname or pwt_config.mqtt_host
        self.component_id = component_id

        logger.info(f'CommDriver component id: {self.component_id}')
        self.mqtt_client = None
        # atexit.register(self.clean_up)

    def shutdown(self):
        self.clean_up()
        super().shutdown()

    def clean_up(self):
        logger.debug("commDriver cleanup.")
        try:
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
        except Exception as e:
            print (f"cleanup excpetion: {e}")
        # super().clean_up()

    def before_run(self):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info(f"Connected to MQTT Broker! {self.hostname}")
            else:
                logger.error("Failed to connect, return code %d\n", rc)

        self.mqtt_client = mqtt_client.Client(self.component_id)
        self.mqtt_client.username_pw_set(pwt_config.mqtt_username, pwt_config.mqtt_password)
        self.mqtt_client.on_connect = on_connect
        try:
            self.mqtt_client.connect(self.hostname, pwt_config.mqtt_port)
        except ConnectionRefusedError:
            logger.error('Unable to connect to the MQTT Broker! (ConnectionRefused)')
        except socket.error as e:
            logger.error('Unable to connect to the MQTT Broker! '+str(e))


        def on_message(client, userdata, msg):
            logger.info(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
            self.handle_message(msg)

        #self.client.subscribe('#') # e.g. subscribe([("my/topic", 0), ("another/topic", 2)])
        self.mqtt_client.subscribe([("lobby", 1), ("components/" + self.component_id + "/cmd", 1)])
        self.mqtt_client.on_message = on_message
        self.mqtt_client.loop_start()

    def handle_message(self, msg):
        logger.debug("Handling msg from MQTT...")

        if mqtt_client.topic_matches_sub('lobby', msg.topic) and msg.payload.decode() == 'hello':
            self.greeting()
        # if mqtt_client.topic_matches_sub('components/'+self.client_id, msg.topic):
        #     logger.debug('ITS ME')
        if mqtt_client.topic_matches_sub('components/' + self.component_id + '/cmd/#', msg.topic):
            cmd = msg.payload.decode()
            logger.debug('Parsing command: ' + cmd)
            cmd = json.loads(cmd)
            self.cmd_out_queue.put(cmd)

    def greeting(self):
        logger.info(f'Sending greeting from {self.component_id}')
        self.mqtt_client.publish('lobby/components', str(self.component_id))

    @api_command
    def send_measurement(self, measurement : dict):
        """Sends measurement to components/[component_id]/measurements/ topic"""
        logger.debug('Publishing send_measurement.')
        self.mqtt_client.publish('components/' + self.component_id + '/measurements/', json.dumps(measurement))

    @api_command
    def send_state(self, state : dict):
        """Sends state to components/[component_id]/state"""
        logger.debug('Publishing state.')
        self.mqtt_client.publish('components/' + self.component_id + '/state/', json.dumps(state))

    @api_command
    def send_api_info(self, ai : dict):
        """Sends api info to the broker"""
        logger.debug('Publishing api_info.')
        self.mqtt_client.publish('lobby/components/' + self.component_id, json.dumps(ai))

    @api_command
    def send_log(self, log : dict):
        """Sends log entry to the broker"""
        logger.debug(f"Publishing log - {log['message']}")
        self.mqtt_client.publish('components/' + self.component_id + '/log/', json.dumps(log))