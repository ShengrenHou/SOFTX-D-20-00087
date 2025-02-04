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
import pycity_base.classes.supply.building_energy_system as bes

from pycity_scheduling.classes.entity_container import EntityContainer
from pycity_scheduling.classes.thermal_entity_cooling import ThermalEntityCooling
from pycity_scheduling.classes.thermal_entity_heating import ThermalEntityHeating


class BuildingEnergySystem(EntityContainer, bes.BES):
    """
    Extension of pyCity_base class BES for scheduling purposes.

    Parameters
    ----------
    environment : Environment

    Notes
    -----
    - The constraints generated by a BES are the same as the ones created by an EntityContainer.
    """

    def __init__(self, environment):
        super().__init__(environment)
        self._long_id = "BES_" + self._id_string

    def get_lower_entities(self):
        yield from self.boilers
        yield from self.compression_chillers
        yield from self.chp_units
        yield from self.electrical_heaters
        yield from self.heatpumps
        yield from self.ths_units
        yield from self.tcs_units
        yield from self.battery_units
        yield from self.pv_units

    @property
    def ths_units(self):
        """Provides all THS units."""
        ths_units = []
        for tes in self.tes_units:
            if isinstance(tes, ThermalEntityHeating):
                ths_units.append(tes)
        return ths_units

    @property
    def tcs_units(self):
        """Provides all TCS units."""
        tcs_units = []
        for tes in self.tes_units:
            if isinstance(tes, ThermalEntityCooling):
                tcs_units.append(tes)
        return tcs_units

    def getHasDevices(self,
                      all_devices=True,
                      battery=False,
                      boiler=False,
                      chp=False,
                      chiller=False,
                      electrical_heater=False,
                      heatpump=False,
                      inverter_acdc=False,
                      inverter_dcac=False,
                      pv=False,
                      ths=False,
                      tcs=False):
        """
        Get information if certain devices are installed devices.
        The result is in alphabetical order, starting with "battery"

        Parameters
        ----------
        all_devices : boolean, optional
            If true: Return all installed devices
            If false: Only return the specified devices
        battery : boolean, optional
            Return information on the battery
        boiler : boolean, optional
            Return information on the boiler
        chp : boolean, optional
            Return information on the chp unit
        chiller : boolean, optional
            Return information on the chiller unit
        electrical_heater : boolean, optional
            Return information on the electrical heater
        heatpump : boolean, optional
            Return information on the heat pump
        inverter_acdc : boolean, optional
            Return information on the AC-DC inverter
        inverter_dcac : boolean, optional
            Return information on the DC-AC inverter
        pv : boolean, optional
            Return information on the PV modules
        ths : boolean, optional
            Return information on the thermal heating storage
        tcs : boolean, optional
            Return information on the thermal cooling storage
        """
        result = super().getHasDevices(all_devices=all_devices,
                                       battery=battery,
                                       boiler=boiler,
                                       chp=chp,
                                       compression_chiller=chiller,
                                       electrical_heater=electrical_heater,
                                       heatpump=heatpump,
                                       inverter_acdc=inverter_acdc,
                                       inverter_dcac=inverter_dcac,
                                       pv=pv,
                                       tes=False)
        if all_devices:
            result = list(result)
            result[-1] = (len(self.ths_units) > 0)
            result.append((len(self.tcs_units) > 0))
            result = tuple(result)
        else:
            if ths:
                result += ((len(self.ths_units) > 0),)
            if tcs:
                result += ((len(self.tcs_units) > 0),)
        return result
