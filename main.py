import pandas as pd
from measurement import Measurement, MeasurementReaktor

pd.set_option('display.width', 400)
pd.set_option('display.max_columns', 10)


path = '/Users/mkirch/OneDrive/Promotion/PERM/raw_data/HY_A3_06.txt'
measurement = Measurement(path=path)
measurement.calculate_permeability([1e-18, 0.001], parameter='both')

#path = '/Users/mkirch/OneDrive/Promotion/PERM/raw_data/HY_RV5_05.txt'
#measurement = MeasurementReaktor(path=path)
#measurement.calculate_permeability([1e-18, 0.001], parameter='both')