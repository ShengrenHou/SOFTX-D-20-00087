import copy

import matplotlib.pyplot as plt
from matplotlib import gridspec
import pycity_scheduling.util.factory as factory
from pycity_scheduling.classes import *
from pycity_scheduling.algorithms import *

import numpy as np

env = factory.generate_standard_environment(step_size=3600, op_horizon=24, mpc_horizon=None, mpc_step_width=None,
                                            initial_date=(2018, 2, 10), initial_time=(0, 0, 0))

cd = CityDistrict(environment=env, objective='peak-shaving')

bd1 = Building(environment=env, objective='peak-shaving')
cd.addEntity(entity=bd1, position=[0, 0])
ap1 = Apartment(environment=env)
bd1.addEntity(ap1)
sh1 = SpaceHeating(environment=env, method=1, livingArea=160, specificDemand=95.9, profile_type='HEF')
#load = np.array([10, 10, 15, 12, 9, 8, 11, 13, 17, 10, 14, 16, 12, 14, 16, 10, 11, 9, 14, 15, 17, 18, 9, 10])
#sh1 = SpaceHeating(env, method=0, loadcurve=load)
ap1.addEntity(sh1)
bes1 = BuildingEnergySystem(environment=env)
bd1.addEntity(bes1)
tes1 = ThermalEnergyStorage(environment=env, E_Th_max=40.0, soc_init=0.5)
bes1.addDevice(tes1)
hp1 = HeatPump(environment=env, P_Th_nom=8.0)
bes1.addDevice(hp1)
pv1 = Photovoltaic(environment=env, area=60.0, eta=0.18)
bes1.addDevice(pv1)
fi = FixedLoad(environment=env, method=1, annualDemand=3000.0, profileType="H0")
#fi = FixedLoad(env, method=0, demand=load)
ap1.addEntity(fi)

eh1 = ElectricalHeater(environment=env, P_Th_nom=2.0)
bes1.addDevice(eh1)

#bd2 = copy.deepcopy(bd1)
#cd.addEntity(entity=bd2, position=[0, 1])

central_optimization(cd)

# Plot PV power
plot_time = list(range(env.timer.timestepsUsedHorizon))
figure = plt.figure(figsize=(6, 6))

gs = gridspec.GridSpec(5, 1)
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

ax2 = plt.subplot(gs[3], sharex=ax0)
ax2.plot(plot_time, fi.P_El_Schedule)
plt.grid()
plt.ylabel("fixed load [kW]")

ax3 = plt.subplot(gs[4], sharex=ax0)
ax3.plot(plot_time, tes1.P_Th_Schedule)
plt.grid()
plt.xlabel("Time", fontsize=12)
plt.ylabel("Thermal Energy Storage [kWh]")
plt.ylim((0, 40))
plt.show()
