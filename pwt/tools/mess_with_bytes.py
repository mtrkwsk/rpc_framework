import random

def mess_with_data(data, rate):
    data_corrupted = list(str(data))
    for i, b in enumerate(data):
        if random.random() < rate:
            print(b)
            data_corrupted[i] = 'x'
    return (''.join(data_corrupted)).encode()




data = b"\x00\x00\x00\x00\x00\x00\x00\x00d\x00\x00\x00E\x00\x00x\x00\x01\x00\x00@\x06\xfb~\x00\x00\x00\x00\x7f\x00\x00\x01\x00\x14\x00P\x00\x00\x00\x00\x00\x00\x00\x00P\x02 \x00S\xaa\x00\x00{'id': 'vehicle_123', 'pos_lon': 54.5523456650717, 'pos_lat': 88.27876616655537}"
mess_with_data(data, 0.03)