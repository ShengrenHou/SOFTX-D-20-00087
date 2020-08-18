import numpy as np

from pycity_scheduling.classes import *
from pycity_scheduling.algorithms import algorithms


t = Timer(op_horizon=14, step_size=3600, initial_time=(0, 0, 0))
p = Prices(t)
w = Weather(t)
e = Environment(t, w, p)
cd = CityDistrict(e, objective='peak-shaving')

bd1 = Building(e, objective='peak-shaving')
cd.addEntity(bd1, [0,0])
bes1 = BuildingEnergySystem(e)
bd1.addEntity(bes1)
tes1 = ThermalEnergyStorage(e, 40, 0.5, 0.5)
bes1.addDevice(tes1)
eh1 = ElectricalHeater(e, 20)
bes1.addDevice(eh1)
bat = Battery(e,50,10,5)
bes1.addDevice(bat)
pv1 = Photovoltaic(e,1000,0.12)
bes1.addDevice(pv1)
ap1 = Apartment(e)
bd1.addEntity(ap1)
#load = np.array([10, 10, 15, 12, 9, 8, 11, 13, 17, 10, 14, 16, 12, 14, 16, 10, 11, 9, 14, 15, 17, 18, 9, 10])
load = np.array([10, 10, 15, 12, 9, 8, 11, 13, 17, 10, 14, 16, 12, 14])
#fi = FixedLoad(environment=e, method=1, annualDemand=3000.0, profileType="H0")
fi1 = FixedLoad(e, method=0, demand=load)
ap1.addEntity(fi1)
sh1 = SpaceHeating(e, method=0, loadcurve=load)
ap1.addEntity(sh1)


bd2 = Building(e, objective='price')
cd.addEntity(bd2, [0, 0])
bes2 = BuildingEnergySystem(e)
bd2.addEntity(bes2)
tes2 = ThermalEnergyStorage(e, 40, 0.5, 0.5)
bes2.addDevice(tes2)
eh2 = ElectricalHeater(e, 20)
bes2.addDevice(eh2)
ap2 = Apartment(e)
bd2.addEntity(ap2)
load2 = np.array([20, 20,10,15])
fi2 = FixedLoad(e, method=0, demand=load)
ap2.addEntity(fi2)
sh2 = SpaceHeating(e, method=0, loadcurve=load)
ap2.addEntity(sh2)


f = algorithms['exchange-admm']
r = f(cd, rho=2, eps_primal=0.001)
"""
print("\nTotal amount of buildings in city district: " + str(len(cd.nodes.items())) + "\n")
print("" + str(cd) + ":")
for building in cd.get_lower_entities():
    print("\t--> " + str(building) + ":")
    for bes in building.get_lower_entities():
        print("\t\t--> " + str(bes) + ":")
        for entity in bes.get_lower_entities():
            print("\t\t\t--> " + str(entity) + "")
print("")
"""
# Algorithm specific outputs:
#print(r[0])
#print(r[1])
#print(r[2])
#print(r[3])

# Scheduling outputs:
print(list(cd.P_El_Schedule))
print(list(pv1.P_El_Schedule))
print(list(bat.P_El_Schedule))
print(list(eh1.P_El_Schedule))
print(list(fi1.P_El_Schedule))
print(list(eh1.P_El_Schedule+fi1.P_El_Schedule+bat.P_El_Schedule+pv1.P_El_Schedule+eh2.P_El_Schedule+fi2.P_El_Schedule))
#print(tes.E_Th_Schedule)   #added by me

#print(tes.P_Th_Schedule)
#print(tes.P_Th_Schedule+eh.P_El_Schedule)
#print(sh.P_Th_Demand)     #added by me
#print(pv.P_El_Schedule)
#for t in range(1,4):
 #   print(tes1.E_Th_Schedule(t+1) )
  #  print(tes1.E_Th_Schedule(t) + tes1.P_Th_Schedule(t) - tes1.kLosses(t)