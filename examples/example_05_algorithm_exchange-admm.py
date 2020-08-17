import numpy as np

from pycity_scheduling.classes import *
from pycity_scheduling.algorithms import *

# ToDo: Check why DeferrableLoad and ElectricalVehicle fails!

# This is a very simple power scheduling example using the distributed ADMM algorithm.

# Define timer, price, weather and environment objects:
t = Timer(op_horizon=2)
p = Prices(t)
w = Weather(t)
e = Environment(t, w, p)

# City district / aggregator objective is peak-shaving:
cd = CityDistrict(e, objective='peak-shaving')

# Schedule two sample buildings. The first building has no objective, the second building's objective is price.

# Building no. one comes with fixed load, space heating, electrical heater, pv unit, and thermal energy storage
bd1 = Building(e, objective='none')
cd.addEntity(bd1, [0, 0])
bes = BuildingEnergySystem(e)
bd1.addEntity(bes)
tes = ThermalEnergyStorage(e, 40, 0.5)
bes.addDevice(tes)
eh = ElectricalHeater(e, 10)
bes.addDevice(eh)
ap = Apartment(e)
bd1.addEntity(ap)
load = np.array([10, 10])
fi = FixedLoad(e, method=0, demand=load)
ap.addEntity(fi)
sh = SpaceHeating(e, method=0, loadcurve=load)
ap.addEntity(sh)
pv = Photovoltaic(e, method=1, peak_power=4.6)
bes.addDevice(pv)

# Building no. two comes with deferrable load, curtailable load, space heating, chp unit, thermal energy storage and an
# electrical vehicle
bd2 = Building(e, objective='price')
cd.addEntity(bd2, [0, 0])
bes = BuildingEnergySystem(e)
bd2.addEntity(bes)
tes = ThermalEnergyStorage(e, 40, 0.5)
bes.addDevice(tes)
chp = CombinedHeatPower(e, 20.0)
bes.addDevice(chp)
ap = Apartment(e)
bd2.addEntity(ap)
load = np.array([20, 20])
#dl = DeferrableLoad(e, 3.0, 1.5)
#ap.addEntity(dl)
cl = CurtailableLoad(e, 1.5, 0.8)
ap.addEntity(cl)
sh = SpaceHeating(e, method=0, loadcurve=load)
ap.addEntity(sh)
#ev = ElectricalVehicle(e, 37.0, 11.0)
#ap.addEntity(ev)

# Perform the scheduling
r = exchange_admm(cd, rho=2.0, eps_primal=0.001, eps_dual=0.01)
cd.copy_schedule("admm")

# Print some ADMM results:
print("ADMM - Number of iterations:")
print(r[0])
print("ADMM - Norm vector 'r' over iterations:")
print(r[1])
print("ADMM - Norm vector 's' over iterations:")
print(r[2])
print("")

# Print the building's schedules:
print("Schedule building no. one:")
print(list(bd1.P_El_Schedule))
print("Schedule building no. two:")
print(list(bd2.P_El_Schedule))
