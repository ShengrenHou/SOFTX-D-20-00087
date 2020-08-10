import matplotlib.pyplot as plt
from matplotlib import gridspec

import pycity_scheduling.util.factory as factory
from pycity_scheduling.classes import *
from pycity_scheduling.algorithms import *


# Scheduling will be performed for a typical winter day within the annual heating period:
env = factory.generate_standard_environment(step_size=3600, op_horizon=24, mpc_horizon=None, mpc_step_width=None,
                                            initial_date=(2010, 2, 10), initial_time=(0, 0, 0))

# City district / aggregator objective is peak-shaving:
cd = CityDistrict(environment=env, objective='peak-shaving')

# Building equipped with space heating, electrical heater, thermal energy storage, and photovoltaic unit.
# Objective is peak-shaving:
bd1 = Building(environment=env, objective='peak-shaving')
cd.addEntity(entity=bd1, position=[0, 0])
ap1 = Apartment(environment=env)
bd1.addEntity(ap1)
sh1 = SpaceHeating(environment=env, method=1, livingArea=120.0, specificDemand=85.9, profile_type='HEF')
ap1.addEntity(sh1)
bes1 = BuildingEnergySystem(environment=env)
bd1.addEntity(bes1)
eh1 = ElectricalHeater(environment=env, P_Th_nom=12.0, lower_activation_limit=0.5)
bes1.addDevice(eh1)
tes1 = ThermalEnergyStorage(environment=env, E_Th_max=24.0)
bes1.addDevice(tes1)
pv1 = Photovoltaic(environment=env, area=100.0, eta=0.18)
bes1.addDevice(pv1)


# First, perform the scheduling using convex models for the electrical appliances:
central_optimization(cd, mode='convex')
cd.copy_schedule("convex_schedule")

# Plot the convex schedules:
plot_time = list(range(env.timer.timesteps_used_horizon))
figure = plt.figure(figsize=(6, 6))

gs = gridspec.GridSpec(5, 1)
ax0 = plt.subplot(gs[0])
ax0.plot(plot_time, cd.P_El_Schedule)
plt.xlim((0, env.timer.timesteps_used_horizon - 1))
plt.ylim([-15, 15])
plt.title("Convex Schedules")
plt.ylabel("District [kW]")
plt.grid()

ax1 = plt.subplot(gs[1], sharex=ax0)
ax1.plot(plot_time, pv1.P_El_Schedule)
plt.xlim((0, env.timer.timesteps_used_horizon - 1))
plt.ylabel("PV [kW]")
plt.grid()

ax2 = plt.subplot(gs[2], sharex=ax0)
ax2.plot(plot_time, sh1.P_Th_Schedule)
plt.xlim((0, env.timer.timesteps_used_horizon - 1))
plt.ylabel("Space Heating Demand [kW]")
plt.grid()

ax3 = plt.subplot(gs[3], sharex=ax0)
ax3.plot(plot_time, eh1.P_El_Schedule)
plt.xlim((0, env.timer.timesteps_used_horizon - 1))
plt.ylabel("El. Heater [kW]")
plt.grid()

ax4 = plt.subplot(gs[4], sharex=ax0)
ax4.plot(plot_time, tes1.E_Th_Schedule)
plt.xlim((0, env.timer.timesteps_used_horizon - 1))
plt.ylabel("TES SoC [kWh]")
plt.grid()

plt.xlabel("Time", fontsize=12)

figManager = plt.get_current_fig_manager()
figManager.window.state("zoomed")
plt.show()

# Second, perform the scheduling using integer models for the electrical appliances:
central_optimization(cd, mode='integer')
cd.copy_schedule("integer_schedule")

# Plot the integer schedules:
gs = gridspec.GridSpec(5, 1)
ax0 = plt.subplot(gs[0])
ax0.plot(plot_time, cd.P_El_Schedule)
plt.xlim((0, env.timer.timesteps_used_horizon - 1))
plt.ylim([-15, 15])
plt.title("Integer Schedules")
plt.ylabel("District [kW]")
plt.grid()

ax1 = plt.subplot(gs[1], sharex=ax0)
ax1.plot(plot_time, pv1.P_El_Schedule)
plt.xlim((0, env.timer.timesteps_used_horizon - 1))
plt.ylabel("PV [kW]")
plt.grid()

ax2 = plt.subplot(gs[2], sharex=ax0)
ax2.plot(plot_time, sh1.P_Th_Schedule)
plt.xlim((0, env.timer.timesteps_used_horizon - 1))
plt.ylabel("Space Heating Demand [kW]")
plt.grid()

ax3 = plt.subplot(gs[3], sharex=ax0)
ax3.plot(plot_time, eh1.P_El_Schedule)
plt.xlim((0, env.timer.timesteps_used_horizon - 1))
plt.ylabel("El. Heater [kW]")
plt.grid()

ax4 = plt.subplot(gs[4], sharex=ax0)
ax4.plot(plot_time, tes1.E_Th_Schedule)
plt.xlim((0, env.timer.timesteps_used_horizon - 1))
plt.ylabel("TES SoC [kWh]")
plt.grid()

plt.xlabel("Time", fontsize=12)

figManager = plt.get_current_fig_manager()
figManager.window.state("zoomed")
plt.show()
