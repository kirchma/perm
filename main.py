import pandas as pd
import numpy as np
import os, time
from matplotlib import pyplot as plt
import scipy.sparse
import scipy.sparse.linalg
import scipy.optimize as optimize
from scipy.interpolate import interp1d
import CoolProp.CoolProp as cp


class MeasurementData:

    def __init__(self, path):
        self.path = path
        self.filename, _ = os.path.splitext(os.path.split(path)[1])
        self.start = None
        self.stop = None

    def interpolate_data(self, **kwargs):
        data = self.prepare_data()
        if kwargs.get('step'):
            log_time_scale = self.create_log_time_intervall(data, kwargs['step'])
        elif kwargs.get('manual'):
            coordinates = self.get_manual_coordinates(data)
            log_time_scale = self.create_log_time_manual(data, coordinates)
            #TODO: log_time_scale gibt eine verschachtelte Liste zurück, in separate Funktion packen
        else:
            log_time_scale = self.create_log_time(data)

        function_inlet_pressure = interp1d(data['Duration'], data['Inlet_Pressure'])
        function_outlet_pressure = interp1d(data['Duration'], data['Outlet_Pressure'])
        function_temperature = interp1d(data['Duration'], data['Temperature'])

        inlet_pressure_log_scale = function_inlet_pressure(log_time_scale)
        outlet_pressure_log_scale = function_outlet_pressure(log_time_scale)
        temperature_log_scale = function_temperature(log_time_scale)


        if kwargs.get('manual'):
            data_log_scale = []
            for i in range(len(log_time_scale)):
                temp = pd.DataFrame(np.array([log_time_scale[i], inlet_pressure_log_scale[i],
                                                        outlet_pressure_log_scale[i], temperature_log_scale[i]]).T,
                                              columns=['Duration', 'Inlet_Pressure', 'Outlet_Pressure', 'Temperature'])
                data_log_scale.append(temp)
        else:
            data_log_scale = pd.DataFrame(np.array([log_time_scale, inlet_pressure_log_scale,
                                                    outlet_pressure_log_scale, temperature_log_scale]).T,
                                          columns=['Duration', 'Inlet_Pressure', 'Outlet_Pressure', 'Temperature'])
        return data_log_scale

    def get_manual_coordinates(self, data):
        while True:
            plot_result = Plotter(data, **{'name': self.filename})
            x_coordinates = plot_result.plot_select_interval()

            user_input = input('Messintervalle ok?')
            if user_input == 'y':
                break
        # get nearest row index for each x-coordinate from user input
        time_index = [data['Duration'].sub(i).abs().idxmin() for i in x_coordinates]
        # add first and last time point of the measurement to the manual selected coordinates
        time_index.extend([0, data.index[-1]])
        time_index.sort()
        return time_index

    def prepare_data(self, **kwargs):
        kwargs.setdefault('set_start_time_to_max_pressure', True)
        raw_data = self.read_file(self.path)
        converted_data = self.convert_data(raw_data)
        self.set_start_stop(converted_data)

        time_adjusted_data = converted_data.iloc[self.start:self.stop]
        if kwargs.get('set_start_time_to_max_pressure'):
            time_adjusted_data = self.set_start_time_to_max_pressure(time_adjusted_data)
        else:
            time_adjusted_data = self.reset_duration(time_adjusted_data)

        plot_after_adjustment = Plotter(time_adjusted_data, **{'data_before_adjustment': converted_data,
                                                               'start': self.start, 'stop': self.stop,
                                                               'name': self.filename})
        #plot_after_adjustment.plot_measurement_chart()
        return time_adjusted_data

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
            df[['Inlet_Pressure', 'Outlet_Pressure', 'Confining_Pressure']].apply(lambda x: x / 10 + 0.0977)
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
        print(f'Messdauer = {df["Duration"].max()/86400:.2f} Tage')
        df = self.reset_duration(df)
        return df

    @staticmethod
    def reset_duration(df):
        df = df.copy()
        df.reset_index(inplace=True, drop=True)
        df['Duration'] = df['Duration'] - df.iloc[0, 0] + 1
        return df

    @staticmethod
    def create_log_time(data):
        time_min = 1
        time_max = int(data['Duration'].max())
        amount_of_data_points = 100
        log_time_scale = np.geomspace(time_min, time_max, amount_of_data_points).round(2)
        return log_time_scale

    @staticmethod
    def create_log_time_intervall(data, step):
        max_step = 5
        time_min = 1

        if step < max_step:
            time_max = int(data['Duration'].max()) / max_step * step
        else:
            time_max = int(data['Duration'].max())
        amount_of_data_points = 100
        log_time_scale = np.geomspace(time_min, time_max, amount_of_data_points).round(2)
        return log_time_scale

    def create_log_time_manual(self, data, time_index):
        log_time_scale = []
        #TODO: passende Namen für die nested lists, da diese nicht identisch mit den Datentypen der oberen Funktionen sind
        time_values = data.iloc[time_index, 0].to_list()
        amount_of_data_points = 100
        for i in range(len(time_values)-1):
            log_time_scale.append(np.geomspace(time_values[i], time_values[i + 1], amount_of_data_points).round(2))
        return log_time_scale

    def get_general_data(self):
        my_dict = self.get_core_dimensions()
        chamber_volume = self.get_chamber_volume()

        my_dict.update({'inlet_chamber_volume': chamber_volume[0],
                        'outlet_chamber_volume': chamber_volume[1]})
        return my_dict

    def get_core_dimensions(self):
        database = self.read_file('database.csv')
        database.set_index('name', inplace=True)
        length = database.loc[self.filename, 'length']
        diameter = database.loc[self.filename, 'diameter']
        area = np.pi * 0.25 * diameter**2
        gas = database.loc[self.filename, 'gas']
        my_dict = {'length': length,
                   'area': area,
                   'gas': gas}
        return my_dict

    def get_chamber_volume(self):
        database = self.read_file('database.csv')
        all_units = self.read_file('measurement_units.csv')
        ml_to_m3 = 1e-6

        database.set_index('name', inplace=True)
        used_unit = database.loc[self.filename, 'unit']
        filt = all_units['number'] == used_unit
        chamber_volume = all_units.loc[filt, ['inlet_chamber_in_ml', 'outlet_chamber_in_ml']]
        return chamber_volume.values[0] * ml_to_m3


