import pandas as pd
from measurement import Measurement

pd.set_option('display.width', 400)
pd.set_option('display.max_columns', 10)


path = '/Users/mkirch/OneDrive/Promotion/PERM/raw_data/HY_S01.txt'
measurement = Measurement(path=path)
measurement.calculate_permeability([1e-22, 0.001], parameter='both')