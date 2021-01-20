import unittest
from main import LinearSystem
import pandas as pd
import numpy as np


class TestLinearSystem(unittest.TestCase):

    def setUp(self):
        self.data = pd.read_csv('test_data_01.csv')
        general_data = {'area': np.pi * 0.25 * 0.1**2, 'length': 0.2, 'gas': 'H2',
                        'inlet_chamber_volume': 150*1e-6, 'outlet_chamber_volume': 160*1e-6}
        self.initial_guess = [1e-16, 0.01]
        self.eq = LinearSystem(self.data, general_data, self.initial_guess)
        self.eq.number_of_cells = 3

    def tearDown(self):
        pass

    def test_get_initial_pressure(self):
        np.testing.assert_array_equal(self.eq.get_initial_pressure(), [1e7, 1e5, 1e5])

    def test_set_stepsize(self):
        dt = self.data['Duration'].diff()[1:].to_list()
        for step in range(len(dt)):
            self.assertEqual(self.eq.set_stepsize_dt(step), dt[step])

    def test_initialize_permeability_porosity(self):
        permeability, porosity = self.eq.initialize_permeability_porosity()
        np.testing.assert_array_equal(permeability, [1, self.initial_guess[0], 1])
        np.testing.assert_array_equal(porosity, [1, self.initial_guess[1], 1])


    def test_build_diagonals(self):
        pressure = np.array([1e7, 1e5, 1e5])
        self.eq.calculated_data.update({'dt': 9})
        dt = 9
        dx = 0.1

        off_diagonal = [7.176345904e-13 / dx, 1.517955181e-14 / dx]
        main_diagonal = [1.11737513e-10 / dt + off_diagonal[0],
                         6.59645475e-11 * dx / dt + off_diagonal[0] + off_diagonal[1],
                         1.34381873e-10 / dt + off_diagonal[1]]
        solution_vector = [1.1173751e-10 / dt, 6.5964547e-11 / dt * dx, 1.3438187e-10 / dt]

        main, off, vector = self.eq.build_diagonals(pressure)
        np.testing.assert_allclose(main, main_diagonal)
        np.testing.assert_allclose(off, off_diagonal)
        np.testing.assert_allclose(vector, solution_vector)


    #def test_iterate_nonlinear_parameters(self):
        #self.eq1.calculated_data.update({'dt': 1})
        # TODO: Druck fuer alle Iterationen berechnen und die letzte stufe angeben
        #pressure = np.array([9701160.5, 5048228.1, 105583.12])
        #np.testing.assert_allclose(self.eq1.iterate_nonlinear_parameters(), pressure, rtol=1e-6)



if __name__ == '__main__':
    unittest.main()