class MeasurementDataReaktor(MeasurementData):

    @staticmethod
    def convert_data(df):
        df['temp'] = pd.to_datetime(df['Date'] + df['Time'], format='%d.%m.%Y%X')
        df['Duration'] = pd.to_timedelta(df['temp'] - df['temp'][0]).dt.total_seconds()
        df.drop(['Date', 'Time', 'temp'], axis=1, inplace=True)
        df = df[['Duration', 'Inlet_Pressure', 'Outlet_Pressure',
                 'Confining_Pressure_Reactor', 'Confining_Pressure_Sample', 'Temperature']]
        # convert bar (relative) to Megapascal (absolute)
        df[['Inlet_Pressure', 'Outlet_Pressure', 'Confining_Pressure_Reactor', 'Confining_Pressure_Sample']] = \
            df[['Inlet_Pressure', 'Outlet_Pressure', 'Confining_Pressure_Reactor', 'Confining_Pressure_Sample']]\
                .apply(lambda x: x / 10 + 0.0977)
        return df

    def get_core_dimensions(self):
        database = self.read_file('database_reaktor.csv')
        database.set_index('name', inplace=True)
        length = database.loc[self.filename, 'length']
        outer_diameter = database.loc[self.filename, 'outer_diameter']
        inner_diameter = database.loc[self.filename, 'inner_diameter']
        area = np.pi * 0.25 * (outer_diameter**2 - inner_diameter**2)
        gas = database.loc[self.filename, 'gas']
        my_dict = {'length': length,
                   'area': area,
                   'gas': gas}
        return my_dict

    def get_chamber_volume(self):
        database = self.read_file('database_reaktor.csv')
        all_units = self.read_file('measurement_units.csv')
        ml_to_m3 = 1e-6

        database.set_index('name', inplace=True)
        used_unit = int(database.loc[self.filename, 'unit'])
        filt = all_units['number'] == used_unit
        chamber_volume = all_units.loc[filt, ['inlet_chamber_in_ml', 'outlet_chamber_in_ml']]
        return chamber_volume.values[0] * ml_to_m3


