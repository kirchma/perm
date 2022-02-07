from linear_system import LinearSystem
import numpy as np
import pandas as pd
import scipy.optimize as optimize


class Optimizer:

    def __init__(self, df_100, sample_data, guess):
        self.df_100 = df_100
        self.sample_data = sample_data
        self.guess = guess
        self.data = None
        self.optimization_steps = [['k', 'n', 'e']]

    def nelder_mead(self, parameter):
        if parameter == 'k':
            min_result = optimize.minimize(self.optimize_function, self.guess[0], args=parameter,
                                           method='Nelder-Mead', options={'disp': False}, tol=0.001)
        elif parameter == 'both':
            min_result = optimize.minimize(self.optimize_function, self.guess, args=parameter,
                                           method='Nelder-Mead', options={'disp': False}, tol=0.001)

        self.print_final_result(min_result)

        self.df_100[['Inlet_Pressure_Cal', 'Outlet_Pressure_Cal']] = None
        self.df_100['Inlet_Pressure_Cal'] = pd.DataFrame.from_dict(self.data['inlet_pressure_calculated'])
        self.df_100['Outlet_Pressure_Cal'] = pd.DataFrame.from_dict(self.data['outlet_pressure_calculated'])

        return min_result, self.optimization_steps

    def optimize_function(self, guess, parameter):
        if parameter == 'k':
            guess = [guess[0], self.guess[1]]
        elif parameter == 'both':
            guess = guess

        self.data = LinearSystem(self.df_100, self.sample_data, guess).solve_linear_system()
        error = self.calculate_error()
        self.optimization_steps.append([guess[0], guess[1], error/100])
        print(f'k = {guess[0]:.4} m^2, n = {guess[1]:.4}, e = {error:.3} %')
        return error

    def calculate_error(self):
        p_in_ref = self.data['inlet_pressure']
        p_in = self.data['inlet_pressure_calculated']
        p_out_ref = self.data['outlet_pressure']
        p_out = self.data['outlet_pressure_calculated']

        absolute_magnitude = np.sqrt(sum(p_in_ref**2 + p_out_ref**2))
        difference = abs(p_in_ref - p_in) + abs(p_out_ref - p_out)
        absolute_error = np.sqrt(sum(difference**2))
        relative_error = absolute_error / absolute_magnitude * 100
        return relative_error

    @staticmethod
    def print_final_result(min_result):
        print(f'\n Calculation finished: {min_result.message} \n'
              f'\tNumber of iterations: {min_result.nit} \n'
              f'\tNumber of function evaluations: {min_result.nfev} \n'
              f'\tPermeability: {min_result.x[0]:.3} m^2 \n'
              f'\tPorosity: \n'
              f'\tRelative error: {round(min_result.fun, 2)} %')
