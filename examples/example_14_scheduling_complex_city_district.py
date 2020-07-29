import matplotlib.pyplot as plt
from matplotlib import gridspec

import numpy as np

import pycity_scheduling.util.factory as factory
import pycity_scheduling.algorithms as algs
from pycity_scheduling.classes import *

# This example is built upon the district setup as defined in example 'example_12_district_generator.py'.
# However, the city district scenario contains more than 100 buildings and is hence considered complex.
env = factory.generate_standard_environment(initial_date=(2018, 12, 6), step_size=900, op_horizon=96)

# 75 single-family houses
num_sfh = 75

# 50% SFH.2002, 30% SFH.2010, 20% SFH.2016
sfh_distribution = {
    'SFH.2002': 0.5,
    'SFH.2010': 0.3,
    'SFH.2016': 0.2,
}

# 50% with heat pump, 10% with boiler, 30% with electrical heater, 10% with chp:
sfh_heating_distribution = {
    'HP': 0.5,
    'BL': 0.1,
    'EH': 0.3,
    'CHP': 0.1,
}

# all apartments have a fixed load, 20% have a deferrable load, 30% have an
# electric vehicle
#
# 50% of buildings have a battery, 80% have a rooftop photovoltaic unit
# The values are rounded in case they cannot be perfectly matched to the given number of buildings.
sfh_device_probs = {
    'FL': 1.0,
    'DL': 0.2,
    'EV': 0.3,
    'BAT': 0.5,
    'PV': 0.8,
}

# 25 multi-family houses, number of apartments stems from Tabula:
num_mfh = 25
mfh_distribution = {
    'MFH.2002': 0.6,
    'MFH.2010': 0.2,
    'MFH.2016': 0.2,
}
mfh_heating_distribution = {
    'HP': 0.5,
    'BL': 0.1,
    'EH': 0.3,
    'CHP': 0.1,
}
mfh_device_probs = {
    'FL': 1.0,
    'DL': 0.2,
    'EV': 0.2,
    'BAT': 0.4,
    'PV': 0.8,
}
district = factory.generate_tabula_district(env, num_sfh, num_mfh,
                                            sfh_distribution,
                                            sfh_heating_distribution,
                                            sfh_device_probs,
                                            mfh_distribution,
                                            mfh_heating_distribution,
                                            mfh_device_probs,
                                            district_objective='peak-shaving',
                                            building_objective='price'
                                            )

# To cover the city district's load, it is supplied by a wind energy converter of approx. 2MWp:
v = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 99])
p = np.array([0, 0, 3, 25, 82, 174, 321, 532, 815, 1180, 1580, 1810, 1980, 2050, 2050, 2050, 2050, 2050, 2050, 2050,
              2050, 2050, 2050, 2050, 2050, 2050, 0, 0])
wec = WindEnergyConverter(env, velocity=v, power=p, hub_height=78.0)
district.addEntity(wec, [0, 0])

# Perform the scheduling (city district/aggregator objective is peak shaving, buildings' objectives is price):
algs.central_optimization(district)

# Plot scheduling results:
plot_time = list(range(env.timer.timestepsUsedHorizon))
figure = plt.figure(figsize=(6, 6))

gs = gridspec.GridSpec(1, 1)
ax0 = plt.subplot(gs[0])
ax0.plot(plot_time, district.P_El_Schedule)
plt.grid()
plt.ylabel("City District Power [kW]")
plt.xlim((0, env.timer.timestepsUsedHorizon - 1))
plt.title("Complex City District Scenario - Schedule")
plt.show()
