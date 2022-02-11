import pandas as pd

from import_data import Data, DataReaktor
import os
from optimize import Optimizer
from linear_system import LinearSystem
import numpy as np
from scipy.interpolate import interp1d
from plots import Plotter, PlotterReaktor


class Measurement:

    def __init__(self, path):
        self.path = path
        self.file_name, _ = os.path.splitext(os.path.split(path)[1])
        self.path_raw, _ = os.path.splitext(os.path.split(path)[0])
        self.path_sim = os.path.join(os.path.dirname(os.path.dirname(path)), 'sim_data')
        self.df_100 = None
        self.df_final = None
        self.sample_data = None

    def calculate_uncertainty(self, guess):
        solution = self.get_solution()
        GCI = self.richardson_extrapolation(solution)
        self.temp(guess, GCI)

    def richardson_extrapolation(self, solution):
        grid_dimensions = [100, 50, 25]
        time_steps = [200, 100, 50]
        mesh_refinement_ratio = grid_dimensions[0] / grid_dimensions[1]
        pressures = []
        safety_factor = 3

        for i in range(len(grid_dimensions)):
            LinearSystem.number_of_cells = grid_dimensions[i]
            Data.number_of_time_steps = time_steps[i]
            self.set_adjusted_data()
            data = LinearSystem(self.df_100, self.sample_data, solution).solve_linear_system()
            pressures.append(data['cell_pressure'])

        # interpolate cell pressures to get same x location as the smallest grid
        length = self.sample_data['length'] * 100
        x_axis = [np.linspace(0, length, grid_dimensions) for grid_dimensions in grid_dimensions]
        f_0 = interp1d(x_axis[0], pressures[0])
        f_1 = interp1d(x_axis[1], pressures[1])
        pressures[0] = f_0(x_axis[2])
        pressures[1] = f_1(x_axis[2])

        order_of_convergence = np.log(abs((pressures[1]-pressures[2]) / (pressures[0]-pressures[1]))) \
                            / np.log(mesh_refinement_ratio)
        p_exact = pressures[0] + (pressures[0] - pressures[1]) \
                                       / (mesh_refinement_ratio**order_of_convergence - 1)
        relative_error_1 = (pressures[1] - pressures[0]) / pressures[0]
        relative_error_2 = (pressures[2] - pressures[1]) / pressures[1]
        GCI_1 = (safety_factor * abs(relative_error_1)) / (mesh_refinement_ratio**order_of_convergence - 1)
        GCI_2 = (safety_factor * abs(relative_error_2)) / (mesh_refinement_ratio**order_of_convergence - 1)
        asymptotic_range = GCI_2 / (mesh_refinement_ratio**order_of_convergence * GCI_1)
        print(f'''
        --- Grid Convergence Study ---
        
        Number of Grids = {len(grid_dimensions)}
        
        Grid Size    Time Step      Quantity (first cell | last cell)
            1           1           {pressures[0][0]:.0f} | {pressures[0][-1]:.0f}
            2           2           {pressures[1][0]:.0f} | {pressures[1][-1]:.0f}
            4           4           {pressures[2][0]:.0f} | {pressures[2][-1]:.0f}
        
        Order of convergence p = {order_of_convergence.mean():.5f}
        
        Richardson Extrapolation: Calculated with the first and second finest grids.
        
                    Quantity (first cell | last cell)
        p_exact     {p_exact[0]:.0f} | {p_exact[-1]:.0f}
        
        Grid Convergence Index - GCI
        Factor of Safety = {safety_factor}
        
        Grid        GCI in % (first cell | last cell | mean)
        1 - 2       {GCI_1[0]*100:.4f} | {GCI_1[-1]*100:.4f} | {GCI_1.mean()*100:.4f}
        2 - 4       {GCI_2[0]*100:.4f} | {GCI_2[-1]*100:.4f} | {GCI_2.mean()*100:.4f}
        
        Check the asymptotic range. A value of 1.0 indicates asymptotic range.
        
        range = {asymptotic_range.mean():.4f}
        
        ''')
        return GCI_1

    def temp(self, guess, GCI, parameter='both'):
        LinearSystem.number_of_cells = 50
        Data.number_of_time_steps = 100
        df_opt = pd.DataFrame()

        for i in range(4):
            self.set_adjusted_data()
            if i == 1:
                self.df_100['Inlet_Pressure'] = (self.df_100['Inlet_Pressure'] +
                                                 self.sample_data['uncertainty_inlet']) * (1 + base_error + GCI[0])
                self.df_100['Outlet_Pressure'] = (self.df_100['Outlet_Pressure'] -
                                                  self.sample_data['uncertainty_outlet']) * (1 - base_error - GCI[-1])
                self.df_100['Temperature'] = self.df_100['Temperature'] - 2
                self.sample_data['length'] = self.sample_data['length'] * 0.995
                self.sample_data['diameter'] = self.sample_data['diameter'] * 1.005
                self.sample_data['inlet_chamber_volume'] = self.sample_data['inlet_chamber_volume'] * 0.99
                self.sample_data['outlet_chamber_volume'] = self.sample_data['outlet_chamber_volume'] * 0.99
            elif i == 2:
                self.df_100['Inlet_Pressure'] = (self.df_100['Inlet_Pressure'] -
                                                 self.sample_data['uncertainty_inlet']) * (1 - base_error - GCI[0])
                self.df_100['Outlet_Pressure'] = (self.df_100['Outlet_Pressure'] +
                                                  self.sample_data['uncertainty_outlet']) * (1 + base_error + GCI[-1])
                self.df_100['Temperature'] = self.df_100['Temperature'] + 2
                self.sample_data['length'] = self.sample_data['length'] * 1.005
                self.sample_data['diameter'] = self.sample_data['diameter'] * 0.995
                self.sample_data['inlet_chamber_volume'] = self.sample_data['inlet_chamber_volume'] * 1.01
                self.sample_data['outlet_chamber_volume'] = self.sample_data['outlet_chamber_volume'] * 1.01
            elif i == 3:
                parameter = 'k'

            result = Optimizer(self.df_100, self.sample_data, guess)
            result, opt_steps = result.nelder_mead(parameter)
            df_opt = pd.concat([df_opt, pd.DataFrame(opt_steps[1:], columns=opt_steps[0])], axis=1)
            base_error = result.fun / 100
            i += 1

        path = os.path.join(self.path_sim, self.file_name + '_uncertainty.txt')
        df_opt.to_csv(path, index=False, float_format='%.6g')
        return df_opt

    def calculate_permeability(self, guess, parameter='k'):
        if self.find_file():
            self.set_adjusted_data()
        else:
            self.set_data()

        result = Optimizer(self.df_100, self.sample_data, guess)
        result, opt_steps = result.nelder_mead(parameter)

        plot = Plotter(self.df_100, **{'name': self.file_name})
        plot.result_chart()

        self.add_results(result, guess)
        user_input = input('Ergebnis abspeichern? (y)')
        if user_input == 'y':
            self.save_adjusted_measurement_file()
            self.save_results()

    def get_solution(self):
        df = pd.read_csv(os.path.join(self.path_sim, self.file_name + '.csv'),
                         nrows=10, sep=':', index_col=0, header=None)
        return [float(df.loc['k', 1]), float(df.loc['n', 1])]

    def set_adjusted_data(self):
        data = Data(self.path)
        self.df_100, self.df_final = data.adjusted_pressure_file()
        self.sample_data = data.sample_data()

    def set_data(self):
        data = Data(self.path)
        self.df_100, self.df_final = data.new_pressure_file()
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

        path = os.path.join(self.path_sim, self.file_name + '.csv')
        del self.sample_data['uncertainty_inlet']
        del self.sample_data['uncertainty_outlet']
        df_res = pd.DataFrame.from_dict(self.sample_data, orient='index')
        df_res.to_csv(path, header=False, sep=':', float_format='%.4f')
        df.to_csv(path, index=False, mode='a', float_format='%.2f')
        self.df_final.describe().to_csv(path, mode='a', float_format='%.2f')

    def save_adjusted_measurement_file(self):
        path = os.path.join(self.path_raw, self.file_name + '_adjusted.csv')
        self.df_final.to_csv(path, sep=',', index=False, float_format='%.2f')

    def find_file(self):
        for root, dirs, files in os.walk(self.path_raw):
            if self.file_name + '_adjusted.csv' in files:
                return True
            else:
                return False


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
        self.df_100, self.df_final = data.new_pressure_file()
        self.sample_data = data.sample_data()

    def save_results(self):
        df = self.df_100[['Duration', 'DateTime', 'Inlet_Pressure', 'Inlet_Pressure_Cal', 'Outlet_Pressure',
                          'Outlet_Pressure_Cal', 'Confining_Pressure_Reactor', 'Confining_Pressure_Sample',
                          'Temperature']]

        path = os.path.join(self.path_sim, self.file_name + '.csv')
        df_res = pd.DataFrame.from_dict(self.sample_data, orient='index')
        df_res.to_csv(path, header=False, sep=':', float_format='%.4f')
        df.to_csv(path, index=False, mode='a', float_format='%.2f')
        self.df_final.describe().to_csv(path, mode='a', float_format='%.2f')
