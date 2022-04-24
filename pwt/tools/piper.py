import sys
import time
import os
import multiprocessing as mp


n = 10
buffer = b'\0' * (1000*1000) # 1 megabyte
buffer = b'\0' * (1) # 1

def print_elapsed(name, start):
    elapsed = time.time() - start
    spi = elapsed / n
    ips = n / elapsed
    print(f'{name}: {spi*1000:.3f} ms/item, {ips:.0f} item/sec')

class Driver1(mp.Process):
    def __init__(self, name):

        self.pipe_out, self.pipe_in = mp.Pipe()
        super(Driver1, self).__init__()
        self._name = name

    def run(self):
        for i in range(n):
            print(f"Producer {self._name} sends")
            # q_out.send(f"msg from {name}")
            self.pipe_out.send(buffer)

class Driver2(mp.Process):
    def __init__(self, name):
        self._name = name
        self.pipe_out, self.pipe_in = mp.Pipe()
        super(Driver2, self).__init__()

    def run(self):
        while True:
            for r in mp.connection.wait([self.pipe_in], timeout=1):
                try:
                    rcvd = self.pipe_in.recv()
                    print(f"Consumer {self._name} : {rcvd}")
                except EOFError:
                    print('EOFERROR')



if __name__ == "__main__":
    p_out, p_in = mp.Pipe(duplex=True)

    d1 = Driver1('d1')
    d2 = Driver2('d2')

    d1.start()
    d2.start()





