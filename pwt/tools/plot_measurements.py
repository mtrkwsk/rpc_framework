import pandas as pd
import numpy as np
import time
from copy import deepcopy
import matplotlib.pyplot as plt


colors = ['b', 'r', 'g', 'c']
lines = ['-', '--', ':', '-.']
markers = ['o', 'v', '^', ',']

def plot_measurements(components=[], names=[], drawstyle='default'):

    fig, ax = plt.subplots(figsize=(15, 4))


    if type(components) != list:
        components = [components]

    if type(names) != list:
        names = [names]

    # Pobranie pomiarow z komponentow - get_measurements
    meas_list = []
    components_list = []
    meas_list = []
    for c in components:
        ml = deepcopy(c.get_measurements())

        for m in ml:
            m['component'] = c.name

        meas_list.extend(ml)
        components_list.append(c.name)
        # print (c.measurements)



    # konwersja na format pandasowy - nalezy zadbac zeby to juz bylo polaczone w jedna liste!
    df = pd.DataFrame(meas_list)


    try:
        if len(names) == 0:
            # print(df.measurement.unique())
            names.extend(df.measurement.unique())

        # czas wzgledem pierwszego pomiaru:
        df["timestamp"] = df["timestamp"] - df["timestamp"].min()
        # zamiana bool na int
        try:
            df['value'] = df['value'].astype(float) * 1
        except TypeError:
            print('Warning: some values are not numbers!')

    except KeyError:
        print('Measurement parsing error!')
        return None

    print(names, components_list)
    for im, m in enumerate(names):
        for ic, c in enumerate(components_list):
            if m not in list(df.measurement[df['component']==c]):
                continue

            style = colors[im % len(colors)] + markers[ic % len(markers)] + lines[ic % len(lines)]
            try:
                try:
                    label=df[(df['measurement'] == m) & (df['component'] == c)]['label'][0]
                except Exception as e:
                    label = f"{m} ({c})"
                new_ax = ax.twinx()
                new_ax.spines['left'].set_position(('axes', 1.1))
                df[(df['measurement'] == m) & (df['component'] == c)].plot(x='timestamp', y='value',
                                                                           ax=new_ax,
                                                                           sharex=True,
                                                                           style=style,
                                                                           label=label,
                                                                           grid=True,
                                                                           drawstyle=drawstyle)
            except TypeError:
                print (f'Warning: problem with meas {m} in component {c}')

    return df

