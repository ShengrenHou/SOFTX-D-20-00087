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
import pycity_base.classes.supply.compression_chiller as cc

from pycity_scheduling.classes.thermal_entity_cooling import ThermalEntityCooling
from pycity_scheduling.classes.electrical_entity import ElectricalEntity
from pycity_scheduling.util.generic_constraints import LowerActivationLimit


class Chiller(ThermalEntityCooling, ElectricalEntity, cc.CompressionChiller):
    """
    Extension of pyCity_base class CompressionChiller for scheduling purposes.

    Parameters
    ----------
    environment : Environment
        Common to all other objects. Includes time and weather instances.
    p_th_nom : float
        Nominal thermal power of the chiller in [kW].
    cop : numpy.ndarray or int or float, optional
        The chiller's coefficient of performance (without unit)
        If array, it must provide the coefficient of performance (cop) for
        each time step in the simulation horizon.
        If int or float, a constant cop over the whole horizon is assumed.
        If omitted, an air-water chiller is assumed and the cop is
        calculated based on the ambient air temperature, eta and t_flow.
    eta : int or float, optional
        The Carnot efficiency of the chiller.
        If cop is omitted, eta is used to calculate the cop based on T_sink and T_source
        according to: cop = eta * T_sink * (T_sink - T_source) with T_sink and T_source in Kelvin
    t_min : float, optional
        The chiller's minimum provided temperature in °C
    lower_activation_limit : float, optional (only adhered to in integer mode)
        Must be in [0, 1]. Lower activation limit of the chiller as a
        percentage of the rated power. When the chiller is in operation, its
        power must be zero or between the lower activation limit and its
        rated power.

        - `lower_activation_limit = 0`: Linear behavior
        - `lower_activation_limit = 1`: Two-point controlled
    t_flow: float, optional
        T_sink temperature delivered by CC in °C.
        Is used for cop calculation if cop is omitted.
        Note that t_flow >= t_min must hold.

    Notes
    -----
    - CHs offer sets of constraints for operation. In the `convex` mode the
      following constraints and bounds are generated by the CH:

    .. math::
        0 \\geq p_{th\\_cool} &\\geq& -p_{th\\_nom} \\\\
        cop * p_{el} &=& - p_{th\\_cool}

    - See also:
        - pycity_scheduling.util.generic_constraints.LowerActivationLimit:
          Generates additional constraints for the `lower_activation_limit` in `integer` mode.
    """

    def __init__(self, environment, p_th_nom, cop=None, eta=0.36, t_min=4.0, lower_activation_limit=0, t_flow=16.0):
        simu_horizon = environment.timer.simu_horizon

        (t_ambient,) = environment.weather.getWeatherForecast(getTAmbient=True)
        ts = environment.timer.time_in_year()
        t_ambient = t_ambient[ts:ts + simu_horizon]
        if cop is None:
            # ToDo: Variable cop calculation could be improved for chillers and it is recommended to use a fixed cop.
            with np.errstate(divide='ignore', invalid='ignore'):
                cop = -eta * np.true_divide((t_flow + 273.15), (t_flow - t_ambient))
                cop = np.nan_to_num(cop)
                cop[cop < 0] = 0
            print(list(cop))
        elif isinstance(cop, (int, float)):
            cop = np.full(simu_horizon, cop)
        elif not isinstance(cop, np.ndarray):
            raise TypeError(
                "Unknown type for `cop`: {}. Must be `numpy.ndarray`, `int` "
                "or `float`".format(type(cop))
            )
        super().__init__(environment, p_th_nom*1000.0, cop, t_min, lower_activation_limit)
        self._long_id = "CH_" + self._id_string
        self.cop = cop
        self.p_th_nom = p_th_nom

        self.activation_constr = LowerActivationLimit(self, "p_th_cool", lower_activation_limit, -p_th_nom)

    def populate_model(self, model, mode="convex"):
        """
        Add device block to pyomo ConcreteModel.

        Call parent's `populate_model` method and set thermal variables lower
        bounds to `-self.p_th_nom` and the upper bounds to zero. Also add
        constraint to bind electrical demand to thermal output.

        Parameters
        ----------
        model : pyomo.ConcreteModel
        mode : str, optional
            Specifies which set of constraints to use

            - `convex`  : Use linear constraints
            - `integer`  : Use integer variables representing discrete control decisions
        """
        super().populate_model(model, mode)
        m = self.model

        if mode == "convex" or "integer":
            m.p_th_cool_vars.setlb(-self.p_th_nom)
            m.p_th_cool_vars.setub(0.0)

            m.cop = pyomo.Param(m.t, mutable=True)

            def p_coupl_rule(model, t):
                return model.p_th_cool_vars[t] + model.cop[t] * model.p_el_vars[t] == 0
            m.p_coupl_constr = pyomo.Constraint(m.t, rule=p_coupl_rule)

            self.activation_constr.apply(m, mode)
        else:
            raise ValueError(
                "Mode %s is not implemented by class Chiller." % str(mode)
            )
        return

    def update_model(self, mode=""):
        m = self.model
        cop = self.cop[self.op_slice]
        for t in self.op_time_vec:
            m.cop[t] = cop[t]
        return
