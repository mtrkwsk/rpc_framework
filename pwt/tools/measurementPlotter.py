import threading
import matplotlib.pyplot as plt
import random
import time
import queue
# from jupyterplot import ProgressPlot

class MeasurementPlotter():
    """Get(s) queues to observe and plot them on a common figure"""

    def __init__(self, q=None):
        self.queues = []
        if q:
            self.queues.append(q)

        self.plot_thread = None
        self.shutdown_event = threading.Event()
        self.fig = None

        self.thread_q = queue.Queue()

        self.measurement_data = {}

    def add_queue(self, q):
        self.thread_q.put(q)

    def start(self):
        plt.ion()
        self.fig = plt.figure(figsize=(5, 2))
        # pp = ProgressPlot()
        # self.fig.autofmt_xdate()
        kwargs = {
            'shutdown_event': self.shutdown_event,
            'thread_queue': self.thread_q,
            'fig': self.fig,
        }
        self.plot_thread = threading.Thread(target=self.run, kwargs=kwargs)
        print("Starting plotter...")
        self.plot_thread.start()

    def run(self, shutdown_event=None, thread_queue=None, fig=None):
        print("Running plotter thread...")
        q_to_watch = []
        axx = fig.add_subplot(1, 1, 1)
        axises = {}
        lines = {}

        while not shutdown_event.is_set():
            #Adding new queues to watch:
            if not thread_queue.empty():
                ele = thread_queue.get(block=False)
                if isinstance(ele, queue.Queue):
                    print("New queue to watch: " + str(ele))
                    q_to_watch.append(ele)

            for q in q_to_watch:
                if not q.empty():
                    m = q.get(block=False)
                    #jesli mielismy juz taki measurement:
                    if m['measurement'] in self.measurement_data.keys():
                        #jesli mamy juz dany component
                        if m['component_id'] in self.measurement_data[m['measurement']]:
                            self.measurement_data[m['measurement']][m['component_id']]['y'].append(m['value'])
                            self.measurement_data[m['measurement']][m['component_id']]['x'].append(m['timestamp'])
                            self.measurement_data[m['measurement']][m['component_id']]['line'].set_xdata(
                                self.measurement_data[m['measurement']][m['component_id']]['x'])
                            self.measurement_data[m['measurement']][m['component_id']]['line'].set_ydata(
                                self.measurement_data[m['measurement']][m['component_id']]['y'])

                        else:
                            ax = axises[m['measurement']]
                            self.measurement_data[m['measurement']][m['component_id']] = {}
                            self.measurement_data[m['measurement']][m['component_id']]['y'] = [m['value']]
                            self.measurement_data[m['measurement']][m['component_id']]['x'] = [m['timestamp']]
                            self.measurement_data[m['measurement']][m['component_id']]['line'] = ax.plot(m['timestamp'],
                                                                                                         m['value'])[0]

                    else:
                        ax = axx.twinx()
                        axises[m['measurement']] = ax
                        self.measurement_data[m['measurement']] = {}
                        self.measurement_data[m['measurement']][m['component_id']] = {}
                        self.measurement_data[m['measurement']][m['component_id']]['y'] = [m['value']]
                        self.measurement_data[m['measurement']][m['component_id']]['x'] = [m['timestamp']]
                        self.measurement_data[m['measurement']][m['component_id']]['line'] = ax.plot(m['timestamp'], m['value'])[0]

                    print(m)
                    print(self.measurement_data)


            pass
        print("Quitting plotter thread...")


    def stop(self):
        print("Stopping plotter thread...")
        plt.close(self.fig)
        self.shutdown_event.set()


def random_measurement(amount, scale=1):
    for i in range(0,amount):
        value = random.random() * scale
        m = random.choice(['random1', 'random2'])
        c = random.choice(['comp1', 'comp2'])
        j = {"driver": "RandomMeasurement", "measurement": m, "value": value, "timestamp": time.time(),
         "component_id": c}
        yield j








