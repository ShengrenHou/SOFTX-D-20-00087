import numpy as np
import matplotlib.pyplot as plt

from pycity_scheduling.classes import *
from pycity_scheduling.algorithms import *
import pycity_scheduling.util.debug as debug


# This is a fundamental tutorial on how to use the pycity_scheduling package.


# 1) Environment objects:


# (Almost) every object within pycity_scheduling requires an environment. The environment object holds general data,
# which is valid for all objects within pycity_scheduling, such as time data, weather data or market prices.
# Thus, all objects point to an environment. Therefore, the first step is usually to generate such an environment.

# Generate a timer object for the environment:
timer = Timer(step_size=3600, op_horizon=24, initial_date=(2015, 1, 1), initial_time=(0, 0, 0))


# Generate a weather object for the environment:
weather = Weather(timer=timer)

# Generate a price object for the environment:
price = Prices(timer=timer)

# Generate the environment object:
environment = Environment(timer=timer, weather=weather, prices=price)

# Now there is an environment with timer, weather and price data.
# We can use it to access different data of interest.

# For example, print the current weekday:
print('Weekday:')
print(environment.timer.weekday)

# For example, print the weather forecast for the outdoor temperature (only extract the first 10 timestep values):
print('\nOutdoor temperature forecast:')
print(environment.weather.getWeatherForecast(getTAmbient=True)[0][:10])

# For example, print the energy spot market day-ahead prices:
print('\nDay-ahead spot market prices on 2015/01/01:')
print(environment.prices.da_prices)

# 1) Buildings objects:

# After defining the environment, different building objects should be created. In pycity_scheduling, buildings
# represent the different customers of the local energy system / city district under investigation.
# In general, buildings should also be understood in a more abstract way. For instance, a building object must not
# necessarily represent a building structure, as it would be the case for a wind energy converter.

# Create a building object:
building = Building(environment=environment)

# This building is assumed to be equipped with a building energy system and one apartment (=single-family house).
# In general, every building object can, however, hold up to N different apartments (=multi-family house).
apartment = Apartment(environment=environment)
bes = BuildingEnergySystem(environment=environment)

building.addMultipleEntities([apartment, bes])


# Every apartment usually possesses both electrical and thermal loads:
# The electrical load is added to the apartment as follows:
load = FixedLoad(environment=environment, method=1, annual_demand=3000)

# Print and show the electrical power curve in Watt:
print('\nElectrical load in Watt:')
print(load.get_power(currentValues=False))
plt.plot(load.get_power(currentValues=False))
plt.xlabel('Time in hours')
plt.ylabel('Electrical power in Watt (fixed load)')
plt.title('Fixed load power curve')
plt.show()

# The thermal load is added to the apartment as follows:
space_heating = SpaceHeating(environment=environment, method=1, living_area=150, specific_demand=100)

# Print and show space heating power curve in Watt:
print('\nSpace heating power curve in Watt:')
print(space_heating.get_power(currentValues=False))

plt.plot(space_heating.get_power(currentValues=False))
plt.xlabel('Time in hours')
plt.ylabel('Thermal power in Watt (space heating)')
plt.title('Space heating power curve')
plt.show()


apartment.addMultipleEntities([load, space_heating])


# The BuildingEnergySystem (BES) class is a 'container' for all kind of building energy systems (i.e. electrical and/or
# thermal assets). For example, we can add an electro-thermal heating system (such as a heatpump plus thermal energy
# storage) and a photovoltaic unit to a building's BES as done below. In pycity_scheduling all BES devices automatically
# come with basic scheduling models, which includes the required pyomo optimization variables and constraints.
eh = HeatPump(environment=environment, P_Th_nom=16.0)
tes = ThermalEnergyStorage(environment=environment, E_Th_max=20.0, soc_init=0.5, loss_factor=0)
pv = Photovoltaic(environment=environment, method=0, peak_power=8.0)

bes.addMultipleDevices([eh, tes, pv])

# Verify if the assets were added successfully (method getHasDevice):
print('\nBES has heatpump? : ', bes.getHasDevices(all_devices=False, heatpump=True)[0])
print('BES has thermal energy storage? : ', bes.getHasDevices(all_devices=False, tes=True)[0])
print('BES has photovoltaic? : ', bes.getHasDevices(all_devices=False, pv=True)[0])


# In pycity_scheduling, a group of buildings form a CityDistrict object. The CityDistrict is the object to be "provided"
# to a power scheduling algorithm later on. In other word, it encapsulates all buildings together with their local
# assets and hence it includes all the optimization problem information and data.

# Create a city district object:
cd = CityDistrict(environment=environment)

# Add the building from above to the city district at a certain position/coordinate (x, y).
cd.addEntity(entity=building, position=[0, 0])

# Define and add three other buildings:
for i in range(3):
    heat_demand = SpaceHeating(environment=environment, method=1, living_area=150, specific_demand=100)

    el_load_demand = FixedLoad(environment=environment, method=1, annual_demand=3000)

    pv = Photovoltaic(environment=environment, method=0, peak_power=5.0)
    bl = Boiler(environment=environment, P_Th_nom=24.0)

    ap = Apartment(environment=environment)
    ap.addEntity(heat_demand)
    ap.addEntity(el_load_demand)

    bes = BuildingEnergySystem(environment=environment)
    bes.addDevice(pv)
    bes.addDevice(bl)

    bd = Building(environment=environment)
    bd.addEntity(entity=ap)
    bd.addEntity(entity=bes)

    cd.addEntity(entity=bd, position=[0, i])


# Print the city district information:
print('\nTotal number of buildings in city district:')
print(cd.get_nb_of_building_entities())
print("\nDetailed city district information:")
debug.print_district(cd, 3)


# The final step is to schedule the buildings/assets inside the city district subject to a certain objective, which can
# be, for example, peak-shaving. This corresponds to the aggregator's objective. The scheduling is then performed by
# "providing" the city district object to a certain power scheduling algorithm. Here, the central optimization algorithm
# is used.

# Set the objective and perform the power scheduling using the central optimization algorithm:
cd.setObjective("peak-shaving")
central_optimization(cd)

# The scheduling result obtained from the algorithm run can be (temporally) stored as follows:
cd.copy_schedule("my_central_scheduling")

# Print the scheduling result (city district power values for every time slot within the defined optimization horizon):
print("\nPower schedule of city district:")
print(list(cd.P_El_Schedule))
