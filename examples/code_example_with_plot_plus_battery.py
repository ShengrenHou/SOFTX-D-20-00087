import matplotlib.pyplot as plt
from matplotlib import gridspec

import pycity_scheduling.util.factory as factory
from pycity_scheduling.classes import *
from pycity_scheduling.algorithms import *

# Variable whether to have a backup heater or not:
BACKUP_HEATER = True


env = factory.generate_standard_environment(step_size=900, op_horizon=96, mpc_horizon=None, mpc_step_width=None,
                                            initial_date=(2010, 2, 10), initial_time=(0, 0, 0))

cd = CityDistrict(environment=env, objective='peak-shaving')

bd1 = Building(environment=env, objective='peak-shaving')
cd.addEntity(entity=bd1, position=[0, 0])
ap1 = Apartment(environment=env)
bd1.addEntity(ap1)
sh1 = SpaceHeating(environment=env, method=1, livingArea=160, specificDemand=95.9, profile_type='HEF')
ap1.addEntity(sh1)
bes1 = BuildingEnergySystem(environment=env)
bd1.addEntity(bes1)
tes1 = ThermalEnergyStorage(environment=env, E_Th_max=10.0, soc_init=0.5)
bes1.addDevice(tes1)
hp1 = HeatPump(environment=env, P_Th_nom=8.0)
bes1.addDevice(hp1)
pv1 = Photovoltaic(environment=env, area=60.0, eta=0.18)
bes1.addDevice(pv1)
# New battery:
bat1 = Battery(environment=env, E_El_max=2.0, P_El_max_charge=10.0)
bes1.addDevice(bat1)

if BACKUP_HEATER:
    eh1 = ElectricalHeater(environment=env, P_Th_nom=2.0)
    bes1.addDevice(eh1)

#central_optimization(cd, mode='convex')  # Default!
central_optimization(cd, mode='integer')

# Plot PV power
plot_time = list(range(env.timer.timestepsUsedHorizon))
figure = plt.figure(figsize=(6, 6))

gs = gridspec.GridSpec(6, 1)
ax0 = plt.subplot(gs[0])
ax0.plot(plot_time, cd.P_El_Schedule)
plt.grid()
plt.ylabel("City District [kW]")
plt.xlim((0, env.timer.timestepsUsedHorizon - 1))
plt.ylim((-3, 3))
plt.title("Schedules")

ax1 = plt.subplot(gs[1], sharex=ax0)
ax1.plot(plot_time, pv1.P_El_Schedule)
plt.grid()
plt.ylabel("PV [kW]")

ax2 = plt.subplot(gs[2], sharex=ax0)
ax2.plot(plot_time, hp1.P_El_Schedule)
plt.grid()
plt.ylabel("Heat Pump [kW]")
"""
ax2 = plt.subplot(gs[3], sharex=ax0)
ax2.plot(plot_time, bat1.P_El_Schedule)
plt.grid()
plt.ylabel("Battery [kW]")
"""

ax2 = plt.subplot(gs[4], sharex=ax0)
ax2.plot(plot_time, eh1.P_El_Schedule)
plt.grid()
plt.ylabel("electric heater [kW]")

ax3 = plt.subplot(gs[5], sharex=ax0)
ax3.plot(plot_time, tes1.E_Th_Schedule)
plt.grid()
plt.xlabel("Time", fontsize=12)
plt.ylabel("Thermal Energy Storage [kWh]")
plt.ylim((0, 40))
plt.show()