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
        coordinates = []
        while True:
            user_input = input('Messintervalle ok?')
            if user_input == 'y':
                break
            def onclick(event, ax):
                ax.time_onclick = time.time()
            def onrelease(event, ax):
                if (time.time() - ax.time_onclick) < 0.1:
                    coordinates.append(event.xdata)
                    print(event.xdata, event.ydata)
                    plt.plot(event.xdata, event.ydata, 'r+')
                    fig.canvas.draw()

            fig = plt.figure(figsize=(12, 9))
            ax = fig.add_subplot(111)
            ax.semilogx(data['Duration'], data['Inlet_Pressure'])
            fig.canvas.mpl_connect('button_press_event', lambda event: onclick(event, ax))
            fig.canvas.mpl_connect('button_release_event', lambda event: onrelease(event, ax))
            ax.set_title('Messintervalle', fontsize=16)
            ax.set_xlabel('Messwerte', fontsize=16)
            ax.set_ylabel('Eingangsdruck in MPa', fontsize=16)
            ax.grid()
            plt.show()
        # get nearest row index for each x-coordinate from user input
        coordinates = [data['Duration'].sub(i).abs().idxmin() for i in coordinates]
        coordinates.append(data.index[-1])
        return coordinates

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
        plot_before_adjustment = Plotter(converted_data,
                                         **{'start': self.start, 'stop': self.stop, 'name': self.filename})
        #plot_before_adjustment.plot_measurement_chart()
        plot_after_adjustment = Plotter(time_adjusted_data, **{'name': self.filename})
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

    def create_log_time_manual(self, data, coordinates):
        time_min = 1
        #TODO: passende Namen für die nested lists, da diese nicht identisch mit den Datentypen der oberen Funktionen sind
        time_max = data.iloc[coordinates, 0].to_list()
        amount_of_data_points = 100
        temp = np.geomspace(time_min, time_max, amount_of_data_points).round(2)
        log_time_scale = list(map(list, zip(*temp)))
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
        used_unit = database.loc[self.filename, 'unit']
        filt = all_units['number'] == used_unit
        chamber_volume = all_units.loc[filt, ['inlet_chamber_in_ml', 'outlet_chamber_in_ml']]
        return chamber_volume.values[0] * ml_to_m3


class Plotter:

    def __init__(self, df, **kwargs):
        self.df = df
        for key, value in kwargs.items():
            setattr(self, key, value)

    def plot_measurement_chart(self):
        plt.figure(figsize=(14, 8))
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
        fig = plt.figure(figsize=(14, 8))
        ax = fig.add_subplot(111)
        plt.semilogx(self.df['Duration'], self.df['Inlet_Pressure'], color='C0', linestyle='-', label='Messwerte')
        plt.semilogx(self.df['Duration'], self.df['Outlet_Pressure'], color='C0', linestyle='-')
        plt.scatter(self.df['Duration'], self.calc_data['Inlet_Pressure'] * 1e-6, color='r', s=3, label='Rechenwerte')
        plt.scatter(self.df['Duration'], self.calc_data['Outlet_Pressure'] * 1e-6, color='r', s=3)
        # plot stepwise solution
        try:
            self.intervals[1]
            ax2 = ax.twinx()
            ax2.plot(self.intervals[1], self.intervals[0], color='k', marker="o", ls="")
            k_intervals_sorted = sorted(self.intervals[0])
            ax2.set_ylim(10 ** np.ceil(np.log10(k_intervals_sorted[-1])), 10 ** (np.ceil(np.log10(k_intervals_sorted[0])) - 1))
            ax2.set_yscale('log')
            ax2.set_ylabel('Permeabilität [m²]', fontsize=16)
        except:
            pass

        ax.legend()
        ax.grid(True)
        ax.grid(True, which='minor', linestyle='--')
        ax.set_xlim(left=1)
        ax.set_xlabel('Zeit in s', fontsize=16)
        ax.set_ylabel('Druck in MPa', fontsize=16)
        ax.set_title(self.name, fontsize=16)
        plt.show()


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

        result = [inlet_pressure_calculated, outlet_pressure_calculated]
        chamber_pressure = pd.DataFrame(result).transpose()
        chamber_pressure.columns = ['Inlet_Pressure', 'Outlet_Pressure']
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
            pass
        return result


