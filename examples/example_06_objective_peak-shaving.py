import numpy as np
import matplotlib.pyplot as plt


from pycity_scheduling.classes import *
from pycity_scheduling.algorithms import *


# This is a very simple power scheduling example using the central optimization algorithm to demonstrate the impact
# of system level objective "peak-shaving".

# Define timer, price, weather and environment objects:
t = Timer(op_horizon=96, step_size=900, initial_date=(2015, 4, 1))
p = Prices(timer=t)
w = Weather(timer=t)
e = Environment(timer=t, weather=w, prices=p)

# City district with aggregator objective "peak-shaving":
cd = CityDistrict(environment=e, objective='peak-shaving')

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
cd.copy_schedule("peak-shaving")

# Print and show the city district's schedule:
print("Schedule of the city district:")
print(list(cd.P_El_Schedule))
plt.plot(cd.P_El_Schedule)
plt.ylim([-2.0, 5.0])
plt.xlabel('Time in hours')
plt.ylabel('Electrical power in kW')
plt.title('City district scheduling result')
plt.show()

# Conclusions:
# Using "peak-shaving" as the system level objective results in a "flat" power profile for the considered city district.
# In other words, this means that power peaks (caused by peak demands) and power valleys (caused by PV feed-in) are
# mitigated using the local flexibility of the buildings' assets. A flat power profile is usually the preferred system
# operation from the viewpoint of a grid operator.