class Plotter:

    def __init__(self, df, **kwargs):
        self.df = df
        for key, value in kwargs.items():
            setattr(self, key, value)

    def run_once(f):
        def wrapper(*args, **kwargs):
            if not wrapper.has_run:
                wrapper.has_run = True
                return f(*args, **kwargs)
        wrapper.has_run = False
        return wrapper

    @run_once
    def plot_measurement_chart(self):
        fig = plt.figure(figsize=(12, 12))
        plt.subplot(2, 1, 1)
        plt.title(self.name, fontsize=16)
        plt.xlabel('Zeit in s', fontsize=16)
        plt.ylabel('Druck in MPa', fontsize=16)
        plt.grid(True, which='major')
        plt.grid(True, which='minor', linestyle='--')
        plt.grid(True)
        plt.semilogx(self.data_before_adjustment['Duration'], self.data_before_adjustment['Inlet_Pressure'], color='C0',
                     linestyle='-')
        plt.semilogx(self.data_before_adjustment['Duration'], self.data_before_adjustment['Outlet_Pressure'],
                     color='C0', linestyle='-')
        plt.axvline(x=self.data_before_adjustment.iloc[self.start, 0], color='black', linestyle='--')
        plt.axvline(x=self.data_before_adjustment.iloc[self.stop - 1, 0], color='black', linestyle='--')

        plt.subplot(2, 1, 2)
        plt.xlabel('Zeit in s', fontsize=16)
        plt.ylabel('Druck in MPa', fontsize=16)
        plt.grid(True, which='major')
        plt.grid(True, which='minor', linestyle='--')
        plt.grid(True)
        plt.semilogx(self.df['Duration'], self.df['Inlet_Pressure'], color='C0', linestyle='-')
        plt.semilogx(self.df['Duration'], self.df['Outlet_Pressure'], color='C0', linestyle='-')
        plt.show()

    def plot_calculation_chart(self):
        self.setup_figure()
        plt.semilogx(self.df['Duration'], self.df['Inlet_Pressure'], color='C0', linestyle='-', label='Messwerte')
        plt.semilogx(self.df['Duration'], self.df['Outlet_Pressure'], color='C0', linestyle='-')
        plt.scatter(self.calc_data['Duration'], self.calc_data['Inlet_Pressure'] * 1e-6, color='r', s=3, label='Rechenwerte')
        plt.scatter(self.calc_data['Duration'], self.calc_data['Outlet_Pressure'] * 1e-6, color='r', s=3)
        # plot stepwise solution
        try:
            self.intervals[1]
            ax2 = ax.twinx()
            ax2.plot(self.intervals[1], self.intervals[0], color='k', marker="o", ls="")
            k_intervals_sorted = sorted(self.intervals[0])
            ax2.set_ylim(10 ** np.ceil(np.log10(k_intervals_sorted[-1])), 10 ** (np.ceil(np.log10(k_intervals_sorted[0])) - 1))
            ax2.set_yscale('log')
            ax2.set_ylabel('Permeabilität [m²]', fontsize=16)
        except AttributeError:
            pass
        plt.legend()
        plt.show()

    def plot_select_interval(self):
        x_coordinates = []

        def onclick(event, ax):
            ax.time_onclick = time.time()

        def onrelease(event, ax):
            if (time.time() - ax.time_onclick) < 0.1:
                x_coordinates.append(event.xdata)
                print(event.xdata, event.ydata)
                plt.plot(event.xdata, event.ydata, 'r+')
                fig.canvas.draw()

        fig = plt.figure(figsize=(12, 9))
        ax = fig.add_subplot(111)
        ax.semilogx(self.df['Duration'], self.df['Inlet_Pressure'])
        fig.canvas.mpl_connect('button_press_event', lambda event: onclick(event, ax))
        fig.canvas.mpl_connect('button_release_event', lambda event: onrelease(event, ax))
        ax.set_title('Messintervalle', fontsize=16)
        ax.set_xlabel('Messwerte', fontsize=16)
        ax.set_ylabel('Eingangsdruck in MPa', fontsize=16)
        ax.grid()
        plt.show()
        return x_coordinates

    def setup_figure(self):
        fig = plt.figure(figsize=(14, 8))
        plt.title(self.name, fontsize=16)
        plt.xlabel('Zeit in s', fontsize=16)
        plt.ylabel('Druck in MPa', fontsize=16)
        plt.grid(True, which='major')
        plt.grid(True, which='minor', linestyle='--')
        plt.grid(True)


