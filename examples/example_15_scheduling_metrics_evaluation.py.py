import numpy as np

import pycity_scheduling.classes as classes
import pycity_scheduling.algorithms as algs
from pycity_scheduling.util import factory
from pycity_scheduling.util.metric import calculate_costs, peak_to_average_ratio, peak_reduction_ratio, \
                                          self_consumption, autarky, absolute_flexibility_gain

# Use a standard environment of 24 hours with hourly resolution (=60min=3600sec):
env = factory.generate_standard_environment(step_size=3600, op_horizon=24)
# Make it attractive for the consumers to shift demand into the second half of the scheduling period:
env.prices.tou_prices = np.array([20]*12 + [10]*12)

# City district / aggregator objective is set to peak-shaving:
cd = classes.CityDistrict(env, objective='peak-shaving')
# The sample building in this example comes with a constant electrical and space heating load of 10kW,
# thermal storage of capacity 20kWh and an electric heater of thermal nominal power 20kW:
bd = factory.generate_simple_building(env, fl=10, sh=10, tes=20, eh=20)

cd.addEntity(bd, (0, 0))

# Perform a 'pseudo' stand-alone scheduling, where each device is scheduled on its own (=no coordination):
algs.stand_alone_optimization(cd)
# Results are now in the _Ref schedules:
bd.copy_schedule("Ref")
cd.copy_schedule("Ref")
# Now perform a coordinated scheduling with aggregator and customer objectives:
algs.central_optimization(cd)

# Evaluate and print different metrics:
np.set_printoptions(formatter={'float': '{: >8.3f}'.format})
print('Comparing stand-alone with optimized case:')
print('Building P_El:')
print(bd.P_El_Ref_Schedule)
print(bd.P_El_Schedule)
print('Optimized costs:        {: >8.3f}'.format(calculate_costs(bd)))
bd.load_schedule("Ref")
print('Stand-alone costs:      {: >8.3f}'
      .format(calculate_costs(bd)))
bd.load_schedule("default")
print('Optimized PAR:          {: >8.3f}'.format(peak_to_average_ratio(bd)))
bd.load_schedule("Ref")
print('Stand-alone PAR:        {: >8.3f}'
      .format(peak_to_average_ratio(bd)))
bd.load_schedule("default")
print('PRR:                    {: >8.3f}'.format(peak_reduction_ratio(bd, "Ref")))
print('Self-consumption ratio: {: >8.3f}'.format(self_consumption(bd)))
print('Autarky ratio:          {: >8.3f}'.format(autarky(bd)))
print('Absolute flex. gain:    {: >8.3f}'.format(absolute_flexibility_gain(cd, "Ref")))

# Conclusion:
# In contrast to the unoptimized case (stand-alone) both the price as well as
# the peaks in the schedule are reduced in the optimized case. This is due to the
# price and peak-shaving objectives of the building and the city district.
