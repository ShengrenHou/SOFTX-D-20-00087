import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec

from pycity_scheduling.classes import *
from pycity_scheduling.algorithms import *


# This is a very simple power scheduling example using the central optimization algorithm to demonstrate the impact
# of system level objective "valley-filling".

# Define timer, price, weather and environment objects:
t = Timer(op_horizon=96, step_size=900, initial_date=(2015, 4, 1))
p = Prices(timer=t)
w = Weather(timer=t)
e = Environment(timer=t, weather=w, prices=p)

# City district with aggregator objective "valley-filling":
valley_profile = [3.0 for i in range(24)] + [4.0 for i in range(24)] + [3.5 for i in range(48)]
cd = CityDistrict(environment=e, objective='valley-filling', valley_profile=np.array(valley_profile))

# Schedule some sample buildings. The buildings' objectives are defined as "none".
n = 10
for i in range(n):
    bd = Building(environment=e, objective='none')
    cd.addEntity(entity=bd, position=[0, i])
    bes = BuildingEnergySystem(environment=e)
    bd.addEntity(bes)
    tes = ThermalEnergyStorage(environment=e, E_Th_max=40, soc_init=0.5)
    bes.addDevice(tes)
    eh = ElectricalHeater(environment=e, P_Th_nom=10)
    bes.addDevice(eh)
    ap = Apartment(environment=e)
    bd.addEntity(ap)
    fi = FixedLoad(e, method=1, annual_demand=3000.0, profile_type='H0')
    ap.addEntity(fi)
    sh = SpaceHeating(environment=e, method=1, living_area=120, specific_demand=90, profile_type='HEF')
    ap.addEntity(sh)
    pv = Photovoltaic(environment=e, method=1, peak_power=8.2)
    bes.addDevice(pv)
    bat = Battery(environment=e, E_El_max=12.0, P_El_max_charge=4.6, P_El_max_discharge=4.6)
    bes.addDevice(bat)


# Perform the scheduling:
r = central_optimization(city_district=cd)
cd.copy_schedule("valley-filling")

# Print and show the city district's schedule:
print("Schedule of the city district:")
print(list(cd.P_El_Schedule))

gs = gridspec.GridSpec(3, 1)
ax0 = plt.subplot(gs[0])
ax0.plot(list(range(e.timer.timesteps_used_horizon)), cd.P_El_Schedule)
plt.ylim([-2.0, 5.0])
plt.ylabel('Electrical power in kW')
plt.title('City district scheduling result')

ax1 = plt.subplot(gs[1], sharex=ax0)
ax1.plot(list(range(e.timer.timesteps_used_horizon)), valley_profile)
plt.ylabel('Reference power curve in kW')

ax1 = plt.subplot(gs[2], sharex=ax0)
ax1.plot(list(range(e.timer.timesteps_used_horizon)), np.array(cd.P_El_Schedule) + np.array(valley_profile))
plt.ylim([0.0, 10.0])
plt.ylabel('Sum of both power curves in kW')

plt.xlabel('Time in hours', fontsize=12)

figManager = plt.get_current_fig_manager()
figManager.window.state("zoomed")
plt.show()

# Conclusions:
# Using "valley-filling" as the system level objective results in a "inverse" power profile for the considered city
# district compared to the "reference" power curve. The reference power curve usually represents a baseline with several
# power peaks and valleys that should get "compensated" taking advantage of the local flexibility potentials. In other
# words, this means that the sum of the city district's power profile and the reference power curve results in a "flat"
# power profile. This is usually the preferred system operation from the viewpoint of a grid operator and/or district
# operator.
