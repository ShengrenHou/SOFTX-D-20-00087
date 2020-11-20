"""
The pycity_scheduling framework


Copyright (C) 2020
Institute for Automation of Complex Power Systems (ACS);
E.ON Energy Research Center;
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
import pycity_base.classes.supply.battery as bat

from pycity_scheduling.classes.electrical_entity import ElectricalEntity


class Battery(ElectricalEntity, bat.Battery):
    """
    Extension of pyCity_base class Battery for scheduling purposes.

    Initialize Battery.

    Parameters
    ----------
    environment : Environment
        Common Environment instance.
    e_el_max : float
        Electric capacity of the battery [kWh].
    p_el_max_charge : float
        Maximum charging power [kW].
    p_el_max_discharge : float, optional
        Maximum discharging power [kW]. Defaults to zero.
    soc_init : float, optional
        Initial state of charge. Defaults to 50%.
    eta : float, optional
        Charging and discharging efficiency. Must be in (0,1]. Defaults
        to one.
    storage_end_equality : bool, optional
        `True` if the soc at the end of the scheduling has to be equal to
        the initial soc.
        `False` if it has to be greater or equal than the initial soc.
        Defaults to `False`.

    Notes
    -----
    - Batteries offer sets of constraints for operation. In the `convex` mode
      the following constraints and bounds are generated by the battery:

    .. math::

        p_{el} &=& p_{el\\_demand} - p_{el\\_supply} \\\\
        p_{el\\_max\\_discharge} &\\geq& p_{el\\_supply} \\geq 0 \\\\
        p_{el\\_max\\_charge} &\\geq& p_{el\\_demand} \\geq 0 \\\\
        e_{el\\_max} &\\geq& e_{el} \\geq 0 \\\\
        e_{el} &=& e_{el\\_previous} + (\\eta * p_{el\\_demand}
        - (1 / \\eta) * p_{el\\_supply}) * \\Delta t \\\\
        \\text{with} \\quad e_{el\\_previous} &=& \\
        \\begin{bmatrix} e_{el\\_ini} & e_{el\\_0} & \\cdots & e_{el\\_n-1}\\end{bmatrix}

    - Additional constraints generated by the parameters are:

    .. math::

        e_{el\\_t\\_last} &=& soc\\_init * e_{el\\_max}, & \\quad \\text{if storage_end_equality} \\\\
        e_{el\\_t\\_last} &\\geq& soc\\_init * e_{el\\_max}, & \\quad \\text{else}

    - In `integer` mode the following constraints are added additionally:

    .. math::

        p_{el\\_demand} &\\leq& p_{state} * p_{el\\_max\\_discharge} \\\\
        p_{el\\_supply} &\\leq& (1-p_{state}) * p_{el\\_max\\_charge}
    """

    def __init__(self, environment, e_el_max, p_el_max_charge, p_el_max_discharge=None, soc_init=0.5, eta=1,
                 storage_end_equality=False):

        capacity = e_el_max * 3600 * 1000
        soc_abs = soc_init * capacity  # absolute SOC
        super().__init__(environment, soc_abs, capacity, 0.0, eta, eta)
        self._long_id = "BAT_" + self._id_string

        self.objective = 'peak-shaving'
        self.e_el_max = e_el_max
        self.soc_init = soc_init  # relative SOC
        self.p_el_max_charge = p_el_max_charge
        self.p_el_max_discharge = p_el_max_discharge if p_el_max_discharge is not None else p_el_max_charge
        self.eta = eta
        self.storage_end_equality = storage_end_equality

        self.new_var("p_el_demand")
        self.new_var("p_el_supply")
        self.new_var("p_state", dtype=np.bool, func=lambda model:
                     self.schedule["p_el_demand"][self.op_slice] >
                     self.schedule["p_el_supply"][self.op_slice]
                     )
        self.new_var("e_el")

    def populate_model(self, model, mode="convex"):
        """
        Add device block of variables and constraints to pyomo ConcreteModel.

        Call parent's `populate_model` method and set variables lower bounds to
        `None`. Then add variables for demand, supply and the state of charge,
        with their corresponding upper bounds (`self.p_el_max_charge`,
        `self.p_el_max_discharge`, `self.e_el_max`). Finally add continuity
        constraints to the block.

        Parameters
        ----------
        model : pyomo.ConcreteModel
        mode : str, optional
            Specifies which set of constraints to use.

            - `convex`  : Use linear constraints
            - `integer`  : Use integer variables representing discrete control decisions
        """
        super().populate_model(model, mode)
        m = self.model
        if mode in ["convex", "integer"]:
            # additional variables for battery
            m.p_el_vars.setlb(None)
            m.p_el_demand_vars = pyomo.Var(m.t, domain=pyomo.Reals,
                                           bounds=(0.0, np.inf if mode == "integer" else self.p_el_max_charge),
                                           initialize=0)
            m.p_el_supply_vars = pyomo.Var(m.t, domain=pyomo.Reals,
                                           bounds=(0.0, np.inf if mode == "integer" else self.p_el_max_discharge),
                                           initialize=0)
            m.e_el_vars = pyomo.Var(m.t, domain=pyomo.Reals, bounds=(0, self.e_el_max), initialize=0)

            def p_rule(model, t):
                return model.p_el_vars[t] == model.p_el_demand_vars[t] - model.p_el_supply_vars[t]
            m.p_constr = pyomo.Constraint(m.t, rule=p_rule)
            m.e_el_init = pyomo.Param(default=self.soc_init * self.e_el_max, mutable=True)

            def e_rule(model, t):
                delta = (
                        (self.eta_charge * model.p_el_demand_vars[t]
                         - (1.0 / self.eta_discharge) * model.p_el_supply_vars[t])
                        * self.time_slot
                )
                e_el_last = model.e_el_vars[t - 1] if t >= 1 else model.e_el_init
                return model.e_el_vars[t] == e_el_last + delta
            m.e_constr = pyomo.Constraint(m.t, rule=e_rule)

            def e_end_rule(model):
                if self.storage_end_equality:
                    return model.e_el_vars[self.op_horizon-1] == self.e_el_max * self.soc_init
                else:
                    return model.e_el_vars[self.op_horizon-1] >= self.e_el_max * self.soc_init
            m.e_end_constr = pyomo.Constraint(rule=e_end_rule)

            if mode == "integer":
                m.p_state_vars = pyomo.Var(m.t, domain=pyomo.Binary)

                def c_rule(model, t):
                    return model.p_el_demand_vars[t] <= model.p_state_vars[t] * self.p_el_max_charge
                m.p_charge_integer_constr = pyomo.Constraint(m.t, rule=c_rule)

                def d_rule(model, t):
                    return model.p_el_supply_vars[t] <= (1 - model.p_state_vars[t]) * self.p_el_max_discharge
                m.p_discharge_integer_constr = pyomo.Constraint(m.t, rule=d_rule)

        else:
            raise ValueError(
                "Mode %s is not implemented by class Battery." % str(mode)
            )
        return

    def update_model(self, mode=""):
        m = self.model
        timestep = self.timestep

        if timestep == 0:
            m.e_el_init = self.soc_init * self.e_el_max
        else:
            m.e_el_init = self.e_el_schedule[timestep - 1]
        return