class Optimizer:

    def __init__(self, measured_data, general_data, initial_guess):
        self.measured_data = measured_data
        self.general_data = general_data
        self.initial_guess = initial_guess
        self.error = []
        self.k_iterative = []

    def nelder_mead(self):
        min_result = optimize.minimize(self.iteration, self.initial_guess[0], method='Nelder-Mead',
                                       options={'disp': True}, tol=0.001)
        print(min_result)
        # recalculate with best fit parameters
        self.initial_guess[0] = min_result.x
        chamber_pressure, _ = LinearSystem(self.measured_data,
                                           self.general_data,
                                           self.initial_guess).solve_linear_system()
        return chamber_pressure, min_result.x[0]

    def iteration(self, guess):
        guess = [guess[0], self.initial_guess[1]]
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


class Main:

    def __init__(self, path):
        self.path = path
        self.measured_data = None
        self.general_data = None
        self.chamber_pressure = None

    def single_run(self, initial_guess):
        self.set_data('2KA')
        self.chamber_pressure, _ = LinearSystem(self.measured_data, self.general_data,
                                                initial_guess).solve_linear_system()
        self.plot_result()

    def optimize_perm_1d(self, initial_guess):
        self.set_data('2KA')
        self.chamber_pressure, _ = Optimizer(self.measured_data, self.general_data,
                                             initial_guess).nelder_mead()
        self.plot_result()

    def optimize_reaktor(self, initial_guess):
        self.set_data('Reaktor')
        self.chamber_pressure, _ = Optimizer(self.measured_data, self.general_data,
                                             initial_guess).nelder_mead()
        self.plot_result()

    def optimize_measurement_intervals(self, initial_guess):
        time_interval = []
        k_interval = []
        self.general_data = MeasurementData(self.path).get_general_data()
        for step in range(1,6):
            self.measured_data = MeasurementData(self.path).interpolate_data(step=step)
            self.chamber_pressure, k = Optimizer(self.measured_data, self.general_data, initial_guess).nelder_mead()
            k_interval.append(k)
            time_interval.append(self.measured_data['Duration'].max())
        #TODO: Variable name
        plot_result = Plotter(self.measured_data, **{'calc_data': self.chamber_pressure,
                                                     'intervals': [k_interval, time_interval],
                                                     'name': 'Messung'})
        plot_result.plot_calculation_chart()


    def optimize_measurement_manual(self, initial_guess):
        self.general_data = MeasurementData(self.path).get_general_data()
        self.measured_data = MeasurementData(self.path).interpolate_data(manual=True)
        for i in range(len(self.measured_data)):
            self.chamber_pressure, _ = Optimizer(self.measured_data[i], self.general_data,
                                             initial_guess).nelder_mead()

    def set_data(self, measurement_typ='2KA'):
        if measurement_typ == '2KA':
            self.measured_data = MeasurementData(self.path).interpolate_data()
            self.general_data = MeasurementData(self.path).get_general_data()
        elif measurement_typ == 'Reaktor':
            self.measured_data = MeasurementDataReaktor(self.path).interpolate_data()
            self.general_data = MeasurementDataReaktor(self.path).get_general_data()

    def plot_result(self):
        filename, _ = os.path.splitext(os.path.split(self.path)[1])

        plot_result = Plotter(self.measured_data, **{'calc_data': self.chamber_pressure, 'name': filename})
        plot_result.plot_calculation_chart()

#x = MeasurementData('C:\\Users\\Martin\\OneDrive\\Promotion\\PERM\\raw_data\\HY_SA2_3.txt')
#x.interpolate_data()

x = Main('C:\\Users\\Martin\\OneDrive\\Promotion\\PERM\\raw_data\\HY_V9.txt')
x.optimize_measurement_manual([1e-22, 0.001])







'''
data = pd.DataFrame({
    'Inlet_Pressure': [10, 9.9, 9.8],
    'Outlet_Pressure': [0.1, 0.2, 0.3],
    'Duration': [1, 1000, 10000],
    'Temperature': [15.18, 15.18, 15.18]})
general_data = {'area': np.pi * 0.25 * 0.1**2, 'length': 0.2, 'gas': 'H2',
                'inlet_chamber_volume': 150*1e-6, 'outlet_chamber_volume': 160*1e-6}
initial_guess = [1e-16, 0.01]

x = Optimizer(data, general_data, initial_guess)
x.gradient_descent()
'''
