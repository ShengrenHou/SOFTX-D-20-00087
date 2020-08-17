import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec

from pycity_scheduling.classes import *
from pycity_scheduling.algorithms import *

# ToDo: Why does the central algorithm fail in this example?


# This is a very simple power scheduling example using the central optimization algorithm to demonstrate the impact
# of system level objective "price".

# Define timer, price, weather and environment objects:
t = Timer(op_horizon=96, step_size=900, initial_date=(2015, 4, 1))
p = Prices(timer=t)
w = Weather(timer=t)
e = Environment(timer=t, weather=w, prices=p)

# City district with aggregator objective "peak-shaving":
cd = CityDistrict(environment=e, objective='price')

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
cd.copy_schedule("price")

# Print and show the city district's schedule:
print("Schedule of the city district:")
print(list(cd.P_El_Schedule))

gs = gridspec.GridSpec(2, 1)
ax0 = plt.subplot(gs[0])
ax0.plot(list(range(e.timer.timesteps_used_horizon)), cd.P_El_Schedule)
plt.ylim([-100.0, 200.0])
plt.ylabel('Electrical power in kW')
plt.title('City district scheduling result')

ax1 = plt.subplot(gs[1], sharex=ax0)
ax1.plot(list(range(e.timer.timesteps_used_horizon)), e.prices.da_prices)
plt.ylabel('Spot market day-ahead prices in ct/kWh')

plt.xlabel('Time in hours', fontsize=12)

figManager = plt.get_current_fig_manager()
figManager.window.state("zoomed")
plt.show()

# Conclusions:
# Using "price" as the system level objective results in a "cheap" power profile for the considered city district.
# In other words, this means that power is bought from the spot market during cheap tariff periods and sold during
# expensive tariff periods incorporating the local flexibility potentials. A cost-optimal power profile is usually
# the preferred option by a district operator.
