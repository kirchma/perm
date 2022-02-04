import pandas as pd

from import_data import Data, DataReaktor
import os
from optimize import Optimizer
from plots import Plotter, PlotterReaktor


class Measurement:

    def __init__(self, path):
        self.path = path
        self.file_name, _ = os.path.splitext(os.path.split(path)[1])
        self.df_100 = None
        self.df_final = None
        self.sample_data = None

    def calculate_permeability(self, guess, parameter='k'):
        self.set_data()
        result = Optimizer(self.df_100, self.sample_data, guess)
        result = result.nelder_mead(parameter)

        plot = Plotter(self.df_100, **{'name': self.file_name})
        plot.result_chart()

        self.add_results(result, guess)
        self.save_adjusted_measurement_file()
        self.save_results()

    def set_data(self):
        data = Data(self.path)
        self.df_100, self.df_final = data.pressure_data()
        self.sample_data = data.sample_data()

    def add_results(self, result, guess):
        try:
            porosity = result.x[1]
        except:
            porosity = guess[1]
        self.sample_data.update({'k': result.x[0],
                                 'n': porosity,
                                 'error': result.fun / 100})

    def save_results(self):
        df = self.df_100[['Duration', 'DateTime', 'Inlet_Pressure', 'Inlet_Pressure_Cal', 'Outlet_Pressure',
                          'Outlet_Pressure_Cal', 'Confining_Pressure', 'Temperature']]

        path = '/Users/mkirch/OneDrive/Promotion/PERM/sim_data/' + self.file_name + '.csv'
        df_res = pd.DataFrame.from_dict(self.sample_data, orient='index')
        df_res.to_csv(path, header=False, sep=':', float_format='%.4f')
        df.to_csv(path, index=False, mode='a', float_format='%.2f')
        self.df_final.describe().to_csv(path, mode='a', float_format='%.2f')

    def save_adjusted_measurement_file(self):
        path = '/Users/mkirch/OneDrive/Promotion/PERM/raw_data/' + self.file_name + '_adjusted.csv'
        self.df_final.to_csv(path, sep=',', index=False, float_format='%.2f')


class MeasurementReaktor(Measurement):

    def calculate_permeability(self, guess, parameter='k'):
        self.set_data()
        result = Optimizer(self.df_100, self.sample_data, guess)
        result = result.nelder_mead(parameter)

        plot = PlotterReaktor(self.df_100, **{'name': self.file_name})
        plot.result_chart()

        self.add_results(result, guess)
        self.save_adjusted_measurement_file()
        self.save_results()

    def set_data(self):
        data = DataReaktor(self.path)
        self.df_100, self.df_final = data.pressure_data()
        self.sample_data = data.sample_data()

    def save_results(self):
        df = self.df_100[['Duration', 'DateTime', 'Inlet_Pressure', 'Inlet_Pressure_Cal', 'Outlet_Pressure',
                          'Outlet_Pressure_Cal', 'Confining_Pressure_Reactor', 'Confining_Pressure_Sample',
                          'Temperature']]

        path = '/Users/mkirch/OneDrive/Promotion/PERM/sim_data/' + self.file_name + '.csv'
        df_res = pd.DataFrame.from_dict(self.sample_data, orient='index')
        df_res.to_csv(path, header=False, sep=':', float_format='%.4f')
        df.to_csv(path, index=False, mode='a', float_format='%.2f')
        self.df_final.describe().to_csv(path, mode='a', float_format='%.2f')
