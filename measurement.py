import pandas as pd

from import_data import Data, DataReaktor
import os
from optimize import Optimizer
from linear_system import LinearSystem
import numpy as np
from plots import Plotter, PlotterReaktor

import settings


class Measurement:

    def __init__(self, path):
        self.path = path
        self.file_name, _ = os.path.splitext(os.path.split(path)[1])
        self.path_raw, _ = os.path.splitext(os.path.split(path)[0])
        self.path_sim = os.path.join(os.path.dirname(os.path.dirname(path)), 'sim_data')
        self.df_100 = None
        self.df_final = None
        self.sample_data = None

    def richardson_extrapolation(self, solution):
        grid_dimensions = [100, 50, 25]
        time_steps = [200, 100, 50]
        mesh_refinement_ratio = (grid_dimensions[0] / grid_dimensions[1]) * (time_steps[0] / time_steps[1])
        pressures = []
        safety_factor = 1.25

        for i in range(len(grid_dimensions)):
            LinearSystem.number_of_cells = grid_dimensions[i]
            Data.number_of_time_steps = time_steps[i]
            self.set_adjusted_data()
            data = LinearSystem(self.df_100, self.sample_data, solution).solve_linear_system()
            pressures.append(data['cell_pressure'])

        points = np.array([[pressures[0][0], pressures[0][-1]],
                           [pressures[1][0], pressures[1][-1]],
                           [pressures[2][0], pressures[2][-1]]])

        order_of_convergence = abs(np.log(abs((points[1] - points[2]) / (points[0] - points[1]))) \
                                   / np.log(mesh_refinement_ratio))
        p_exact = points[0] + (points[0] - points[1]) \
                  / (mesh_refinement_ratio ** order_of_convergence - 1)
        relative_error_1 = abs((points[1] - points[0]) / points[0])
        relative_error_2 = abs((points[2] - points[1]) / points[1])
        GCI_1 = (safety_factor * abs(relative_error_1)) / (mesh_refinement_ratio ** order_of_convergence - 1) * 100
        GCI_2 = (safety_factor * abs(relative_error_2)) / (mesh_refinement_ratio ** order_of_convergence - 1) * 100
        asymptotic_range = GCI_2 / (mesh_refinement_ratio ** order_of_convergence * GCI_1)

        df = pd.DataFrame(
            [points[0], points[1], points[2], p_exact, order_of_convergence, GCI_1, GCI_2, asymptotic_range]).T
        df.columns = ['p_fine', 'p_medium', 'p_coarse', 'p_exact', 'order_of_convergence', 'GCI_1', 'GCI_2', 'range']
        df.to_csv(self.path_sim + '//a.csv', index=False, float_format='%.6g')

        print(f'''
        --- Grid Convergence Study ---

        Number of Grids = {len(grid_dimensions)}

        Grid Size    Time Step      Quantity (first cell | last cell)
            1           1           {points[0][0]:.0f} | {points[0][-1]:.0f}
            2           2           {points[1][0]:.0f} | {points[1][-1]:.0f}
            4           4           {points[2][0]:.0f} | {points[2][-1]:.0f}

        Order of convergence p = {order_of_convergence[0]:.5f} | {order_of_convergence[-1]:.5f}


        Richardson Extrapolation: Calculated with the first and second finest grids.

                    Quantity (first cell | last cell)
        p_exact     {p_exact[0]:.0f} | {p_exact[-1]:.0f}

        Grid Convergence Index - GCI
        Factor of Safety = {safety_factor}

        Grid        GCI in % (first cell | last cell | mean)
        1 - 2       {GCI_1[0]:.4f} | {GCI_1[-1]:.4f}
        2 - 4       {GCI_2[0]:.4f} | {GCI_2[-1]:.4f}

        Check the asymptotic range. A value of 1.0 indicates asymptotic range.

        range = {asymptotic_range[0]:.4f} | {asymptotic_range[-1]:.4f}

        ''')

    def calculate_uncertainty(self, parameter='k'):
        df_opt = pd.DataFrame()

        for i in range(17):
            self.set_adjusted_data()
            settings.init()
            try:
                t_max = self.df_100['Duration'].max()
                inlet_error = self.sample_data['inlet_sensor']['range'] * (
                            self.sample_data['inlet_sensor']['error'] + base_error)
                P_ein_max = self.df_100['Inlet_Pressure'] + inlet_error
                P_ein_min = self.df_100['Inlet_Pressure'] - inlet_error
                outlet_error = self.sample_data['outlet_sensor']['range'] * (
                            self.sample_data['outlet_sensor']['error'] + base_error)
                P_aus_max = self.df_100['Outlet_Pressure'] + outlet_error
                P_aus_min = self.df_100['Outlet_Pressure'] - outlet_error
            except:
                pass

            if i == 1:
                self.df_100['Inlet_Pressure'] = P_ein_max - (
                            (P_ein_max - self.df_100['Inlet_Pressure']) * self.df_100['Duration'] / t_max)
                self.df_100['Outlet_Pressure'] = P_aus_min - (
                            (P_aus_min - self.df_100['Outlet_Pressure']) * self.df_100['Duration'] / t_max)

            elif i == 2:
                self.df_100['Inlet_Pressure'] = P_ein_min - (
                            (P_ein_min - self.df_100['Inlet_Pressure']) * self.df_100['Duration'] / t_max)
                self.df_100['Outlet_Pressure'] = P_aus_max - (
                            (P_aus_max - self.df_100['Outlet_Pressure']) * self.df_100['Duration'] / t_max)
                original_k = guess[0] * 0.1
                recent_k = result.x[0]

            elif i == 3:
                settings.compressibility_multiplier = 0.997
                settings.viscosity_multiplier = 0.96
                settings.density_multiplier = 0.9996
                if original_k > recent_k:
                    self.df_100['Inlet_Pressure'] = P_ein_max - (
                                (P_ein_max - self.df_100['Inlet_Pressure']) * self.df_100['Duration'] / t_max)
                    self.df_100['Outlet_Pressure'] = P_aus_min - (
                                (P_aus_min - self.df_100['Outlet_Pressure']) * self.df_100['Duration'] / t_max)
                else:
                    self.df_100['Inlet_Pressure'] = P_ein_min - (
                                (P_ein_min - self.df_100['Inlet_Pressure']) * self.df_100['Duration'] / t_max)
                    self.df_100['Outlet_Pressure'] = P_aus_max - (
                                (P_aus_max - self.df_100['Outlet_Pressure']) * self.df_100['Duration'] / t_max)
                self.df_100['Temperature'] = self.df_100['Temperature'] - 0.5
                self.sample_data['length'] = self.sample_data['length'] * 0.995
                self.sample_data['diameter'] = self.sample_data['diameter'] * 1.005
                self.sample_data['inlet_chamber_volume'] = self.sample_data['inlet_chamber_volume'] * 0.98
                self.sample_data['outlet_chamber_volume'] = self.sample_data['outlet_chamber_volume'] * 0.98
            elif i == 4:
                settings.compressibility_multiplier = 1.003
                settings.viscosity_multiplier = 1.04
                settings.density_multiplier = 1.0004
                if original_k > recent_k:
                    self.df_100['Inlet_Pressure'] = P_ein_min - (
                                (P_ein_min - self.df_100['Inlet_Pressure']) * self.df_100['Duration'] / t_max)
                    self.df_100['Outlet_Pressure'] = P_aus_max - (
                                (P_aus_max - self.df_100['Outlet_Pressure']) * self.df_100['Duration'] / t_max)
                else:
                    self.df_100['Inlet_Pressure'] = P_ein_max - (
                                (P_ein_max - self.df_100['Inlet_Pressure']) * self.df_100['Duration'] / t_max)
                    self.df_100['Outlet_Pressure'] = P_aus_min - (
                                (P_aus_min - self.df_100['Outlet_Pressure']) * self.df_100['Duration'] / t_max)
                self.df_100['Temperature'] = self.df_100['Temperature'] + 0.5
                self.sample_data['length'] = self.sample_data['length'] * 1.005
                self.sample_data['diameter'] = self.sample_data['diameter'] * 0.995
                self.sample_data['inlet_chamber_volume'] = self.sample_data['inlet_chamber_volume'] * 1.02
                self.sample_data['outlet_chamber_volume'] = self.sample_data['outlet_chamber_volume'] * 1.02

            elif i == 5:
                self.df_100['Temperature'] = self.df_100['Temperature'] - 0.5
            elif i == 6:
                self.df_100['Temperature'] = self.df_100['Temperature'] + 0.5
            elif i == 7:
                self.sample_data['length'] = self.sample_data['length'] * 0.995
                self.sample_data['diameter'] = self.sample_data['diameter'] * 1.005
            elif i == 8:
                self.sample_data['length'] = self.sample_data['length'] * 1.005
                self.sample_data['diameter'] = self.sample_data['diameter'] * 0.995
            elif i == 9:
                self.sample_data['inlet_chamber_volume'] = self.sample_data['inlet_chamber_volume'] * 0.98
                self.sample_data['outlet_chamber_volume'] = self.sample_data['outlet_chamber_volume'] * 0.98
            elif i == 10:
                self.sample_data['inlet_chamber_volume'] = self.sample_data['inlet_chamber_volume'] * 1.02
                self.sample_data['outlet_chamber_volume'] = self.sample_data['outlet_chamber_volume'] * 1.02
            elif i == 11:
                settings.compressibility_multiplier = 0.997
            elif i == 12:
                settings.compressibility_multiplier = 1.003
            elif i == 13:
                settings.viscosity_multiplier = 0.96
            elif i == 14:
                settings.viscosity_multiplier = 1.04
            elif i == 15:
                settings.density_multiplier = 0.9996
            elif i == 16:
                settings.density_multiplier = 1.0004

            guess = pd.read_csv(os.path.join(self.path_sim, self.file_name + '.csv'),
                                skiprows=6, nrows=2, header=None, sep=':', usecols=[1])
            guess = [float(guess.loc[0]) * 10, float(guess.loc[1])]
            result = Optimizer(self.df_100, self.sample_data, guess)
            result, opt_steps = result.nelder_mead(parameter)
            df_opt = pd.concat([df_opt, pd.DataFrame(opt_steps[1:], columns=opt_steps[0])], axis=1)
            base_error = result.fun / 100
            i += 1

        path = os.path.join(self.path_sim + '//uncertainty', self.file_name + '_uncertainty.txt')
        df_opt.to_csv(path, index=False, float_format='%.6g')
        return df_opt

    def calculate_permeability_flask(self, df_100, sample_data, guess, parameter='k'):
        result = Optimizer(df_100, sample_data, guess)
        result, opt_steps = result.nelder_mead(parameter)

    def calculate_permeability(self, guess, parameter='k'):
        if self.find_file():
            user_input = input('Bereits angepasste Messdaten nutzen? (y/n')
            if user_input == 'y':
                self.set_adjusted_data()
            elif user_input == 'n':
                self.set_data()
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

    def calculate_permeability_stepwise(self, guess, parameter='k'):
        self.set_data()
        data = Data(self.path)
        df_100_list = []
        result_list = []
        temp = pd.DataFrame({'t': [], 'k': []})

        result = Optimizer(self.df_100, self.sample_data, guess)
        result, opt_steps = result.nelder_mead(parameter)
        df_100_list.append(self.df_100)
        result_list.append(result)
        temp.loc[0] = [df_100_list[0]['Duration'].max(), result_list[0].x[0]]

        duration_10_percent = self.df_final['Duration'].max() * 0.1
        for i in range(9):
            self.df_100 = self.df_final[self.df_final['Duration'].between(1, duration_10_percent * (i + 1))]
            self.df_100.reset_index(inplace=True, drop=True)
            self.df_100 = data.interpolate(self.df_100)
            result = Optimizer(self.df_100, self.sample_data, guess)
            result, opt_steps = result.nelder_mead(parameter)
            df_100_list.append(self.df_100)
            result_list.append(result)
            temp.loc[i + 1] = [df_100_list[-1]['Duration'].max(), result_list[-1].x[0]]

        plot = Plotter(df_100_list, **{'name': self.file_name, 'result': result_list})
        plot.result_chart_stepwise()

        df = df_100_list[0][['Duration', 'DateTime', 'Inlet_Pressure', 'Inlet_Pressure_Cal', 'Outlet_Pressure',
                             'Outlet_Pressure_Cal', 'Confining_Pressure', 'Temperature']]

        path = os.path.join(self.path_sim, self.file_name + '_interval.txt')
        del self.sample_data['inlet_sensor']
        del self.sample_data['outlet_sensor']
        df_res = pd.DataFrame.from_dict(self.sample_data, orient='index')
        df_res.to_csv(path, header=False, sep=':', float_format='%.4f')
        df.to_csv(path, index=False, mode='a', float_format='%.2f')
        temp.to_csv(path, mode='a', index=False)

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
        del self.sample_data['inlet_sensor']
        del self.sample_data['outlet_sensor']
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
        if self.find_file():
            user_input = input('Bereits angepasste Messdaten nutzen? (y/n)')
            if user_input == 'y':
                self.set_adjusted_data()
            elif user_input == 'n':
                self.set_data()
        else:
            self.set_data()
        result = Optimizer(self.df_100, self.sample_data, guess)
        result, opt_steps = result.nelder_mead(parameter)

        plot = PlotterReaktor(self.df_100, **{'name': self.file_name})
        plot.result_chart()

        self.add_results(result, guess)
        user_input = input('Ergebnis abspeichern? (y)')
        if user_input == 'y':
            self.save_adjusted_measurement_file()
            self.save_results()

    def set_data(self):
        data = DataReaktor(self.path)
        self.df_100, self.df_final = data.new_pressure_file()
        self.sample_data = data.sample_data()

    def set_adjusted_data(self):
        data = DataReaktor(self.path)
        self.df_100, self.df_final = data.adjusted_pressure_file()
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