class LinearSystem:
    number_of_cells = 51

    def __init__(self, data, general_data, initial_guess):
        self.measured_data = {'inlet_pressure': np.array(data['Inlet_Pressure'].values) * 1e6,
                              'outlet_pressure': np.array(data['Outlet_Pressure'].values) * 1e6,
                              'duration': np.array(data['Duration'].values),
                              'temperature': data['Temperature'].mean() + 273.15}
        self.guess = {'permeability': initial_guess[0],
                      'porosity': initial_guess[1]}
        self.general_data = general_data
        self.calculated_data = {}

    def solve_linear_system(self):
        number_of_timesteps = len(self.measured_data['duration']) - 1
        inlet_pressure_calculated = [self.measured_data['inlet_pressure'][0]]
        outlet_pressure_calculated = [self.measured_data['outlet_pressure'][0]]
        cell_pressure = self.get_initial_pressure()

        for step in range(number_of_timesteps):
            self.set_stepsize_dt(step)
            cell_pressure = self.iterate_nonlinear_parameters(cell_pressure)
            inlet_pressure_calculated.append(cell_pressure[0])
            outlet_pressure_calculated.append(cell_pressure[-1])

        result = [self.measured_data['duration'], inlet_pressure_calculated, outlet_pressure_calculated]
        chamber_pressure = pd.DataFrame(result).transpose()
        chamber_pressure.columns = ['Duration', 'Inlet_Pressure', 'Outlet_Pressure']
        return chamber_pressure, cell_pressure

    def set_stepsize_dt(self, step: int) -> float:
        timesteps = self.measured_data['duration']
        dt = timesteps[step + 1] - timesteps[step]
        self.calculated_data.update({'dt': dt})
        return dt

    def iterate_nonlinear_parameters(self, cell_pressure) -> np.ndarray:
        inner_iteration = 0
        max_iteration = 10
        difference = 1

        _, solution_vector = self.get_linear_system(cell_pressure)
        while difference > 1e-4 and inner_iteration <= max_iteration:
            coefficient_matrix, _ = self.get_linear_system(cell_pressure)
            cell_pressure_new = scipy.sparse.linalg.spsolve(coefficient_matrix, solution_vector)
            # iterativer Loeser, kann genutzt werden, ist bei dem kleinen Gleichungssystem aber langsamer
            #cell_pressure_new, code = scipy.sparse.linalg.cg(coefficient_matrix, solution_vector, tol=1e-10)
            difference = self.l2_norm(cell_pressure_new, cell_pressure)
            cell_pressure = cell_pressure_new
            inner_iteration += 1
        return cell_pressure

    def get_initial_pressure(self) -> np.ndarray:
        atmospheric_pressure = self.measured_data['outlet_pressure'][0]
        cell_pressure = np.ones(self.number_of_cells) * atmospheric_pressure
        cell_pressure[0] = self.measured_data['inlet_pressure'][0]
        return cell_pressure

    def get_linear_system(self, cell_pressure: np.ndarray):
        main_diagonal, off_diagonal, solution_vector = self.build_diagonals(cell_pressure)

        A = scipy.sparse.diags(
            diagonals=[main_diagonal * -1, off_diagonal, off_diagonal],
            offsets=[0, -1, 1],
            shape=(self.number_of_cells, self.number_of_cells),
            format='csr')
        b = - solution_vector * cell_pressure
        return A, b

    @staticmethod
    def l2_norm(p, p_ref):
        l2_diff = np.sqrt(np.sum((p - p_ref) ** 2))
        l2_ref = np.sqrt(np.sum(p_ref ** 2))
        return l2_diff / l2_ref
    '''
    crank-nicolson
    def build_diagonals(self, cell_pressure: np.ndarray):
        k, n = self.initialize_permeability_porosity()
        compressibility, viscosity, density = self.get_coolprop_data(cell_pressure)
        dx = self.general_data['length'] / (self.number_of_cells - 1)
        dt = self.calculated_data['dt']

        viscosity_mean = (viscosity[1:] + viscosity[:-1]) / 2
        density_mean = (density[1:] + density[:-1]) / 2
        k_mean_harmonic = ((2 * k[1:] * k[:-1]) / (k[1:] + k[:-1]))

        off_diagonal = (density_mean * self.general_data['area'] * k_mean_harmonic) / (viscosity_mean * dx)
        main_diagonal = (self.general_data['area'] * n * compressibility * density * dx) * 2 / dt
        main_diagonal[1:-1] = main_diagonal[1:-1] + off_diagonal[:-1] + off_diagonal[1:]
        main_diagonal[0] = (self.general_data['inlet_chamber_volume'] * density[0] * compressibility[0]) * 2 / \
                           dt + off_diagonal[0]
        main_diagonal[-1] = (self.general_data['outlet_chamber_volume'] * density[-1] * compressibility[-1]) * 2 / \
                           dt + off_diagonal[-1]

        solution_vector = self.general_data['area'] * n * compressibility * density * dx * 2 / dt
        solution_vector[1:-1] = (solution_vector[1:-1] - off_diagonal[:-1] - off_diagonal[1:]) * cell_pressure[1:-1] + \
                                off_diagonal[:-1] * cell_pressure[:-2] + off_diagonal[1:] * cell_pressure[2:]
        solution_vector[0] = (self.general_data['inlet_chamber_volume'] * density[0] * compressibility[0]
                              * 2 / dt - off_diagonal[0]) * cell_pressure[0] + off_diagonal[0] * cell_pressure[1]
        solution_vector[-1] = (self.general_data['outlet_chamber_volume'] * density[-1] * compressibility[-1]
                               * 2 / dt - off_diagonal[-1]) * cell_pressure[-1] + off_diagonal[-1] * cell_pressure[-2]

        return main_diagonal, off_diagonal, solution_vector
    '''
    def build_diagonals(self, cell_pressure: np.ndarray):
        k, n = self.initialize_permeability_porosity()
        compressibility, viscosity, density = self.get_coolprop_data(cell_pressure)
        dx = self.general_data['length'] / (self.number_of_cells - 1)
        dt = self.calculated_data['dt']

        viscosity_mean = (viscosity[1:] + viscosity[:-1]) / 2
        density_mean = (density[1:] + density[:-1]) / 2
        k_mean_harmonic = ((2 * k[1:] * k[:-1]) / (k[1:] + k[:-1]))

        off_diagonal = (density_mean * self.general_data['area'] * k_mean_harmonic) / (viscosity_mean * dx)
        main_diagonal = (self.general_data['area'] * n * compressibility * density * dx) / dt
        main_diagonal[1:-1] = main_diagonal[1:-1] + off_diagonal[:-1] + off_diagonal[1:]
        main_diagonal[0] = (self.general_data['inlet_chamber_volume'] * density[0] * compressibility[0]) / \
                           dt + off_diagonal[0]
        main_diagonal[-1] = (self.general_data['outlet_chamber_volume'] * density[-1] * compressibility[-1]) / \
                            dt + off_diagonal[-1]
        solution_vector = self.general_data['area'] * n * compressibility * density * dx / dt
        solution_vector[0] = self.general_data['inlet_chamber_volume'] * density[0] * compressibility[0] / dt
        solution_vector[-1] = self.general_data['outlet_chamber_volume'] * density[-1] * compressibility[-1] / dt

        return main_diagonal, off_diagonal, solution_vector

    def initialize_permeability_porosity(self):
        k = self.guess['permeability'] * np.ones(self.number_of_cells)
        k[0] = k[-1] = 1
        n = self.guess['porosity'] * np.ones(self.number_of_cells)
        n[0] = n[-1] = 1
        return k, n

    def get_coolprop_data(self, pressure):
        try:
            searched_parameter = ['ISOTHERMAL_COMPRESSIBILITY', 'VISCOSITY', 'DMASS']
            result = []
            for i in searched_parameter:
                result.append(cp.PropsSI(i, 'T', self.measured_data['temperature'],
                                         'P', pressure, self.general_data['gas']))
        except:
            # TODO add error handling
            result = [np.ones(self.number_of_cells),
                      np.ones(self.number_of_cells),
                      np.ones(self.number_of_cells)]
        return result


