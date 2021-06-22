'''
from uncertainties import ufloat
import numpy as np

diameter = ufloat(101.01, 0.04)
length = ufloat(203.37, 0.04)

volume_sample = np.pi * 0.25 * diameter**2 * length * 0.001



p1 = ufloat(97.37, 100*0.0015)
p2 = ufloat(1, 60*0.0015)
p_ges = ufloat(46.9, 60*0.0015)
V1 = ufloat(167.37, 1)
V2 = ufloat(169.94, 1)

#volume_pore = (p1*V1 + p2*V2 - p_ges*(V1+V2)) / (p_ges - p3)
volume_pore = (p1*V1 + p2*V2 - p_ges*(V1+V2)) / (p_ges - p2)

porosity = volume_pore / volume_sample *100


print(f'Gesamtes Anlagenvolumen {V1+V2:.2f}')

print(f'{volume_sample:.2f}')
print(f'{volume_pore:.2f}')
print(f'{porosity:.2f}')
'''


# stationaere Permeabilitaetsberechnung
from uncertainties import ufloat
import CoolProp.CoolProp as cp
import numpy as np


q = [1.088, 1.044, 0.895]
p = [1.517, 1.385, 1.242]

q = [2.065, 1.615, 1.380, 0.913, 0.715, 0.324]
p = [1.682, 1.381, 1.209, 0.822, 0.633, 0.190]

k_list = []
pm_list =[]

for i in range(6):
    Q = ufloat(q[i], q[i] * 0.006) / (1000*60)
    pe = ufloat((p[i] + 0.973) * 1e5, 1200)

    L = ufloat(0.05137, 0.00004)
    D = ufloat(0.05003, 0.00002)
    A = np.pi * 0.25 * D**2

    pa = p_atm = ufloat(0.973 * 1e5, 500)
    pm = (pe + pa) / 2
    T = ufloat((22.75 + 273.15), 0.1)
    eta = cp.PropsSI('VISCOSITY', 'T', T.n, 'P', pm.n, 'N2')

    k = 2*Q*L*eta*p_atm / (A*(pe**2 - pa**2))
    k_list.append(k.n)
    pm_list.append(1/pm.n)
    print(f'k = {k:.3g}, p_m = {pm.n:.3g}')
    #print(1/pm)


inlet_pressure = p[0]
outlet_pressure = pa
mean_pressure = (inlet_pressure + outlet_pressure) / 2 * 1e-5
k_i = k_list[2] * 1e-10

for _ in range(5):
    f = 3.05351e-6 * k_i ** 0.65 / mean_pressure + k_i - k_list[0]
    f_diff = 1.98478e-6 / (mean_pressure * k_i ** 0.35) + 1
    k_new = k_i - f / f_diff
    k_i = k_new

print(k_i)



from matplotlib import pyplot as plt

fig = plt.figure(figsize=(14,10))
plt.subplot(111)
plt.xlim(0, 9e-6)
plt.ylim(1e-14, 1e-13)


plt.plot(pm_list[:-1], k_list[:-1])
plt.show()



