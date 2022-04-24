import time
from multiprocessing import Process, Queue, Pipe
import socket
import sys
import random
import threading
import queue

desired_sample_rate = 20_000_000
# How many bytes does 1 sample take:
bytes_in_type = 1 # double
# Buffer size in samples:
n_samples = (1000 * 1000) # 1 megabyte
n_samples = 1472 # default for uhd driver
n_samples = 4096
# n_samples = 128



print(f"Expected delay: {(n_samples*1000*1000)/desired_sample_rate} us")

buffer = b'\0' * bytes_in_type * n_samples
# buffer = b'\0' * 4096
def samples_for_buff(sr, buffer):
    """Calculates sample amount for desired sample rate and buffer"""
    bs = sys.getsizeof(buffer)
    n = round(sr / bs) * 10 # Multiplied by 10 to average
    # print(f"{n} samples to send")
    return(n)

n = samples_for_buff(desired_sample_rate, buffer)


def print_elapsed(name, start):
    elapsed = time.time() - start
    spi = elapsed / n
    ips = n / elapsed
    bytesps = ips * n_samples / 1000000
    time.sleep(1*random.random())
    print(f'{name}: {spi*1000:.3f} ms/item, {ips:.0f} item/sec, {bytesps:.1f} MSa/s')

def producer_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    time.sleep(2)
    s.connect(('127.0.0.1', 6999))
    start = time.time()
    ii = 0
    for i in range(n):
        try:
            ii = ii +1
            s.send(buffer)
        except ConnectionResetError:
            print(ii)
    s.close()
    print_elapsed(f'producer sent {ii} samples:', start)

def consumer_socket():
    b_size = sys.getsizeof(buffer)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.bind(('127.0.0.1', 6999))
    s.listen()
    c, a = s.accept()
    ii = 0
    start = time.time()
    for i in range(n):
        ii = ii + 1
        out = c.recv(b_size)

    print_elapsed(f'consumer received {ii} samples', start)
    time.sleep(2)
    s.close()


def producer(q):
    start = time.time()
    for i in range(n):
        q.put(buffer)
    print_elapsed('producer', start)

def consumer(q):
    start = time.time()
    for i in range(n):
        out = q.get()
    print_elapsed('consumer', start)

class PipeQueue():
    def __init__(self, **kwargs):
        self.out_pipe, self.in_pipe = Pipe(**kwargs)
    def put(self, item):
        self.in_pipe.send_bytes(item)
    def get(self):
        return self.out_pipe.recv_bytes()
    def close(self):
        self.out_pipe.close()
        self.in_pipe.close()

class QQueue():
    def __init__(self, **kwargs):
        self.q = Queue()
    def put(self, item):
        self.q.put(item)
    def get(self):
        return self.q.get()
    def close(self):
        pass


if __name__ == '__main__':
    # print('pipe duplex=True')
    # q = PipeQueue(duplex=True)
    # producer_process = Process(target=producer, args=(q,))
    # consumer_process = Process(target=consumer, args=(q,))
    # consumer_process.start()
    # producer_process.start()
    # consumer_process.join()
    # producer_process.join()
    # q.close()
    #
    # print('pipe duplex=False')
    # q = PipeQueue(duplex=False)
    # producer_process = Process(target=producer, args=(q,))
    # consumer_process = Process(target=consumer, args=(q,))
    # consumer_process.start()
    # producer_process.start()
    # consumer_process.join()
    # producer_process.join()
    # q.close()

    # print('==== Multiprocess Queue')
    # q = QQueue()
    # producer_process = Process(target=producer, args=(q,))
    # consumer_process = Process(target=consumer, args=(q,))
    # consumer_process.start()
    # producer_process.start()
    # consumer_process.join()
    # producer_process.join()
    #
    # print('==== Multiprocess Socket')
    # producer_process = Process(target=producer_socket)
    # consumer_process = Process(target=consumer_socket)
    # consumer_process.start()
    # producer_process.start()
    # consumer_process.join()
    # producer_process.join()
    #
    # print('==== Threaded Queue')
    # q = QQueue()
    # producer_process = threading.Thread(target=producer, args=(q,))
    # consumer_process = threading.Thread(target=consumer, args=(q,))
    # consumer_process.start()
    # producer_process.start()
    # consumer_process.join()
    # producer_process.join()
    #
    print('==== Threaded Socket')
    producer_process = threading.Thread(target=producer_socket)
    consumer_process = threading.Thread(target=consumer_socket)
    consumer_process.start()
    producer_process.start()
    consumer_process.join()
    producer_process.join()

    # x = queue.Queue()
    # def f(x):
    #     x.put(b'\0'*4096*1)
    #     return 2
    #
    # x2 = queue.Queue()
    # def g(x2):
    #     try:
    #         x2.get_nowait()
    #     except queue.Empty:
    #         pass
    #
    # x3 = queue.Queue()
    # def z(x3):
    #     x3.put(b'\0' * 4096 * 1)
    #     try:
    #         x3.get_nowait()
    #     except queue.Empty:
    #         pass


    # import timeit
    # import time
    # print('a')
    # # print(timeit.timeit('f(x)', globals=globals(), number=1_000_000))
    # # print(timeit.timeit('g(x)', globals=globals(), number=1_000_000))
    # # print(timeit.timeit('z(x)', globals=globals(), number=1_000_000))
    # # print(timeit.timeit('print("a")', globals=globals(), number=1_000))
    # print(timeit.timeit('time.sleep(0)', globals=globals(), number=1_000_000))



