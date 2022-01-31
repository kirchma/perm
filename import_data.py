import os.path
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
import datetime as dt

from plots import Plotter


class Data:

    def __init__(self, path):
        self.path = path
        self.file_name, _ = os.path.splitext(os.path.split(path)[1])
        self.start = None
        self.stop = None

    @staticmethod
    def read_file(path):
        try:
            df = pd.read_csv(path, sep=' ')
            return df
        except Exception as ex:
            print(f'Exception {type(ex).__name__}, {ex.args}')

    @staticmethod
    def convert_units(df):
        df['DateTime'] = pd.to_datetime(df['Date'] + df['Time'], format='%d.%m.%Y%X')
        df['Duration'] = pd.to_timedelta(df['DateTime'] - df['DateTime'][0]).dt.total_seconds()
        df.drop(['Date', 'Time'], axis=1, inplace=True)
        df = df[['Duration', 'DateTime', 'Inlet_Pressure', 'Outlet_Pressure', 'Confining_Pressure', 'Temperature']]
        # convert bar (relative) to Pascal (absolute) and °C to K
        df[['Inlet_Pressure', 'Outlet_Pressure', 'Confining_Pressure']] = \
            df[['Inlet_Pressure', 'Outlet_Pressure', 'Confining_Pressure']].apply(lambda x: x * 1e5 + 97700)
        df['Temperature'] = df['Temperature'] + 273.15
        return df

    def adjust_measurement_interval(self, df):
        self.set_start_stop(df)
        self.set_start_stop_manual(df)
        df = df.iloc[self.start:self.stop]
        print(df.describe())
        df = self.reset_duration(df)
        return df

    def set_start_stop_manual(self, df):
        while True:
            plot = Plotter(df, **{'start': self.start, 'stop': self.stop, 'name': self.file_name})
            plot.raw_data_chart()
            user_input = input('Ist die Messzeit in Ordnung? (y) falls nicht bitte neue Werte für Beginn und '
                               'Ende der Messung angeben (start, ende)')
            if user_input == 'y':
                break
            else:
                start, stop = user_input.split(',')
                if start.isdigit() & stop.isdigit():
                    self.start = df['Duration'].sub(int(start)).abs().idxmin()
                    self.stop = df['Duration'].sub(int(stop)).abs().idxmin()
                elif start.isdigit():
                    self.start = df['Duration'].sub(int(start)).abs().idxmin()
                elif stop.isdigit():
                    self.stop = df['Duration'].sub(int(stop)).abs().idxmin()
        return user_input

    def set_start_stop(self, df):
        df['open'] = df['Inlet_Pressure'] < df['Inlet_Pressure'].max() * 0.98
        open = df.index[df['open'] == True].tolist()[0]
        self.start = df.iloc[open:]['Inlet_Pressure'].idxmax()

        df['pressure_equilibrium'] = df['Inlet_Pressure'] <= df['Outlet_Pressure']
        try:
            self.stop = df.index[df['pressure_equilibrium'] == True].tolist()[0]
        except:
            self.stop = len(df)
        df.drop(['open', 'pressure_equilibrium'], axis=1, inplace=True)

    @staticmethod
    def interpolate(df):
        start_date_in_seconds = (df['DateTime'] - dt.datetime(1970,1,1)).dt.total_seconds()[0] - 1
        time_log_scale = np.geomspace(1, int(df['Duration'].max()), 100).round(2)

        function_inlet = interp1d(df['Duration'], df['Inlet_Pressure'])
        function_outlet = interp1d(df['Duration'], df['Outlet_Pressure'])
        function_confining = interp1d(df['Duration'], df['Confining_Pressure'])
        function_temperature = interp1d(df['Duration'], df['Temperature'])

        inlet_log_scale = function_inlet(time_log_scale)
        outlet_log_scale = function_outlet(time_log_scale)
        confining_log_scale = function_confining(time_log_scale)
        temperature_log_scale = function_temperature(time_log_scale)

        df = pd.DataFrame(np.array([time_log_scale, inlet_log_scale, outlet_log_scale,
                                    confining_log_scale, temperature_log_scale]).T,
                          columns=['Duration', 'Inlet_Pressure', 'Outlet_Pressure',
                                   'Confining_Pressure', 'Temperature'])
        df['DateTime'] = pd.to_datetime(df['Duration']+start_date_in_seconds, unit='s')

        return df

    @staticmethod
    def reset_duration(df):
        df = df.copy()
        df.reset_index(inplace=True, drop=True)
        df['Duration'] = df['Duration'] - df.iloc[0]['Duration'] + 1
        return df

    def pressure_data(self):
        df = self.read_file(self.path)
        df = self.convert_units(df)
        df_final = self.adjust_measurement_interval(df)
        df_final_100 = self.interpolate(df_final)
        return df_final_100, df_final

    def sample_data(self):
        my_dict = self.get_core_dimensions()
        unit = self.get_unit_dimensions()
        my_dict.update({'inlet_chamber_volume': unit[0],
                        'outlet_chamber_volume': unit[1]})
        return my_dict

    def get_core_dimensions(self):
        database = self.read_file('database.csv')
        database.set_index('name', inplace=True)

        length = database.loc[self.file_name, 'length']
        diameter = database.loc[self.file_name, 'diameter']
        area = np.pi * 0.25 * diameter**2
        gas = database.loc[self.file_name, 'gas']
        my_dict = {'length': length,
                   'diameter': diameter,
                   'area': area,
                   'gas': gas}
        return my_dict

    def get_unit_dimensions(self):
        database = self.read_file('database.csv')
        units = self.read_file('measurement_units.csv')
        ml_to_m3 = 1e-6

        database.set_index('name', inplace=True)
        unit = database.loc[self.file_name, 'unit']
        filt = units['number'] == unit
        volume = units.loc[filt, ['inlet_chamber_in_ml', 'outlet_chamber_in_ml']]
        return volume.values[0] * ml_to_m3

