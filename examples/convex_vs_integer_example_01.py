import matplotlib.pyplot as plt
from matplotlib import gridspec

import pycity_scheduling.util.factory as factory
from pycity_scheduling.classes import *
from pycity_scheduling.algorithms import *

# ToDo: Fix from Gitlab required. Then adjust and fix example.
# ToDo: Why do electro-thermal heating units not follow the SH Profile without TES?! Fixed!!! :)

# Scheduling will be performed for a typical winter day within the annual heating period:
env = factory.generate_standard_environment(step_size=900, op_horizon=96, mpc_horizon=None, mpc_step_width=None,
                                            initial_date=(2010, 2, 10), initial_time=(0, 0, 0))

# City district / aggregator objective is peak-shaving:
cd = CityDistrict(environment=env, objective='peak-shaving')

# Building equipped with space heating, heat pump, photovoltaic unit and battery storage.
# Objective is peak-shaving:
bd1 = Building(environment=env, objective='peak-shaving')
cd.addEntity(entity=bd1, position=[0, 0])
ap1 = Apartment(environment=env)
bd1.addEntity(ap1)
sh1 = SpaceHeating(environment=env, method=1, livingArea=140, specificDemand=85.9, profile_type='HEF')
ap1.addEntity(sh1)
bes1 = BuildingEnergySystem(environment=env)
bd1.addEntity(bes1)
hp1 = HeatPump(environment=env, P_Th_nom=16.0, cop=3.0)
bes1.addDevice(hp1)
pv1 = Photovoltaic(environment=env, area=60.0, eta=0.18)
bes1.addDevice(pv1)
bat1 = Battery(environment=env, E_El_max=13.5, P_El_max_charge=4.6)
bes1.addDevice(bat1)


# First, perform the scheduling using convex models for the electrical appliances:
central_optimization(cd, mode='convex')
cd.copy_schedule("convex_schedule")

# Plot the convex schedules:
plot_time = list(range(env.timer.timestepsUsedHorizon))
figure = plt.figure(figsize=(6, 6))

gs = gridspec.GridSpec(5, 1)
ax0 = plt.subplot(gs[0])
ax0.plot(plot_time, cd.P_El_Schedule)
plt.xlim((0, env.timer.timestepsUsedHorizon - 1))
plt.ylim([-3, 3])
plt.title("Convex Schedules")
plt.ylabel("District [kW]")
plt.grid()

ax1 = plt.subplot(gs[1], sharex=ax0)
ax1.plot(plot_time, pv1.P_El_Schedule)
plt.xlim((0, env.timer.timestepsUsedHorizon - 1))
plt.ylabel("PV [kW]")
plt.grid()

ax2 = plt.subplot(gs[2], sharex=ax0)
ax2.plot(plot_time, hp1.P_Th_Schedule)
plt.xlim((0, env.timer.timestepsUsedHorizon - 1))
plt.ylabel("El. Heater [kW]")
plt.grid()

ax3 = plt.subplot(gs[3], sharex=ax0)
ax3.plot(plot_time, bat1.P_El_Schedule)
plt.xlim((0, env.timer.timestepsUsedHorizon - 1))
plt.ylabel("Bat. Power [kW]")
plt.grid()

ax4 = plt.subplot(gs[4], sharex=ax0)
ax4.plot(plot_time, bat1.E_El_Schedule)
plt.xlim((0, env.timer.timestepsUsedHorizon - 1))
plt.ylabel("Bat. SoC [kWh]")
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
plt.xlim((0, env.timer.timestepsUsedHorizon - 1))
plt.ylim([-3, 3])
plt.title("Integer Schedules")
plt.ylabel("District [kW]")
plt.grid()

ax1 = plt.subplot(gs[1], sharex=ax0)
ax1.plot(plot_time, pv1.P_El_Schedule)
plt.xlim((0, env.timer.timestepsUsedHorizon - 1))
plt.ylabel("PV [kW]")
plt.grid()

ax2 = plt.subplot(gs[2], sharex=ax0)
ax2.plot(plot_time, hp1.P_Th_Schedule)
plt.xlim((0, env.timer.timestepsUsedHorizon - 1))
plt.ylabel("El. Heater [kW]")
plt.grid()

ax3 = plt.subplot(gs[3], sharex=ax0)
ax3.plot(plot_time, bat1.P_El_Schedule)
plt.xlim((0, env.timer.timestepsUsedHorizon - 1))
plt.ylabel("Bat. Power [kW]")
plt.grid()

ax4 = plt.subplot(gs[4], sharex=ax0)
ax4.plot(plot_time, bat1.E_El_Schedule)
plt.xlim((0, env.timer.timestepsUsedHorizon - 1))
plt.ylabel("Bat. SoC [kWh]")
plt.grid()

plt.xlabel("Time", fontsize=12)

figManager = plt.get_current_fig_manager()
figManager.window.state("zoomed")
plt.show()
