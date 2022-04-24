import numpy as np
import math
from iq_streaming.tools import data_info
import time


def split_to_packets(a, packet_size):
    splits = [packet_size * i for i in range(1, math.ceil(len(a) / packet_size))]
    return np.split(a, splits)


def lcm(a, b):
    return abs(a * b) // math.gcd(a, b)


class SignalGenerator:
    def __init__(self, sample_rate=None, signal_freq=None, signal_mag=None):
        self.sample_rate = int(sample_rate) if sample_rate else None
        self.signal_freq = int(signal_freq) if signal_freq else None
        self.signal_buffer = np.array([0])
        self.signal_mag = signal_mag or 1.0

        # Pomysl zeby generowac autonatycznie os x dla wykresow:
        self.last_len = 0
        pass

    def generate(self, sample_rate=None, signal_freq=None, signal_mag=None, dtype=np.complex64):
        """Creates one period of signal and fills the buffer"""
        print(sample_rate)
        if sample_rate is not None:
            self.sample_rate = int(sample_rate)
            self.signal_freq = int(signal_freq)
        self.signal_mag = self.signal_mag or float(signal_mag)
        # print(self.sample_rate / self.signal_freq)
        # print(f"GCD: {math.gcd(self.sample_rate, self.signal_freq)}")
        # To jest bufor ktory po wysylaniu z okreslonym sample_ratem powinien dac dana czestotliwosc
        print(f"Generating signal: rate: {self.sample_rate} freq: {self.signal_freq} mag: {self.signal_mag}")
        if math.gcd(self.sample_rate, self.signal_freq) == 1:
            print("Warning: sampling rate does not match desired signal frequency!")
        # limit magnitude to avoid overflow value: 0.99999 (< -0.0001 dB compared to 1.0)
        magnitude = self.signal_mag if self.signal_mag < 1.0 else 0.99999
        if dtype in [np.complex64, np.complex128]:
            self.signal_buffer = magnitude * np.exp(
                2j * np.pi * np.arange(self.sample_rate / self.signal_freq, dtype=dtype)
                * self.signal_freq / self.sample_rate, dtype=dtype)
        elif dtype == np.int16:
            self.signal_buffer = magnitude * np.sin(
                2 * np.pi * self.signal_freq * np.arange(self.sample_rate / self.signal_freq, dtype=np.int16)
                / self.sample_rate)
        print(f"  Signal_buffer len: {len(self.signal_buffer)}")
        print(f"  Signal_buffer len: {np.dtype(self.signal_buffer[0])}")

    def convert_buffer(self, format="SC16_Q11"):
        if format == "SC16_Q11":
            self.signal_buffer_original = self.signal_buffer.copy()
            self.signal_buffer = bytearray((np.frombuffer(memoryview(self.signal_buffer_original), dtype=np.float32).astype(np.float16) * 2048).astype(np.int16).tobytes())
        else:
            print("Format not supported.")

        print(f"Signal buffer converted: len {len(self.signal_buffer_original)} -> {len(self.signal_buffer)}")

    def get_next(self, packet_size=None, delay=None, duration=None):
        """Generator which yields next sample from the buffer"""
        duration_in_samples = None
        samples_sent = 0
        if duration:
            duration_in_samples = int(duration * self.sample_rate)

        if packet_size:
            i = 1
            start = 0
            while True:
                if duration and duration_in_samples - samples_sent <= packet_size:
                    yield self.get_n_samples(n=duration_in_samples - samples_sent, start=start)
                    break
                # yield b'\0'*packet_size

                yield self.get_n_samples(n=packet_size, start=start)
                samples_sent += packet_size
                # print(start)
                start = i * (packet_size % lcm(len(self.signal_buffer), packet_size))

                i = (i + 1) % len(self.signal_buffer)
                if delay:
                    time.sleep(delay)
        else:
            i = 0
            while True:
                try:
                    yield self.signal_buffer[i]
                    i += 1
                    if delay:
                        time.sleep(delay)

                except IndexError:
                    if len(self.signal_buffer) == 0:
                        print("Signal buffer is empty!")
                        return 0
                    else:
                        i = 0
        return False

    def get_sample(self, n=None, dtype=None):
        """ returns n-th sample of the buffer (circular way)"""
        try:

            return self.signal_buffer[n % len(self.signal_buffer)]
        except IndexError:
            print("index error")
        except Exception as e:
            print(e)

    def get_n_samples(self, n, start=0):
        """ returns (n) samples of the signal"""
        if len(self.signal_buffer) == 0:
            return None
        times = n // len(self.signal_buffer) + 1
        # print('times ',times)
        return self.get_buffer(times=times, start=start)[0:n]

    def get_buffer(self, times=1, start=0):
        """ returns repeated (times) times buffer from start point"""
        start = start % len(self.signal_buffer)
        if type(self.signal_buffer) == np.ndarray:
            return np.tile(np.append(self.signal_buffer[start:], self.signal_buffer[:start]), times)
        elif type(self.signal_buffer) == bytearray:
            # print("buff", self.signal_buffer)
            # print("aa", start, times)
            # print("buff ret", (self.signal_buffer[start:] + self.signal_buffer[:start]) * times)

            return (self.signal_buffer[start:] + self.signal_buffer[:start]) * times
        #
        # if times == 1 :
        #     if start == 0:
        #         return self.signal_buffer
        #     else:
        #         return np.append(self.signal_buffer[start:], self.signal_buffer[:start])
        # if start == 0:
        #     return np.tile(self.signal_buffer, times)
        # else:
        #     return np.tile(np.append(self.signal_buffer[start:], self.signal_buffer[:start]), times)

    def get_n_packets(self, n, packet_size):
        """ returns (n) packets of (packet_size) size"""
        return split_to_packets(self.get_n_samples(n * packet_size), packet_size)

    def get_duration(self, t, packet_size=None, output_time=False):
        """ returns signal repeated to achieve duration (t) seconds. Optionally grouped into packets of (packet_size) size"""
        n = t * self.sample_rate

        if isinstance(n, float):
            nr = math.floor(n)
            delta = (n - nr) / self.sample_rate
            if delta != 0:
                print('WARNING: duration does not multiply the signal period!')
                return (self.get_n_samples(n=nr), delta)
            else:
                n = int(n)

        if output_time:
            return (self.get_n_samples(n=n), np.linspace(0, t, n))
        else:
            return self.get_n_samples(n=n)

    def load_from_file(self, filename, sample_rate, convert_to_bytes=True):
        print(f"Loading from file {filename}, sample rate {sample_rate}")

        if '.bin' in filename:
            try:
                f = open(filename, 'rb')
                self.signal_buffer = bytearray(f.read())
                f.close()
            except FileNotFoundError:
                print('File not found!!!')
                return False
        elif '.npy' in filename:
            try:
                self.signal_buffer = np.load(filename)
            except FileNotFoundError:
                print('File not found!!!')
                return False
            self.sample_rate = sample_rate
        elif '.tdms' in filename:
            self.load_tdms(filename, sample_rate)
        else:
            print('File format not recognized!')
            return False

        self.sample_rate = sample_rate
        print(f"Signal loaded, len: {len(self.signal_buffer)}")

        if convert_to_bytes and type(self.signal_buffer) != bytearray:
            print('Converting...')
            self.convert_buffer(format="SC16_Q11")


        return True

    def load_tdms(self, filename, sample_rate):
        from nptdms import TdmsFile
        data = np.array([])
        print(f"Loading TDMS {filename}")
        with TdmsFile.open(filename) as tdms_file:
            all_groups = tdms_file.groups()
            print(f" Groups: {all_groups}")
            print(f" Channel in group [0]: {all_groups[0].channels()}")
            print(f" Channel [0][0] name: {all_groups[0].channels()[0].name}")
            print(f" Channel [0][0] properties: {all_groups[0].channels()[0].properties}")
            print(f" Channel [0][0] path: {all_groups[0].channels()[0].path}")
            print(f" Channel [0][0] data len: {len(all_groups[0].channels()[0][:])}")
            data = np.array(all_groups[0].channels()[0][:]).astype(np.complex64)
        self.signal_buffer = data
        self.sample_rate = sample_rate

    # def get_sample(self, n=None, times=None, packets=None, duration=None, samples=None, packet_size=None, dtype=None):
    #
    #             """
    #         Get the signal in form of:
    #         - no args - the buffer
    #         - (n)-th sample of the buffer
    #         - repeated the buffer (times) times
    #         - list of (packets) packets filled with generated signal
    #         - signal repeated with the duration of (duration)
    #         - (samples) samples of repeated signal
    #         if packet_size is 0, the whole buffer is returned,
    #         otherwise buffer is devided on (packet_size) packets and returned as a list
    #         each sample is in format of (dtype)
    #         """
    # pass
