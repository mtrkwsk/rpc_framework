import pwt_config
from pwt_config import component_id

import logging
import multiprocessing as mp
from pwt.command import command
import paho.mqtt.publish as publish
import time
import json
import socket

# class LoggingNoSendLogFilter(logging.Filter):
#     def filter(self, record):
#         # return True
#         if hasattr(record, 'cmd_name') and record.cmd_name == 'send_log':
#             return False
#         else:
#             return True


class PwtLoggerMqtt(logging.Handler):
    def __init__(self, component_id, hostname=None, port=None):
        logging.Handler.__init__(self)
        self.setLevel('INFO')
        self.formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)-5s %(processName)-14s %(message)s',
                                           datefmt='%m/%d/%Y %I:%M:%S')
        self.client_id = component_id
        self.hostname = hostname or pwt_config.mqtt_host
        self.port = port or pwt_config.mqtt_port
        self.auth = {'username': pwt_config.mqtt_username, 'password': pwt_config.mqtt_password}
        self.connection_failed = False
        # self.client = client.Client()
        # self.client.connect_async(self.host, self.port)
        # self.own_msg_cids = []

    def emit(self, record: logging.LogRecord) -> None:
        # print('log emit')
        topic = 'components/' + self.client_id + '/log/'
        # print(f'Emit logger {self.hostname} {self.port} {self.connection_failed} {topic}')
        if self.connection_failed:
            return
        s = self.formatter.format(record)
        d = {
            "formatted": s,
            "asctime": record.asctime,
            "logger_name": record.name,
            "level_name": record.levelname,
            "process_name": record.processName,
            "message": record.message,
            "thread_name": record.threadName,
            "timestamp": time.time(),
            "component_id": self.client_id
        }
        try:
            publish.single('components/' + self.client_id + '/log/',
                           json.dumps(d),
                           hostname=self.hostname,
                           port=self.port,
                           auth=self.auth,
                           keepalive=60,
                           client_id='')

        except Exception as e:
            self.connection_failed = True
            print(e)
            logging.getLogger('pwt').error(f"Unable to send log to MQTT! ({self.hostname}:{self.port})")


#
#
# class PwtLoggerCmd(logging.Handler):
#     def __init__(self, q):
#         logging.Handler.__init__(self)
#         self.setLevel('INFO')
#         self.addFilter(LoggingNoSendLogFilter())
#         self.formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)-5s %(processName)-14s %(message)s',
#                                            datefmt='%m/%d/%Y %I:%M:%S')
#         self.cmd_queue = q
#
#         # self.own_msg_cids = []
#
#     def emit(self, record: logging.LogRecord) -> None:
#         s = self.formatter.format(record)
#         d = {
#             "formatted": s,
#             "asctime": record.asctime,
#             "logger_name": record.name,
#             "level_name": record.levelname,
#             "process_name": record.processName,
#             "message": record.message,
#             "thread_name": record.threadName
#         }
#         if self.cmd_queue:
#             # if hasattr(record, 'cmd_name') and record.cmd_name == 'send_log':
#             #     return
#             c = command('send_log', log = d)
#             # self.own_msg_cids.append(c['cid'])
#             # if hasattr(record, 'cid'):
#             #     if record.cid in self.own_msg_cids:
#                     # print("looped cid!")
#                     # self.own_msg_cids.pop(self.own_msg_cids.index(record.cid))
#                     # return
#             self.cmd_queue.put(c)


def config_logger(component_id, l, hostname=None, port=None):
    # l.addFilter(LoggingNoSendLogFilter())

    # h = PwtLoggerCmd(self.cmd_sink_queue)
    h = PwtLoggerMqtt(component_id=component_id, hostname=hostname, port=port)
    l.addHandler(h)

class NoSendMeasurementFilter(logging.Filter):
    def filter(self, record):
        return not 'send_measurement' in record.getMessage()

def init_logger():
    l = logging.getLogger('pwt')
    try:
        import coloredlogs
        fs = coloredlogs.DEFAULT_FIELD_STYLES
        fs['levelname']['color'] = 'yellow'
        fs['processName'] = {'color': 'cyan'}
        fs['asctime']['color'] = 'magenta'

        coloredlogs.install(fmt='%(asctime)s %(name)s %(levelname)-7s %(processName)-16s %(threadName)-10s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S',
                            level='DEBUG', logger=l, field_styles=fs)
        l.addFilter(NoSendMeasurementFilter())
    except Exception as e:
        print(e)
        logging.basicConfig(format='%(asctime)s %(name)s %(levelname)-8s %(processName)-10s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S', level=logging.DEBUG)
        pass
    return l