class Optimizer:

    def __init__(self, measured_data, general_data, initial_guess):
        self.measured_data = measured_data
        self.general_data = general_data
        self.initial_guess = initial_guess
        self.error = []
        self.k_iterative = []

    def nelder_mead(self, parameter):
        if parameter == 'k':
            min_result = optimize.minimize(self.optimize_function, self.initial_guess[0], args=parameter,
                                           method='Nelder-Mead', options={'disp': False}, tol=0.001)
            self.initial_guess[0] = min_result.x
        elif parameter == 'both':
            min_result = optimize.minimize(self.optimize_function, self.initial_guess, args=parameter,
                                           method='Nelder-Mead', options={'disp': False}, tol=0.001)
            self.initial_guess = min_result.x

        # recalculate with best fit parameters
        chamber_pressure, _ = LinearSystem(self.measured_data,
                                           self.general_data,
                                           self.initial_guess).solve_linear_system()
        real_permeability = self.klinkenberg(chamber_pressure, min_result.x[0])
        self.print_output(min_result, real_permeability)

        return chamber_pressure, min_result
        
    def optimize_function(self, guess, parameter):
        if parameter == 'k':
            guess = [guess[0], self.initial_guess[1]]
        elif parameter == 'both':
            guess = guess

        chamber_pressure, _ = LinearSystem(self.measured_data,
                                           self.general_data,
                                           guess).solve_linear_system()
        self.error.append(self.calculate_error(chamber_pressure))
        print(f"k = {guess[0]:.4} m^2 , n = {guess[1] * 100:.2} %, e = {self.error[-1]:.3} %")
        return self.error[-1]

    def calculate_error(self, p):
        p_in_ref = self.measured_data['Inlet_Pressure'] * 1e6
        p_out_ref = self.measured_data['Outlet_Pressure'] * 1e6
        p_in = p['Inlet_Pressure']
        p_out = p['Outlet_Pressure']
        absolute_magnitude = np.sqrt(sum(p_in_ref**2 + p_out_ref**2))
        difference_measured_calculated = abs(p_in_ref - p_in) + abs(p_out_ref - p_out)
        absolute_error = np.sqrt(sum(difference_measured_calculated**2))
        relative_error = absolute_error / absolute_magnitude * 100
        return relative_error

    def klinkenberg(self,chamber_pressure, k_s):
        inlet_pressure = chamber_pressure.iloc[-1, 1]
        outlet_pressure = chamber_pressure.iloc[-1, 2]
        mean_pressure = (inlet_pressure + outlet_pressure) / 2 * 1e-5
        k_i = k_s * 1e-10

        for _ in range(5):
            f = 3.05351e-6 * k_i ** 0.65 / mean_pressure + k_i - k_s
            f_diff = 1.98478e-6 / (mean_pressure * k_i ** 0.35) + 1
            k_new = k_i - f / f_diff
            k_i = k_new
        return k_i

    def print_output(self, min_result, real_permeability):
        print(f'\nCalculation finished: {min_result.message} \n'
              f'\tNumber of iterations: {min_result.nit} \n'
              f'\tNumber of function evaluations: {min_result.nfev} \n\n'
              f'\tPermeability: {min_result.x[0]:.2} m²\n'
              f'\tReal permeability: {real_permeability:.2} m²\n'
              f'\tPorosity: {self.initial_guess[1]*100:.2} %\n'
              f'\tRelative error: {round(min_result.fun, 2)} %')


