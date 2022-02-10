import numpy as np
import pandas as pd
import scipy.sparse
import scipy.sparse.linalg
import CoolProp.CoolProp as cp
import plotly.express as px


class LinearSystem:
    number_of_cells = 50

    def __init__(self, df_100, sample_data, guess):
        self.data = {'inlet_pressure': np.array(df_100['Inlet_Pressure'].values),
                     'outlet_pressure': np.array(df_100['Outlet_Pressure'].values),
                     'duration': np.array(df_100['Duration'].values),
                     'datetime': np.array(df_100['DateTime'].values),
                     'temperature': np.array(df_100['Temperature'].values)}
        self.guess = {'permeability': guess[0],
                      'porosity': guess[1]}
        self.sample = sample_data

    def solve_linear_system(self):
        number_of_timesteps = len(self.data['duration']) - 1
        self.calculate_timesteps()
        self.initialize_calculated_pressure()
        sample_pressure = self.get_initial_pressure()

        for step in range(number_of_timesteps):
            self.data.update({'actual_time_step': step})
            sample_pressure = self.iterate_nonlinear_parameters(sample_pressure)
            self.data['inlet_pressure_calculated'][step+1] = sample_pressure[0]
            self.data['outlet_pressure_calculated'][step+1] = sample_pressure[-1]

        self.data.update({'cell_pressure': sample_pressure})
        return self.data

    def get_initial_pressure(self):
        atmospheric_pressure = self.data['outlet_pressure'][0]
        sample_pressure = np.ones(self.number_of_cells) * atmospheric_pressure
        sample_pressure[0] = self.data['inlet_pressure'][0]
        return sample_pressure

    def initialize_calculated_pressure(self):
        inlet_pressure_calculated = np.ones(100)
        inlet_pressure_calculated[0] = self.data['inlet_pressure'][0]
        outlet_pressure_calculated = np.ones(100)
        outlet_pressure_calculated[0] = self.data['outlet_pressure'][0]
        self.data.update({'inlet_pressure_calculated': inlet_pressure_calculated,
                          'outlet_pressure_calculated': outlet_pressure_calculated})

    def calculate_timesteps(self):
        timesteps = np.diff(self.data['duration'])
        self.data.update({'timesteps': timesteps})

    def iterate_nonlinear_parameters(self, sample_pressure):
        i = 0
        difference = 1
        #difference_list = []

        _, solution_vector = self.get_linear_system(sample_pressure)
        while difference > 1e-5 and i <= 10:
            coefficient_matrix, _ = self.get_linear_system(sample_pressure)
            sample_pressure_new = scipy.sparse.linalg.spsolve(coefficient_matrix, solution_vector)
            difference = self.l2_norm(sample_pressure_new, sample_pressure)
            sample_pressure = sample_pressure_new
            i += 1
            #difference_list.append(difference)

        '''
        df = pd.DataFrame(difference_list, columns=['difference'])
        fig = px.line(df, x=df.index, y='difference', log_y=True)
        fig.show()
        exit()
        '''
        return sample_pressure

    @staticmethod
    def residuum(A, x_guess, b):
        r = abs(np.sum((A*x_guess - b) / b))
        return r

    def get_linear_system(self, sample_pressure):
        main_diagonal, off_diagonal, solution_vector = self.build_diagonals(sample_pressure)
        A = scipy.sparse.diags(
            diagonals=[main_diagonal*-1, off_diagonal, off_diagonal],
            offsets=[0, -1, 1],
            shape=(self.number_of_cells, self.number_of_cells),
            format='csr')
        b = - solution_vector * sample_pressure
        return A, b

    def build_diagonals(self, sample_pressure):
        k, n = self.initialize_permeability_porosity()
        compressibility, viscosity, density = self.get_coolprop_data(sample_pressure)
        dx = self.sample['length'] / (self.number_of_cells - 1)
        dt = self.data['timesteps'][self.data['actual_time_step']]
        area = self.sample['area']
        inlet_volume = self.sample['inlet_chamber_volume']
        outlet_volume = self.sample['outlet_chamber_volume']

        viscosity_mean = (viscosity[1:] + viscosity[:-1]) / 2
        density_mean = (density[1:] + density[:-1]) / 2
        k_mean_harmonic = ((2*k[1:]*k[:-1]) / (k[1:]+k[:-1]))

        off_diagonal = (density_mean * area * k_mean_harmonic) / (viscosity_mean * dx)
        main_diagonal = (area * n * compressibility * density * dx) / dt
        main_diagonal[1:-1] = main_diagonal[1:-1] + off_diagonal[:-1] + off_diagonal[1:]
        main_diagonal[0] = (inlet_volume * density[0] * compressibility[0]) / dt + off_diagonal[0]
        main_diagonal[-1] = (outlet_volume * density[-1] * compressibility[-1]) / dt + off_diagonal[-1]
        solution_vector = area * n * compressibility * density * dx / dt
        solution_vector[0] = inlet_volume * density[0] * compressibility[0] / dt
        solution_vector[-1] = outlet_volume * density[-1] * compressibility[-1] / dt

        return main_diagonal, off_diagonal, solution_vector

    def initialize_permeability_porosity(self):
        k = np.ones(self.number_of_cells) * self.guess['permeability']
        k[0] = k[-1] = 1
        n = np.ones(self.number_of_cells) * self.guess['porosity']
        n[0] = n[-1] = 1
        return k, n

    def get_coolprop_data(self, pressure):
        try:
            parameter = ['ISOTHERMAL_COMPRESSIBILITY', 'VISCOSITY', 'DMASS']
            result = cp.PropsSI(parameter, 'T', self.data['temperature'].mean(), 'P', pressure, self.sample['gas'])
            result = result.T
        except:
            result = [np.zeros(self.number_of_cells),np.zeros(self.number_of_cells),np.zeros(self.number_of_cells)]
        return result

    @staticmethod
    def l2_norm(p, p_ref):
        l2_diff = np.sqrt(np.sum((p - p_ref) ** 2))
        l2_ref = np.sqrt(np.sum(p_ref ** 2))
        return l2_diff / l2_ref

