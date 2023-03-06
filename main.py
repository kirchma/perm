import os
import glob
import pandas as pd
from measurement import Measurement, MeasurementReaktor

import settings
settings.init()

pd.set_option('display.width', 400)
pd.set_option('display.max_columns', 10)


#path = '/Users/kirch/code/raw_data/casing2co2_part3.txt'
#measurement = Measurement(path=path)
#measurement.calculate_permeability([1e-19, 0.1], parameter='k')
#measurement.richardson_extrapolation([5.678080e-19, 0.0001])

#path = '/Users/kirch/code/raw_data/RT_HG02_07_CO2.txt'
#measurement = MeasurementReaktor(path=path)
#measurement.calculate_permeability([1e-18, 0.001], parameter='both')


#samples = ['HY_S05']
#for i in range(len(samples)):
#    path = os.path.join('/Users/kirch/code/raw_data/' + samples[i] + '.txt')
#    measurement = Measurement(path=path)
#    measurement.calculate_uncertainty()
