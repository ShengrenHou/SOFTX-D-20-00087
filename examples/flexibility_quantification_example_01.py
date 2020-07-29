import matplotlib.pyplot as plt
from matplotlib import gridspec

import numpy as np

import pycity_scheduling.util.factory as factory
import pycity_scheduling.algorithms as algs
from pycity_scheduling.util.metric import absolute_flexibility_gain

# This example is built upon the same district setup as defined in example 'district_generator_01.py'
env = factory.generate_standard_environment()

# 20 single-family houses
num_sfh = 20

# 50% SFH.2002, 30% SFH.2010, 20% SFH.2016
sfh_distribution = {
    'SFH.2002': 0.5,
    'SFH.2010': 0.3,
    'SFH.2016': 0.2,
}

# 50% with heat pump, 10% with boiler, 40% with electrical heater:
sfh_heating_distribution = {
    'HP': 0.5,
    'BL': 0.1,
    'EH': 0.4,
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

# 5 multi-family houses, number of apartments stems from Tabula:
num_mfh = 5
mfh_distribution = {
    'MFH.2002': 0.6,
    'MFH.2010': 0.2,
    'MFH.2016': 0.2,
}
mfh_heating_distribution = {
    'HP': 0.4,
    'BL': 0.2,
    'EH': 0.4,
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
                                            building_objective='none'
                                            )

# Perform the scheduling (in this example desired to quantify the city district's maximum flexibility potential):
algs.local_optimization(district)
district.save_ref_schedule()
district.objective = 'flexibility-quantification'
algs.central_optimization(district)

# Print the flexibility metric:
np.set_printoptions(formatter={'float': '{: >8.3f}'.format})
print('Absolute flex. gain (kWh):    {: >8.3f}'.format(absolute_flexibility_gain(district, "Ref")))

# Plot
plot_time = list(range(env.timer.timestepsUsedHorizon))
figure = plt.figure(figsize=(6, 6))

gs = gridspec.GridSpec(2, 1)
ax0 = plt.subplot(gs[0])
ax0.plot(plot_time, district.P_El_Ref_Schedule)
plt.grid()
plt.ylabel("City District Reference [kW]")
plt.xlim((0, env.timer.timestepsUsedHorizon - 1))
plt.title("Schedules")

ax1 = plt.subplot(gs[1], sharex=ax0)
ax1.plot(plot_time, district.P_El_Schedule)
plt.grid()
plt.ylabel("City District [kW]")
plt.show()

# ToDo: Wait for stand-alone algorithm fix.
# ToDo: Implement this flexibility quantification method as a separate util function?!
