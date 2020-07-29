import numpy as np

import pycity_scheduling.classes as classes
from pycity_scheduling.algorithms import central_optimization
from pycity_scheduling.util import factory
from pycity_scheduling.util.metric import calculate_costs

# Use a simple environment of 6 hours with quarter-hourly resolution (=15min=900sec):
env = factory.generate_standard_environment(step_size=900, op_horizon=6)

# Make it attractive to shift demand into the first half of the scheduling period (compare metric_example_01.py):
env.prices.tou_prices = np.array([5]*3 + [10]*3)

district = classes.CityDistrict(env)
# The sample building in this example comes with a constant space heating load of 10kW, thermal storage of capacity
# 20 kWh and an electric heater of thermal nominal power 20 kW:
bd = factory.generate_simple_building(env, sh=10, tes=20, eh=20)

district.addEntity(bd, (0, 0))

# Perform the Scheduling without RO:
central_optimization(district)
bd.save_ref_schedule()

# Protect 6 time steps and assume a maximum deviation of 50% in each time step
# Such a high deviation is unrealistic but makes it a good example.
central_optimization(district, robustness=(6, 0.5))

# Print schedules/results:
np.set_printoptions(formatter={'float': '{: >8.3f}'.format})
print('Building P_El:')
print(bd.P_El_Ref_Schedule)
print(bd.P_El_Schedule)
print('ThermalEnergyStorage E_Th:')
print(bd.bes.tes.E_Th_Ref_Schedule)
print(bd.bes.tes.E_Th_Schedule)
print('ThermalEnergyStorage Limits:')
print(list(bd.model.lower_robustness_bounds[:].value))
print(list(bd.model.upper_robustness_bounds[:].value))
print('ElectricHeater P_Th:')
print(bd.bes.electricalHeater.P_Th_Ref_Schedule)
print(bd.bes.electricalHeater.P_Th_Schedule)
print('SpaceHeating P_Th:')
print(bd.apartments[0].Th_Demand_list[0].P_Th_Ref_Schedule)
print(bd.apartments[0].Th_Demand_list[0].P_Th_Schedule)
print('Costs:')
bd.load_schedule("Ref")
print('{:.2f}'.format(calculate_costs(bd)))
bd.load_schedule("default")
print('{:.2f}'.format(calculate_costs(bd)))
