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
        yield from self.boiler
        yield from self.chp
        yield from self.electrical_heater
        yield from self.heatpump
        yield from self.tes
        yield from self.battery
        yield from self.pv
