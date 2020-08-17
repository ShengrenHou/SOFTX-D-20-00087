import numpy as np
import pyomo.environ as pyomo

import pycity_base.classes.demand.electrical_demand as ed

from pycity_scheduling.classes.electrical_entity import ElectricalEntity
from pycity_scheduling import util


class FixedLoad(ElectricalEntity, ed.ElectricalDemand):
    """
    Extension of pyCity_base class ElectricalDemand for scheduling purposes.

    As for all uncontrollable loads, the `P_El_Schedule` contains the forecast
    of the load.
    """

    def __init__(self, environment, method=0, demand=0, annual_demand=0, profile_type="H0", single_family_house=True,
                 total_nb_occupants=0, randomize_appliances=True, light_configuration=0, occupancy=None,
                 do_normalization=False, method_3_type=None, method_4_type=None, prev_heat_dev=False, app_filename=None,
                 light_filename=None, season_light_mod=False, light_mod_fac=0.25):
        """
        Initialize FixedLoad.

        Parameters
        ----------
        environment : Environment
            Common Environment instance.
        method : {0, 1, 2}, optional
            - 0 : provide load curve directly
            - 1 : standard load profile (for households)
            - 2 : stochastic electrical load model
            - 3 : annual profile based on measured weekly profiles (non-residential)
            - 4 : annual profile based on measured annual profiles (non-residential)
        demand : numpy.ndarray of float, optional
            Demand for all investigated time steps in [kW].
            requires `method=0`
        annual_demand : float, optional
            Required for SLP and recommended for method 2.
            Annual electrical demand in [kWh].
            If method 2 is chosen but no value is given, a standard value for
            Germany (http://www.die-stromsparinitiative.de/fileadmin/bilder/
            Stromspiegel/Brosch%C3%BCre/Stromspiegel2014web_final.pdf) is used.
        profile_type : str, optional
            - H0 : Household
            - L0 : Farms
            - L1 : Farms with breeding / cattle
            - L2 : Farms without cattle
            - G0 : Business (general)
            - G1 : Business (workingdays 8:00 AM - 6:00 PM)
            - G2 : Business with high loads in the evening
            - G3 : Business (24 hours)
            - G4 : Shops / Barbers
            - G5 : Bakery
            - G6 : Weekend operation
        total_nb_occupants : int, optional
            Number of people living in the household.
            requires `method=2`
        randomize_appliances : bool, optional
            - True : distribute installed appliances randomly
            - False : use the standard distribution
            requires `method=2`
        light_configuration : {0..99}, optional
            There are 100 light bulb configurations predefined for the
            stochastic model.
            requires `method=2`
        occupancy : int, optional
            Occupancy given at 10-minute intervals for a full year.
            requires `method=2`
        do_normalization : bool, optional
            Defines, if stochastic profile (method=2) should be
            normalized to given annual_demand value (default: False).
            If set to False, annual el. demand depends on stochastic el. load
            profile generation. If set to True, does normalization with
            annual_demand
        method_3_type : str, optional
            Defines type of profile for method=3 (default: None)
            Options:
            - 'food_pro': Food production
            - 'metal': Metal company
            - 'rest': Restaurant (with large cooling load)
            - 'sports': Sports hall
            - 'repair': Repair / metal shop
        method_4_type : str, optional
            Defines type of profile for method=4 (default: None)
            - 'metal_1' : Metal company with smooth profile
            - 'metal_2' : Metal company with fluctuation in profile
            - 'warehouse' : Warehouse
        prev_heat_dev : bool, optional
            Defines, if heating devices should be prevented within chosen
            appliances (default: False). If set to True, DESWH, E-INST,
            Electric shower, Storage heaters and Other electric space heating
            are set to zero. Only relevant for method == 2
        app_filename : str, optional
            Path to Appliances file
            (default: None). If set to None, uses default file Appliances.csv
            in \inputs\stochastic_electrical_load\.
            Only relevant, if method == 2.
        light_filename : str, optional
            Path to Lighting configuration file
            (default: None). If set to None, uses default file Appliances.csv
            in \inputs\stochastic_electrical_load\.
            Only relevant, if method == 2.
        season_light_mod : bool, optional
            Defines, if cosine-wave should be used to strengthen seasonal
            influence on lighting (default: False). If True, enlarges
            lighting power demand in winter month and reduces lighting power
            demand in summer month
        light_mod_fac : float, optional
            Define factor, related to maximal lighting power, which is used
            to implement seasonal influence (default: 0.25). Only relevant,
            if season_light_mod == True

        Notes
        -----
        The standard load profile can be downloaded here:
        http://www.ewe-netz.de/strom/1988.php

        Average German electricity consumption per household can be found here:
        http://www.die-stromsparinitiative.de/fileadmin/bilder/Stromspiegel/
        Brosch%C3%BCre/Stromspiegel2014web_final.pdf
        """
        super().__init__(environment, method, demand*1000, annual_demand, profile_type, single_family_house,
                         total_nb_occupants, randomize_appliances, light_configuration, occupancy, do_normalization,
                         method_3_type, method_4_type, prev_heat_dev, app_filename, light_filename, season_light_mod,
                         light_mod_fac)
        self._long_ID = "FL_" + self._ID_string

        ts = self.timer.time_in_year(from_init=True)
        p = self.loadcurve[ts:ts+self.simu_horizon] / 1000
        self.P_El_Schedule = p

    def update_model(self, mode=""):
        m = self.model
        timestep = self.timestep

        for t in self.op_time_vec:
            m.P_El_vars[t].setlb(self.P_El_Schedule[timestep + t])
            m.P_El_vars[t].setub(self.P_El_Schedule[timestep + t])

    def new_schedule(self, schedule):
        super().new_schedule(schedule)
        self.copy_schedule(schedule, "default", "P_El")

    def update_schedule(self, mode=""):
        pass

    def reset(self, name=None):
        pass
