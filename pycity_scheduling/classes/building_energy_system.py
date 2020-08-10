import numpy as np
import pyomo.environ as pyomo
import pycity_base.classes.supply.building_energy_system as bes

from .entity_container import EntityContainer


class BuildingEnergySystem(EntityContainer, bes.BES):
    """
    Extension of pyCity_base class BES for scheduling purposes.
    """

    def __init__(self, environment):
        super().__init__(environment)
        self._long_ID = "BES_" + self._ID_string

    def get_lower_entities(self):
        yield from self.boilers
        yield from self.chp_units
        yield from self.electrical_heaters
        yield from self.heatpumps
        yield from self.tes_units
        yield from self.battery_units
        yield from self.pv_units
