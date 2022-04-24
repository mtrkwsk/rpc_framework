import uuid
from pwt.command import command

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--mqtt", help="Address of MQTT broker")
parser.add_argument("-d", "--debug", action="store_true", help="Output debug logs")
parser.add_argument("-c", "--component", help="Sets component name (id)")
parser.add_argument("-f", "--fff", help="a dummy argument to fool ipython", default="1")

args = parser.parse_args()

component_id = args.component or "component_"+uuid.uuid1().hex[2:10]

mqtt_host = args.mqtt or "localhost"
mqtt_port = 1883

mqtt_username = "user"
mqtt_password = "password"

VERBOSE_COMMAND_DEBUG = False
VERBOSE_REGISTER_API = False

# 1 or 2
ENDPOINT_VERSION = 2

commands = []
commands.append(command('get_state'))

import socket
def get_ip_as_to_mqtt():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect((mqtt_host, 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()


    return IP
