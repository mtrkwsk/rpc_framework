import numpy as np

"""
Misc
"""

def data_info(data):
    print(type(data))


"""
Conversions 
"""

def sc16q11_to_cdb64(data):
    return (
            np.frombuffer(data, dtype=np.int16)
            .astype(np.float32) / 2048
            )\
        .view(np.complex64)


def cdb64_to_sc16q11(data):
    return bytearray(
        (
        np.frombuffer(
            memoryview(data), dtype=np.float32
            ).astype(np.float16) * 2048
        )
                .astype(np.int16)
                .tobytes()
    )

"""
File load/save
"""

def load_file(filename):
    if '.bin' in filename:
        load_file_bin(filename)
    elif '.tdms' in filename:
        load_file_tdms(filename)
    elif '.npy' in filename:
        load_file_tdms(filename)
    else:
        print('File format not recognized!')

    pass

def save_file(filename):
    pass

def load_file_bin(filename):
    pass

def save_file_bin(filename):
    pass

def load_file_tdms(filename):
    pass

def save_file_tdms(filename):
    pass

def load_file_npy(filename):
    pass

def save_file_npy(filename):
    pass
