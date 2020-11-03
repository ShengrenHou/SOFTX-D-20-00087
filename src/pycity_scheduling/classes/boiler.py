"""
The pycity_scheduling framework


@institution:
Institute for Automation of Complex Power Systems (ACS)
E.ON Energy Research Center
RWTH Aachen University

@author:
Sebastian Schwarz, M.Sc.
Sebastian Alexander Uerlich, B.Sc.
Univ.-Prof. Antonello Monti, Ph.D.
"""


import numpy as np
import pyomo.environ as pyomo
import pycity_base.classes.supply.boiler as bl

from pycity_scheduling.classes.thermal_entity_heating import ThermalEntityHeating
from pycity_scheduling.util.generic_constraints import LowerActivationLimit


class Boiler(ThermalEntityHeating, bl.Boiler):
    """
    Extension of pyCity_base class Boiler for scheduling purposes.

    Parameters
    ----------
    environment : pycity_scheduling.classes.Environment
        Common to all other objects. Includes time and weather instances.
    p_th_nom : float
        Nominal heat output in [kW].
    eta : float, optional
        Efficiency of the gas boiler (without unit).
    lower_activation_limit : float, optional (only adhered to in integer mode)
        Must be in [0, 1]. Lower activation limit of the gas boiler as a
        percentage of the rated power. When the gas boiler is in operation, its
        power must be zero or between the lower activation limit and its
        rated power.

        - `lower_activation_limit = 0`: Linear behavior
        - `lower_activation_limit = 1`: Two-point controlled

    Notes
    -----
    Gas boilers offer sets of constraints for operation. In the `convex`
    mode the following constraints and bounds are generated by the boiler:

    .. math::
        0 \\geq p_{th\\_heat} \\geq -p_{th\\_nom}

    See Also
    --------
    pycity_scheduling.util.generic_constraints.LowerActivationLimit:
    Generates additional constraints for the `lower_activation_limit` in `integer` mode.
    """

    def __init__(self, environment, p_th_nom, eta=1, lower_activation_limit=0):
        # Flow temperature of 55 C
        super().__init__(environment, 1000*p_th_nom, eta, 55, lower_activation_limit)
        self._long_ID = "BL_" + self._ID_string
        self.p_th_nom = p_th_nom

        self.activation_constr = LowerActivationLimit(self, "p_th_heat", lower_activation_limit, -p_th_nom)

    def populate_model(self, model, mode="convex"):
        """Add device block to pyomo ConcreteModel

        Call parent's `populate_model` method and set variables upper bounds
        to `self.p_th_nom`.

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

        if mode == "convex" or "integer":
            m.p_th_heat_vars.setlb(-self.p_th_nom)
            m.p_th_heat_vars.setub(0)

            self.activation_constr.apply(m, mode)
        else:
            raise ValueError(
                "Mode %s is not implemented by class Boiler." % str(mode)
            )
        return

    def get_objective(self, coeff=1):
        """Objective function for entity level scheduling.

        Return the objective function of the boiler weighted with coeff.
        Sum of `p_th_heat`.

        Parameters
        ----------
        coeff : float, optional
            Coefficient for the objective function.

        Returns
        -------
        ExpressionBase :
            Objective function.
        """
        return coeff * pyomo.sum_product(self.model.p_th_heat_vars)