class Main:

    def __init__(self, path):
        self.path = path
        self.measured_data = None
        self.general_data = None
        self.chamber_pressure = None
        self.min_result = None

    def test_mesh(self, initial_guess):
        grid_dimensions = [100, 50, 25]
        p_list = []
        for i in range(len(grid_dimensions)):
            LinearSystem.number_of_cells = grid_dimensions[i]
            self.set_data('2KA')
            self.chamber_pressure, cell_pressure = LinearSystem(self.measured_data, self.general_data,
                                                                initial_guess).solve_linear_system()
            p_list.append(cell_pressure)

        x_axis_0 = np.linspace(0, 200, grid_dimensions[0])
        x_axis_1 = np.linspace(0, 200, grid_dimensions[1])
        x_axis_2 = np.linspace(0, 200, grid_dimensions[2])

        interpolate_function_0 = interp1d(x_axis_0, p_list[0])
        interpolate_function_1 = interp1d(x_axis_1, p_list[1])
        p_list[0] = interpolate_function_0(x_axis_2)
        p_list[1] = interpolate_function_1(x_axis_2)

        plt.plot(x_axis_2, p_list[0])
        plt.plot(x_axis_2, p_list[1])
        plt.plot(x_axis_2, p_list[2])
        plt.show()

        GCI1_list = []
        GCI2_list = []

        for i in range(grid_dimensions[2]):
            fehlerordnung = np.log(abs((p_list[2][i] - p_list[1][i]) / (p_list[1][i] - p_list[0][i]))) / np.log(2)
            e1 = (p_list[1][i] - p_list[0][i]) / p_list[0][i]
            GCI1 = 1.25 * abs(e1) / (2**fehlerordnung - 1)
            e2 = (p_list[2][i] - p_list[1][i]) / p_list[1][i]
            GCI2 = 1.25 * abs(e2) / (2**fehlerordnung - 1)
            GCI1_list.append(GCI1)
            GCI2_list.append(GCI2)

            print(f'Fehlerordnung = {round(fehlerordnung,2)}')
            print(f'GCI_1 = {round(GCI1 * 100, 5)} %')
            print(f'GCI_2 = {round(GCI2 * 100, 5)} %')
            #print(GCI2/(2**fehlerordnung*GCI1))
            print()

        print('end')


    def single_run(self, initial_guess):
        self.set_data('2KA')
        self.chamber_pressure, _ = LinearSystem(self.measured_data, self.general_data,
                                                initial_guess).solve_linear_system()
        self.plot_result()

    def calculate_permeability(self, initial_guess, parameter='k'):
        self.set_data('2KA')
        self.chamber_pressure, _ = Optimizer(self.measured_data, self.general_data,
                                             initial_guess).nelder_mead(parameter)
        self.plot_result()

    def optimize_reaktor(self, initial_guess, parameter='k'):
        self.set_data('Reaktor')
        self.chamber_pressure, _ = Optimizer(self.measured_data, self.general_data,
                                             initial_guess).nelder_mead(parameter)
        self.plot_result()

    def optimize_measurement_intervals(self, initial_guess):
        time_interval = []
        k_interval = []
        self.general_data = MeasurementData(self.path).get_general_data()
        for step in range(1,6):
            self.measured_data = MeasurementData(self.path).interpolate_data(step=step)
            self.chamber_pressure, self.min_result = Optimizer(self.measured_data, self.general_data, initial_guess).nelder_mead()
            k_interval.append(self.min_result.x[0])
            time_interval.append(self.measured_data['Duration'].max())
        # TODO: Variable name
        plot_result = Plotter(self.measured_data, **{'calc_data': self.chamber_pressure,
                                                     'intervals': [k_interval, time_interval],
                                                     'name': 'Messung'})
        plot_result.plot_calculation_chart()

    def optimize_measurement_manual(self, initial_guess):
        self.set_data('manual')
        number_of_intervals = len(self.measured_data)
        chamber_pressure_interval = pd.DataFrame(columns=['Duration', 'Inlet_Pressure', 'Outlet_Pressure'])
        df = pd.DataFrame(columns=['Hours', 'Permeability', 'Real_Permeability', 'Relative_Error'],
                          index=range(0, number_of_intervals))
        for i in range(number_of_intervals):
            self.chamber_pressure, self.min_result = Optimizer(self.measured_data[i],
                                                               self.general_data, initial_guess).nelder_mead()
            df = self.create_output(df, i)
            # TODO: initialdruck im n+1 Intervall anpassen, dieser ist nicht mehr der atmosphärendruck
            chamber_pressure_interval = chamber_pressure_interval.append(self.chamber_pressure)
        # reset measured data for plotting
        # TODO: Plotten deaktivieren
        self.set_data('Reaktor')
        self.chamber_pressure = chamber_pressure_interval
        self.plot_result()
        print(df)

    def create_output(self, df, i):
        measurement_time_in_hours = self.measured_data[i]['Duration'].max() / 3600
        df.loc[i, 'Hours'] = round(measurement_time_in_hours, 1)
        df.loc[i, 'Permeability'] = self.min_result.x[0]
        df.loc[i, 'Relative_Error'] = round(self.min_result.fun, 2)
        return df

    def set_data(self, measurement_typ='2KA'):
        if measurement_typ == '2KA':
            self.measured_data = MeasurementData(self.path).interpolate_data()
            self.general_data = MeasurementData(self.path).get_general_data()
        elif measurement_typ == 'Reaktor':
            self.measured_data = MeasurementDataReaktor(self.path).interpolate_data()
            self.general_data = MeasurementDataReaktor(self.path).get_general_data()
        elif measurement_typ == 'manual':
            self.measured_data = MeasurementDataReaktor(self.path).interpolate_data(manual=True)
            self.general_data = MeasurementDataReaktor(self.path).get_general_data()

    def plot_result(self):
        filename, _ = os.path.splitext(os.path.split(self.path)[1])
        plot_result = Plotter(self.measured_data, **{'calc_data': self.chamber_pressure, 'name': filename})
        plot_result.plot_calculation_chart()

#HY_V9 3.2e-20, 0.001
x = Main('C:\\Users\\Martin\\OneDrive\\Promotion\\PERM\\raw_data\\HY_V9.txt')
x.test_mesh([1e-22, 0.001])


