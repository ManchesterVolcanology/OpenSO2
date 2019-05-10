# -*- coding: utf-8 -*-
"""
Created on Thu May  9 14:31:27 2019

@author: mqbpwbe2
"""

import numpy as np
from scipy.interpolate import griddata

start = 300
stop = 325.01
model_grid = np.arange(start, stop, step = 0.01)
o3_temp = '223K'

fpath = 'C:/Users/mqbpwbe2/Dropbox (The University of Manchester)/python_scripts/iFit/data_bases/gas data/'

sol_path  = fpath + 'sao2010.txt'
so2_path  = fpath + 'SO2_295K.txt'
no2_path  = fpath + 'No2_223l.dat'
o3_path   = fpath + 'O3_xsec.dat'
ring_path = fpath + 'qdoas_ring.dat'

sol_header = 'Fraunhofer Reference Spectrum\n' + \
             'Source: Chance, K. and Kurucz, 2010.Quant. Spec. and Rad. Trans. R. L.\n'+\
             'Wavelength (nm),       Intensity (Photons s-1 cm-2 nm-1)'

so2_header = 'SO2 Cross-Section\n' + \
             'Source: Rufus et al. 2003. JGR: Planets\n' + \
             'Interpolated by cublic spline\n' + \
             'Wavelength (nm),       Absorption cross-section (cm2/molec)'

no2_header = 'NO2 Cross-Section\n' + \
             'Source: Voigt et al. 2002. J. Photochem. adn Photobio. A\n' + \
             'Interpolated by cublic spline\n' + \
             'Wavelength (nm),       Absorption cross-section (cm2/molec)'

o3_header =  'O3 Cross-Section\n' + \
             'Source: Gorshelev et al. 2014. AMT\n' + \
             'Interpolated by cublic spline\n' + \
             'Wavelength (nm),       Absorption cross-section (cm2/molec)'

ring_header= 'Ring Spectrum\n' + \
             'Source: Dankert et al, QDOAS User Manual\n' + \
             'Interpolated by cublic spline\n' + \
             'Wavelength (nm),       Ring Correction'

# Import solar reference spectrum
sol_x, sol_y = np.loadtxt(sol_path, unpack = True)
sol_y = np.divide(sol_y, (sol_y.max() / 70000))
sol = griddata(sol_x, sol_y, model_grid, method = 'cubic')
np.savetxt('sol.txt', np.column_stack((model_grid, sol)), header = sol_header)

# Ring spectrum
ring_x, ring_y = np.loadtxt(ring_path, unpack = True)
ring = griddata(ring_x, ring_y, model_grid, method = 'cubic')
np.savetxt('ring.txt', np.column_stack((model_grid, ring)), header = ring_header)

# SO2
so2_grid, so2_xsec = np.loadtxt(so2_path, unpack = True)
so2_xsec = griddata(so2_grid, so2_xsec, model_grid, method = 'cubic')
np.savetxt('so2.txt', np.column_stack((model_grid, so2_xsec)), header = so2_header)

# NO2
no2 = np.loadtxt(no2_path, skiprows=43)
no2_xsec = no2[:,2]
no2_xsec = griddata(no2[:,0], no2_xsec, model_grid, method = 'cubic')
np.savetxt('no2.txt', np.column_stack((model_grid, no2_xsec)), header = no2_header)

# O3
o3_xsec = np.loadtxt(o3_path)

# Get column number from temperature
temps = ['298K', '283K', '273K', '263K', '253K', '243K', '233K', '223K', '213K',
         '203K', '193K']
col_n = temps.index(o3_temp) + 1

# Extract the right spectrum
o3 = o3_xsec[:,col_n]
o3_xsec = griddata(o3_xsec[:,0], o3, model_grid, method = 'cubic')
np.savetxt('o3.txt', np.column_stack((model_grid, o3_xsec)), header = o3_header)
