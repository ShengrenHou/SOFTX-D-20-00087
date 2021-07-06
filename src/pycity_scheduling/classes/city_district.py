"""
The pycity_scheduling framework


Copyright (C) 2020,
Institute for Automation of Complex Power Systems (ACS),
E.ON Energy Research Center (E.ON ERC),
RWTH Aachen University

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


import numpy as np
import pyomo.environ as pyomo
import pycity_base.classes.city_district as cd

from pycity_scheduling.classes.electrical_entity import ElectricalEntity


class CityDistrict(ElectricalEntity, cd.CityDistrict):
    """
    Extension of pyCity_base class CityDistrict for scheduling purposes. Also represents the district operator.

    Parameters
    ----------
    environment : Environment
    objective : str, optional
        Objective for the district operator. Default is 'price'.

        - 'price' : Optimize for the minimum total cost given by `prices.da_prices`.
        - 'peak-shaving' : Try to 'flatten' the schedule as much as possible.
        - 'co2' : Optimize for the minimum total co2 emissions given by `prices.co2_prices`.
        - 'valley-filling' : Try to fill the 'valleys' given by a reference power profile.
        - 'max-consumption' : Try to minimize the maximum power subscription.
        - 'self-consumption' : Try to maximize the self-consumption of the local power generation.
        - 'flexibility-quantification' : To be used to quantify the flexibility potential of the city district only.
        - 'none' : No objective.
    valley_profile : numpy.ndarray, optional
        Profile to be filled by applying the valley filling objective.

    Notes
    -----
    - The constraints generated by a CD are the same as the ones created by an EntityContainer.
    """

    def __init__(self, environment, objective='price', valley_profile=None):
        super().__init__(environment)
        self._long_id = "CD_" + self._id_string
        self.objective = objective
        self.valley_profile = valley_profile

    def populate_model(self, model, mode="convex"):
        """
        Add city district block to pyomo ConcreteModel.

        Call parent's `populate_model` methods and set variables lower
        bounds to `None`.

        Parameters
        ----------
        model : pyomo.ConcreteModel
        mode : str, optional
            Specifies which set of constraints to use.

            - `convex`  : Use linear constraints
            - `integer`  : Use same constraints as convex mode
        """

        # constraints imprementation to go

        super().populate_model(model, mode)
        m = self.model

        if mode in ["convex", "integer"]:
            m.p_el_vars.setlb(None)
        else:
            raise ValueError(
                "Mode %s is not implemented by city district." % str(mode)
            )
        return

    def get_objective(self, coeff=1):
        if self.objective == 'valley-filling':
            e = coeff * pyomo.sum_product(self.model.p_el_vars, self.model.p_el_vars)
            valley = self.valley_profile[self.op_slice]
            e += 2 * coeff * pyomo.sum_product(valley, self.model.p_el_vars)
            return e
        elif self.objective == 'price':
            prices = self.environment.prices.da_prices[self.op_slice]
            s = sum(abs(prices))
            if s > 0:
                prices = prices * self.op_horizon / s
                return pyomo.sum_product(prices, self.model.p_el_vars)
            else:
                return 0
        else:
            return super().get_objective(coeff)

    def get_lower_entities(self):
        for node in self.nodes.values():
            yield node['entity']

    def account_imbalance(self):
        """
        Changes the current schedule to account imbalances.

        The imbalances are determined from the current schedules of the contained
        entities.
        """

        total = np.zeros_like(self.schedule["p_el"])
        for e in self.get_lower_entities():
            total += e.schedule["p_el"]

        self.schedule["p_el"] = total
        return
