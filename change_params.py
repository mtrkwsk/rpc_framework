import random
import time
import pandas as pd

from pwt.pwtApi import PwtApi

# If run from host (outside docker)
mqtt_host = "rabbitmq"

# If run from docker/jupyter:
mqtt_host = "rabbitmq"

pwt = PwtApi(hostname=mqtt_host, port=1883, verbose=False)

channel = pwt.get_component_by_name('channel')

while True:
    channel.set_driver_parameter(name="channel_gain", value=-12-random.random() * 10)
    time.sleep(1)