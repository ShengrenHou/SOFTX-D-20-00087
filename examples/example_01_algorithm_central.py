import numpy as np

from pycity_scheduling.classes import *
from pycity_scheduling.algorithms import *


# This is a very simple power scheduling example using the central optimization algorithm.

# Define timer, price, weather and environment objects:
t = Timer(op_horizon=2, step_size=3600)
p = Prices(timer=t)
w = Weather(timer=t)
e = Environment(timer=t, weather=w, prices=p)

# City district with aggregator objective "peak-shaving":
cd = CityDistrict(environment=e, objective='peak-shaving')

# Schedule two sample buildings. The buildings' objectives are defined as "price".

# Building no. one comes with fixed load, space heating, electrical heater, pv unit, thermal energy storage, and
# electrical energy storage:
bd1 = Building(environment=e, objective='price')
cd.addEntity(entity=bd1, position=[0, 0])
bes = BuildingEnergySystem(environment=e)
bd1.addEntity(bes)
tes = ThermalEnergyStorage(environment=e, E_Th_max=40, soc_init=0.5)
bes.addDevice(tes)
eh = ElectricalHeater(environment=e, P_Th_nom=10)
bes.addDevice(eh)
ap = Apartment(environment=e)
bd1.addEntity(ap)
load = np.array([10.0, 10.0])
fi = FixedLoad(e, method=0, demand=load)
ap.addEntity(fi)
sh = SpaceHeating(environment=e, method=0, loadcurve=load)
ap.addEntity(sh)
pv = Photovoltaic(environment=e, method=1, peak_power=4.6)
bes.addDevice(pv)
bat = Battery(environment=e, E_El_max=4.8, P_El_max_charge=3.6, P_El_max_discharge=3.6)
bes.addDevice(bat)

# Building no. two comes with deferrable load, curtailable load, space heating, chp unit, thermal energy storage and an
# electrical vehicle:
bd2 = Building(environment=e, objective='price')
cd.addEntity(entity=bd2, position=[0, 0])
bes = BuildingEnergySystem(environment=e)
bd2.addEntity(bes)
tes = ThermalEnergyStorage(environment=e, E_Th_max=35, soc_init=0.5)
bes.addDevice(tes)
chp = CombinedHeatPower(environment=e, P_Th_nom=20.0)
bes.addDevice(chp)
ap = Apartment(environment=e)
bd2.addEntity(ap)
load = np.array([20.0, 20.0])
dl = DeferrableLoad(environment=e, P_El_Nom=2.0, E_Consumption=2.0, load_time=[1, 1])
ap.addEntity(dl)
cl = CurtailableLoad(environment=e, P_El_Nom=1.6, max_curtailment=0.8)
ap.addEntity(cl)
sh = SpaceHeating(environment=e, method=0, loadcurve=load)
ap.addEntity(sh)
ev = ElectricalVehicle(environment=e, E_El_max=37.0, P_El_max_charge=22.0, soc_init=0.65, charging_time=[0, 1])
ap.addEntity(ev)

# Perform the scheduling:
r = central_optimization(city_district=cd)
cd.copy_schedule("central")

# Print the building's schedules:
print("Schedule building no. one:")
print(list(bd1.P_El_Schedule))
print("Schedule building no. two:")
print(list(bd2.P_El_Schedule))
print("Schedule of the city district:")
print(list(cd.P_El_Schedule))

# Conclusions:
# If the central optimization algorithm is applied, the two buildings are scheduled in a way so that both the local and
# system level objectives are satisfied. Local flexibility is used to achieve the system level goal. The central
# optimization, however, is considered inexpedient as it does not satisfy the data privacy safeguard of local buildings
# (customers) and does not fulfil scalability requirements. For this reason, it should be used for reference scheduling
# purposes only.
