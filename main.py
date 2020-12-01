import pandas as pd
import os
from matplotlib import pyplot as plt


class MeasurementData:

    def __init__(self, path):
        self.path = path
        self.filename, _ = os.path.splitext(path)
        self.start = None
        self.stop = None

    def prepare_data(self, **kwargs):
        kwargs.setdefault('set_start_time_to_max_pressure', True)
        raw_data = self.read_file(self.path)
        converted_data = self.convert_data(raw_data)
        self.set_start_stop(converted_data)
        plot_before_adjustment = Plotter(converted_data,
                                         **{'start': self.start, 'stop': self.stop, 'name': self.filename})
        plot_before_adjustment.plot_measurement_chart()
        time_adjusted_data = converted_data.iloc[self.start:self.stop]
        if kwargs.get('set_start_time_to_max_pressure'):
            final_data = self.set_start_time_to_max_pressure(time_adjusted_data)
        else:
            final_data = self.reset_duration(time_adjusted_data)
        plot_after_adjustment = Plotter(final_data, **{'name': self.filename})
        plot_after_adjustment.plot_measurement_chart()
        return final_data

    @staticmethod
    def read_file(path):
        try:
            df = pd.read_csv(path, sep=' ')
            return df
        except Exception as ex:
            print(f"Exception {type(ex).__name__}, {ex.args}")

    @staticmethod
    def convert_data(df):
        df['temp'] = pd.to_datetime(df['Date'] + df['Time'], format='%d.%m.%Y%X')
        df['Duration'] = pd.to_timedelta(df['temp'] - df['temp'][0]).dt.total_seconds()
        df.drop(['Date', 'Time', 'temp'], axis=1, inplace=True)
        df = df[['Duration', 'Inlet_Pressure', 'Outlet_Pressure', 'Confining_Pressure', 'Temperature']]
        # convert bar (relative) to Megapascal (absolute)
        df[['Inlet_Pressure', 'Outlet_Pressure', 'Confining_Pressure']] = \
            df[['Inlet_Pressure', 'Outlet_Pressure', 'Confining_Pressure']].apply(lambda x: x/10 + 0.0977)
        return df

    def set_start_stop(self, data):
        pressure_max_97 = data['Inlet_Pressure'].max() * 0.97
        pressure_max_index = data['Inlet_Pressure'].idxmax()
        inlet_pressure_starting_at_p_max = data.loc[pressure_max_index:, 'Inlet_Pressure']
        pressure_outlet_max = data.loc[pressure_max_index:, 'Outlet_Pressure']

        data['Start'] = inlet_pressure_starting_at_p_max < pressure_max_97
        data['End'] = inlet_pressure_starting_at_p_max <= pressure_outlet_max
        try:
            self.start = data.index[data['Start'] == True].tolist()[0]
        except:
            self.start = 0
        try:
            self.stop = data.index[data['End'] == True].tolist()[0]
        except:
            self.stop = len(data)
        data.drop(['Start', 'End'], axis=1, inplace=True)

    def set_start_time_to_max_pressure(self, df):
        index_max_pressure = df['Inlet_Pressure'].idxmax()
        time_max_pressure_in_sec = df.loc[index_max_pressure, 'Duration']
        valve_opening_in_sec = df.loc[self.start, 'Duration']

        df = df.loc[index_max_pressure:]
        print(f'Start der Messung {(time_max_pressure_in_sec - valve_opening_in_sec):.0f} sec. nach Ventiloeffnung')
        df = self.reset_duration(df)
        return df

    @staticmethod
    def reset_duration(df):
        df = df.copy()
        df.reset_index(inplace=True, drop=True)
        df['Duration'] = df['Duration'] - df.iloc[0, 0] + 1
        return df

    def get_core_dimensions(self):
        database = self.read_file('database.csv')
        database.set_index('name', inplace=True)
        length = database.loc[self.filename, 'length']
        diameter = database.loc[self.filename, 'diameter']
        gas = database.loc[self.filename, 'gas']
        print(length, diameter, gas)

    def get_chamber_volume(self):
        database = self.read_file('database.csv')
        all_units = self.read_file('measurement_units.csv')
        used_unit = database.loc[self.filename, 'unit']
        filt = all_units['number'] == used_unit
        chamber_volume = all_units.loc[filt, ['inlet_chamber_in_ml', 'outlet_chamber_in_ml']]
        return chamber_volume.values[0]


class Plotter:

    def __init__(self, df, **kwargs):
        self.df = df
        for key, value in kwargs.items():
            setattr(self, key, value)

    def plot_measurement_chart(self):
        plt.figure(figsize=(14,8))
        plt.semilogx(self.df['Duration'], self.df['Inlet_Pressure'], color='C0', linestyle='-')
        plt.semilogx(self.df['Duration'], self.df['Outlet_Pressure'], color='C0', linestyle='-')
        try:
            plt.axvline(x=self.df.iloc[self.start, 0], color='black', linestyle='--')
            plt.axvline(x=self.df.iloc[self.stop - 1, 0], color='black', linestyle='--')
        except:
            pass
        plt.title(self.name, fontsize=16)
        plt.xlabel('Zeit in s', fontsize=16)
        plt.ylabel('Druck in MPa', fontsize=16)
        plt.grid(True, which='major')
        plt.grid(True, which='minor', linestyle='--')
        plt.grid(True)
        plt.show()

    def plot_calculation_chart(self):
        pass

    def plot_calculation_detail_chart(self):
        pass


x = MeasurementData('HY_S3.txt')
x.prepare_data()


