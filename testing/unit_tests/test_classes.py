import datetime
import unittest

import numpy as np
from shapely.geometry import Point
import gurobipy as gp

from pycity_scheduling.classes import *
from pycity_scheduling.util.metric import *


gp.setParam('outputflag', 0)


class TestModule(unittest.TestCase):
    def test_filter_entities(self):
        e = get_env(4, 8)
        bd = Building(e)
        bes = BuildingEnergySystem(e)
        pv = Photovoltaic(e, 0, 0)
        bes.addDevice(pv)
        bd.addEntity(bes)

        def do_test(gen):
            entities = list(gen)
            self.assertEqual(1, len(entities))
            self.assertIn(pv, entities)

        do_test(filter_entities(bd.get_entities(), 'PV'))
        do_test(filter_entities(bd, 'res_devices'))
        do_test(filter_entities(bd, [Photovoltaic]))
        do_test(filter_entities(bd, ['PV']))
        do_test(filter_entities(bd, {'PV': Photovoltaic}))
        with self.assertRaises(ValueError):
            next(filter_entities(bd, 'PPV'))
        with self.assertRaises(ValueError):
            next(filter_entities(bd, [int]))
        with self.assertRaises(ValueError):
            next(filter_entities(bd, None))


class TestBattery(unittest.TestCase):
    def setUp(self):
        e = get_env(3)
        self.bat = Battery(e, 10, 20, soc_init=0.875, eta=0.5)

    def test_populate_model(self):
        model = gp.Model('BatModel')
        self.bat.populate_model(model)
        model.addConstr(self.bat.E_El_vars[2] == 10)
        model.addConstr(self.bat.E_El_vars[0] == 5)
        obj = gp.QuadExpr()
        obj.addTerms(
            [1] * 3,
            self.bat.P_El_Demand_vars,
            self.bat.P_El_Demand_vars
        )
        model.setObjective(obj)
        model.optimize()

        var_list = [var.varname for var in model.getVars()]
        self.assertEqual(12, len(var_list))
        var_sum = sum(map(lambda v: v.x, self.bat.P_El_vars[1:]))
        self.assertAlmostEqual(40, var_sum, places=5)
        var_sum = sum(map(
            lambda v: v.x,
            self.bat.P_El_Supply_vars[1:] + self.bat.P_El_Demand_vars[1:]
        ))
        self.assertAlmostEqual(40, var_sum, places=5)

    def test_update_model(self):
        model = gp.Model('BatModel')
        demand_var = model.addVar()
        self.bat.P_El_Demand_vars.append(demand_var)
        self.bat.P_El_Supply_vars.append(model.addVar())
        self.bat.E_El_vars.append(model.addVar())
        self.bat.update_model(model)
        model.addConstr(self.bat.E_El_vars[0] == 10)
        obj = demand_var * demand_var
        model.setObjective(obj)
        model.optimize()

        self.assertAlmostEqual(10, demand_var.x, places=5)

    def test_update_schedule(self):
        m1, var_list = get_model(3)
        m1.optimize()
        self.bat.P_El_vars = var_list
        m2, var_list = get_model(3, 2)
        a = np.arange(3)
        self.bat.P_El_Demand_vars = [m2.addVar(lb=3, ub=3) for i in range(3)]
        self.bat.P_El_Supply_vars = [m2.addVar(lb=0, ub=0) for i in range(3)]
        m2.optimize()
        self.bat.E_El_vars = var_list

        self.bat.update_schedule()
        assert_equal_array(self.bat.P_El_Schedule, a)
        assert_equal_array(self.bat.E_El_Schedule, a * 2)

    def test_calculate_co2(self):
        self.bat.P_El_Schedule = np.array([10]*3)
        self.assertEqual(0, calculate_co2(self.bat))

    def test_get_objective(self):
        model = gp.Model('BatModel')
        self.bat.populate_model(model)
        obj = self.bat.get_objective(2)
        self.assertEqual(3, obj.size())
        self.assertEqual(0, obj.getLinExpr().size())
        self.assertEqual(0, obj.getLinExpr().getConstant())
        coeffs = np.zeros(3)
        for i in range(3):
            var = obj.getVar1(i)
            self.assertIs(var, obj.getVar2(i))
            t = [t for t in range(3) if self.bat.P_El_vars[t] is var][0]
            coeffs[t] += obj.getCoeff(i)
        assert_equal_array(coeffs, np.full(3, 2))


class TestBoiler(unittest.TestCase):
    def setUp(self):
        e = get_env(4, 8)
        self.bl = Boiler(e, 10, 0.4)

    def test_calculate_co2(self):
        self.bl.P_Th_Schedule = - np.array([10] * 8)
        self.bl.P_Th_Ref_Schedule = - np.array([4] * 8)
        co2_em = np.array([1111]*8)

        co2 = calculate_co2(self.bl, co2_emissions=co2_em)
        self.assertEqual(23750, co2)
        co2 = calculate_co2(self.bl, timestep=4, co2_emissions=co2_em)
        self.assertEqual(11875, co2)
        self.bl.load_schedule("Ref")
        co2 = calculate_co2(self.bl, co2_emissions=co2_em)
        self.assertEqual(9500, co2)

    def test_lower_activation(self):
        e = get_env(4, 8)
        bl = Boiler(e, 10, lower_activation_limit=0.5)
        m = gp.Model('BLModel')
        bl.populate_model(m, "integer")
        bl.update_model(m, "integer")
        m.optimize()


class TestBuilding(unittest.TestCase):
    def setUp(self):
        e = get_env(4, 8)
        self.bd = Building(e)

    def test_get_objective(self):
        m, var_list = get_model(4)
        self.bd.P_El_vars = var_list
        m.optimize()

        self.bd.environment.prices.tou_prices = np.array([1]*2 + [4]*6)
        self.assertAlmostEqual(8.4, self.bd.get_objective().getValue())
        self.bd.environment.prices.co2_prices = np.array([4]*2 + [1]*6)
        self.bd.objective = 'co2'
        self.assertAlmostEqual(3.6, self.bd.get_objective().getValue())
        self.bd.objective = 'peak-shaving'
        self.assertAlmostEqual(14, self.bd.get_objective().getValue())

    def test_calculate_co2(self):
        bes = BuildingEnergySystem(self.bd.environment)
        pv = Photovoltaic(self.bd.environment, 0, 0)
        bes.addDevice(pv)
        self.bd.addEntity(bes)
        self.bd.P_El_Schedule = np.array([-5] * 2 + [5] * 4 + [-5] * 2)
        self.bd.P_El_Ref_Schedule = np.array([-2] * 2 + [2] * 4 + [-2] * 2)
        pv.P_El_Schedule = - np.array([10]*8)
        pv.P_El_Ref_Schedule = - np.array([4]*8)
        co2_em = np.array([100]*4 + [400]*4)

        co2 = calculate_co2(self.bd, co2_emissions=co2_em)
        self.assertEqual(2750, co2)
        co2 = calculate_co2(self.bd, timestep=4, co2_emissions=co2_em)
        self.assertEqual(1000, co2)
        self.bd.load_schedule("Ref")
        co2 = calculate_co2(self.bd, co2_emissions=co2_em)
        self.assertEqual(1100, co2)

    def test_get_objective(self):
        model = gp.Model('BuildingModel')
        env = self.bd.environment
        env.prices.tou_prices[:4] = [1, 2, 3, 4]
        env.prices.co2_prices[:4] = [5, 4, 3, 2]
        bes = BuildingEnergySystem(env)
        self.bd.addEntity(bes)
        self.bd.populate_model(model)
        obj = self.bd.get_objective(2)
        self.assertEqual(4, obj.size())
        self.assertEqual(0, obj.getConstant())
        coeffs = np.zeros(4)
        for i in range(4):
            var = obj.getVar(i)
            t = [t for t in range(4) if self.bd.P_El_vars[t] is var][0]
            coeffs[t] += obj.getCoeff(i)
        assert_equal_array(coeffs, env.prices.tou_prices[:4] * 2 / sum(range(5)) * 4)
        bd2 = Building(env, 'co2')
        bd2.addEntity(bes)
        bd2.populate_model(model)
        obj = bd2.get_objective(2)
        self.assertEqual(4, obj.size())
        self.assertEqual(0, obj.getConstant())
        coeffs = np.zeros(4)
        for i in range(4):
            var = obj.getVar(i)
            t = [t for t in range(4) if bd2.P_El_vars[t] is var][0]
            coeffs[t] += obj.getCoeff(i)
        assert_equal_array(coeffs, env.prices.co2_prices[:4] * 2 / sum(range(2, 6, 1)) * 4)
        bd3 = Building(env, 'peak-shaving')
        bd3.addEntity(bes)
        bd3.populate_model(model)
        obj = bd3.get_objective(2)
        self.assertEqual(4, obj.size())
        self.assertEqual(0, obj.getLinExpr().size())
        self.assertEqual(0, obj.getLinExpr().getConstant())
        coeffs = np.zeros(4)
        for i in range(4):
            var = obj.getVar1(i)
            self.assertIs(var, obj.getVar2(i))
            t = [t for t in range(4) if bd3.P_El_vars[t] is var][0]
            coeffs[t] += obj.getCoeff(i)
        assert_equal_array(coeffs, np.full(4, 2))
        bd4 = Building(env, None)
        obj = bd4.get_objective(2)
        self.assertEqual(0, obj.size())
        self.assertEqual(0, obj.getConstant())
        bd4.addEntity(bes)
        bd4 = Building(env, "invalid")
        self.assertRaisesRegex(ValueError, ".*Building.*", bd4.get_objective)



class TestCurtailableLoad(unittest.TestCase):
    combinations = [(4, 1), (3, 1), (2, 1), (1, 1),
                    (1, 3), (1, 4), (2, 2), (2, 3),
                    (0, 1), (0, 2), (0, 3), (0, 4)]
    horizon = 5
    def setUp(self):
        self.e = get_env(5, 20)
    def test_populate_model(self):
        model = gp.Model('CLModel')
        cl = CurtailableLoad(self.e, 2, 0.5)
        cl.populate_model(model)
        obj = gp.quicksum(cl.P_El_vars)
        model.setObjective(obj)
        model.optimize()
        cl.update_schedule()
        self.assertAlmostEqual(5, obj.getValue())
        self.assertTrue(
            5, sum(cl.P_El_Schedule[:5]))

    def test_populate_model_on_off(self):
        model = gp.Model('CLModel')
        cl = CurtailableLoad(self.e, 2, 0.5, 2, 2)
        cl.populate_model(model)
        obj = gp.quicksum(cl.P_El_vars)
        model.setObjective(obj)
        model.optimize()
        cl.update_schedule()
        self.assertAlmostEqual(7, obj.getValue())
        self.assertAlmostEqual(7, sum(cl.P_El_Schedule[:5]))

    def test_populate_model_integer(self):
        for low, full in self.combinations:
            min_states = sum(np.tile([False]*low + [True]*full, 5)[:5])
            for nom in [0.5, 1, 2]:
                with self.subTest(msg="max_low={} min_full={} nom={}".format(low, full, nom)):
                    model = gp.Model('CLModel')
                    cl = CurtailableLoad(self.e, nom, 0.75, low, full)
                    cl.populate_model(model, mode="integer")
                    obj = gp.quicksum(cl.P_El_vars)
                    model.setObjective(obj)
                    model.optimize()
                    cl.update_schedule()
                    schedule_states = np.isclose(cl.P_El_Schedule[:5], [nom]*5)
                    assert_equal_array(cl.P_State_Schedule[:5], schedule_states)
                    self.assertEqual(min_states, sum(schedule_states))
                    self.assertAlmostEqual(min_states*nom+(5-min_states)*nom*0.75, obj.getValue())

    def test_update_model(self):
        for width in [1, 2, 4, 5]:
            with self.subTest(msg="step width={}".format(width)):
                model = gp.Model('CLModel')
                cl = CurtailableLoad(self.e, 2, 0.5)
                cl.populate_model(model)
                obj = gp.quicksum(cl.P_El_vars)
                model.setObjective(obj)
                for t in range(0, 20-5+1, width):
                    self.e.timer.currentTimestep = t
                    cl.update_model(model)
                    model.optimize()
                    cl.update_schedule()
                    self.assertAlmostEqual(5, obj.getValue())
                    self.assertAlmostEqual(5, sum(cl.P_El_Schedule[t:t+5]))

    def test_update_model_on_off(self):
        for low, full in self.combinations:
            for width in [1, 2, 4, 5]:
                with self.subTest(msg="max_low={} min_full={} step width={}".format(low, full, width)):
                    model = gp.Model('CLModel')
                    cl = CurtailableLoad(self.e, 2, 0.5, low, full)
                    cl.populate_model(model)
                    obj = gp.quicksum(cl.P_El_vars)
                    model.setObjective(obj)
                    for t in range(0, 20-5+1, width):
                        self.e.timer.currentTimestep = t
                        cl.update_model(model)
                        model.optimize()
                        cl.update_schedule()

                    endtimestep = self.e.timer.currentTimestep + cl.op_horizon
                    for t in range(0, endtimestep):
                        self.assertGreaterEqual(cl.P_El_Schedule[t], 1)
                        self.assertLessEqual(cl.P_El_Schedule[t], 2)
                    for t in range(0, endtimestep-(low+full)+1):
                        self.assertGreaterEqual(sum(cl.P_El_Schedule[t:t+low+full]),
                                                1*low + 2*full)

    def test_update_model_integer(self):
        for low, full in self.combinations:
            states = np.tile([False] * low + [True] * full, 20)[:20]
            for width in [1, 2, 4, 5]:
                with self.subTest(msg="max_low={} min_full={} step width={}".format(low, full, width)):
                    model = gp.Model('CLModel')
                    cl = CurtailableLoad(self.e, 2, 0.5, low, full)
                    cl.populate_model(model, mode="integer")
                    obj = gp.quicksum(cl.P_El_vars)
                    model.setObjective(obj)
                    for t in range(0, 20-5+1, width):
                        self.e.timer.currentTimestep = t
                        cl.update_model(model, mode="integer")
                        model.setObjectiveN(gp.quicksum(cl.P_El_vars), 0, 10)
                        # move full steps towards the end
                        model.setObjectiveN(gp.quicksum([-i * cl.P_El_vars[i] for i in range(5)]), 1, 5)
                        model.setParam("MIPGap", 1e-6)
                        model.optimize()
                        self.assertEqual(model.Status, 2)
                        cl.update_schedule()
                        schedule_states_el = np.isclose(cl.P_El_Schedule[t:t+5], [2] * 5)
                        schedule_states_b = np.isclose(cl.P_State_Schedule[t:t+5], [1] * 5)
                        assert_equal_array(schedule_states_b, states[t:t + 5])
                        assert_equal_array(schedule_states_el, schedule_states_b)
                        assert_equal_array(
                            cl.P_El_Schedule[t:t+5],
                            np.full(5, 2 * 0.5) + np.array(states[t:t+5]) * (2 * (1. - 0.5))
                        )

    def test_integer_first(self):
        for low, full in self.combinations:
            if low > 0:
                with self.subTest(msg="max_low={} min_full={}".format(low, full)):
                    model = gp.Model('CLModel')

                    cl = CurtailableLoad(self.e, 2, 0.5, low, full)
                    cl.populate_model(model, mode="integer")
                    self.e.timer.currentTimestep = 1
                    cl.P_State_Schedule[0] = False
                    cl.P_El_Schedule[0] = 1
                    cl.update_model(model, "integer")

                    cl.P_State_vars[0].ub = 1
                    cl.P_State_vars[0].lb = 1
                    cl.P_State_vars[1].ub = 0
                    cl.P_State_vars[1].lb = 0

                    model.optimize()
                    if full > 1:
                        self.assertEqual(model.status, 3)
                    else:
                        self.assertEqual(model.status, 2)

    def test_small_horizon(self):
        for width in [1, 2, 4]:
            for horizon in [1, 2, 4]:
                if horizon >= width:
                    with self.subTest(msg="width={} horizon={}".format(width, horizon)):
                        e = get_env(horizon, 20)
                        model = gp.Model('CLModel')
                        cl = CurtailableLoad(e, 2, 0.5)
                        cl.populate_model(model)
                        for t in range(0, 21 - horizon, width):
                            e.timer.currentTimestep = t
                            cl.update_model(model)
                            obj = gp.quicksum(cl.P_El_vars)
                            model.setObjective(obj)
                            model.optimize()

                            self.assertEqual(1, cl.P_El_vars[0].x)

                            cl.update_schedule()

                        assert_equal_array(cl.P_El_Schedule, [1] * 20)

    def test_small_horizon_low_full(self):
        for horizon in [1, 2, 4]:
            e = get_env(horizon, 20)
            for width in [1, 2, 4]:
                if horizon >= width:
                    for low, full in self.combinations:
                        with self.subTest(msg="width={} horizon={} max_low={} min_full={}"
                                              .format(width, horizon, low, full)):

                            model = gp.Model('CLModel')
                            cl = CurtailableLoad(e, 2, 0.5, low, full)
                            cl.populate_model(model)
                            for t in range(0, 21 - horizon, width):
                                e.timer.currentTimestep = t
                                cl.update_model(model)
                                obj = gp.quicksum(cl.P_El_vars)
                                model.setObjective(obj)
                                model.setParam("MIPGap", 1e-6)
                                model.optimize()
                                cl.update_schedule()

                            for t in range(0, 20 - (low + full) + 1):
                                self.assertGreaterEqual(sum(cl.P_El_Schedule[t:t + low + full]),
                                                        1 * low + 2 * full,
                                                        np.array2string(cl.P_El_Schedule))


    def test_small_horizon_low_full_integer(self):
        for horizon in [1, 2, 4]:
            e = get_env(horizon, 20)
            for width in [1, 2, 4]:
                if horizon >= width:
                    for low, full in self.combinations:
                        with self.subTest(msg="width={} horizon={} max_low={} min_full={}".format(width, horizon, low, full)):
                            states = np.tile([1] * low + [2] * full, 20)[:20]
                            model = gp.Model('CLModel')
                            cl = CurtailableLoad(e, 2, 0.5, low, full)
                            cl.populate_model(model, mode="integer")
                            for t in range(0, 21 - horizon, width):
                                e.timer.currentTimestep = t
                                cl.update_model(model, mode="integer")
                                model.setObjectiveN(gp.quicksum(cl.P_El_vars), 0, 10)
                                # move full steps towards the end
                                model.setObjectiveN(gp.quicksum([-i*cl.P_El_vars[i] for i in range(horizon)]), 1, 5)
                                model.setParam("MIPGap", 1e-6)
                                model.optimize()
                                cl.update_schedule()

                            assert_equal_array(cl.P_El_Schedule, states)


class TestCityDistrict(unittest.TestCase):
    def setUp(self):
        e = get_env(4, 8)
        self.cd = CityDistrict(e)

    def test_get_objective(self):
        m, var_list = get_model(4)
        self.cd.P_El_vars = var_list
        m.optimize()

        self.assertEqual(self.cd.objective, "price")
        self.cd.environment.prices.da_prices = np.array([1]*2 + [4]*6)
        self.assertAlmostEqual(8.4, self.cd.get_objective().getValue())
        self.cd.objective = 'peak-shaving'
        self.assertAlmostEqual(14, self.cd.get_objective().getValue())
        self.cd.objective = 'valley-filling'
        self.cd.valley_profile = np.array([-1]*8)
        self.assertAlmostEqual(2, self.cd.get_objective().getValue())
        self.cd.objective = None
        self.assertAlmostEqual(0, self.cd.get_objective().getValue())
        self.cd.objective = "invalid"
        self.assertRaisesRegex(ValueError, ".*CityDistrict.*", self.cd.get_objective)

        self.cd.objective = "max-consumption"
        self.cd.populate_model(m)
        for t in range(4):
            self.cd.P_El_vars[t].start = t
        self.cd.P_El_vars[0].ub = -1
        m.optimize()
        self.assertAlmostEqual(1, self.cd.get_objective().getValue())


    def test_calculate_costs(self):
        self.cd.P_El_Schedule = np.array([10]*4 + [-20]*4)
        self.cd.P_El_Ref_Schedule = np.array([4]*4 + [-4]*4)
        prices = np.array([10]*4 + [20]*4)

        costs = calculate_costs(self.cd, prices=prices, feedin_factor=0.5)
        self.assertEqual(-100, costs)
        costs = calculate_costs(self.cd, timestep=4, prices=prices)
        self.assertEqual(100, costs)
        self.cd.load_schedule("Ref")
        costs = calculate_costs(self.cd, prices=prices)
        self.assertEqual(-40, costs)

    def test_calculate_co2(self):
        pv = Photovoltaic(self.cd.environment, 0, 0)
        self.cd.addEntity(pv, Point(0, 0))
        self.cd.P_El_Schedule = np.array([-5]*2 + [5]*4 + [-5]*2)
        self.cd.P_El_Ref_Schedule = np.array([-2]*2 + [2]*4 + [-2]*2)
        pv.P_El_Schedule = - np.array([10]*8)
        pv.P_El_Ref_Schedule = - np.array([4]*8)
        co2_em = np.array([100]*4 + [400]*4)

        co2 = calculate_co2(self.cd, co2_emissions=co2_em)
        self.assertEqual(2750, co2)
        co2 = calculate_co2(self.cd, timestep=4, co2_emissions=co2_em)
        self.assertEqual(1000, co2)
        self.cd.load_schedule("Ref")
        co2 = calculate_co2(self.cd, co2_emissions=co2_em)
        self.assertEqual(1100, co2)

    def test_self_consumption(self):
        pv = Photovoltaic(self.cd.environment, 0, 0)
        self.cd.addEntity(pv, Point(0, 0))
        self.cd.P_El_Schedule = np.array([4]*2 + [-4]*2 + [-10]*2 + [-2]*2)
        self.cd.P_El_Ref_Schedule = np.array([2]*2 + [-6]*2 + [-9]*2 + [-1]*2)
        pv.P_El_Schedule = - np.array([0]*2 + [8]*4 + [0]*2)
        pv.P_El_Ref_Schedule = - np.array([0]*8)

        self.assertEqual(0.25, self_consumption(self.cd))
        self.assertEqual(0.5, self_consumption(self.cd, timestep=4))
        self.cd.load_schedule("Ref")
        self.assertEqual(1, self_consumption(self.cd))

    def test_calculate_adj_costs(self):
        self.cd.P_El_Schedule = np.array([4] * 2 + [-4] * 2 + [-10] * 2 + [-2] * 2)
        self.cd.P_El_Ref_Schedule = np.array([2] * 2 + [-6] * 2 + [-9] * 2 + [-1] * 2)
        prices = np.array([10] * 4 + [20] * 4)
        costs_adj = calculate_adj_costs(self.cd, "Ref", prices=prices)
        self.assertEqual(2*5+2*5+1*10+1*10, costs_adj)
        costs_adj = calculate_adj_costs(self.cd, "Ref", prices=prices, total_adjustments=False)
        self.assertEqual(20, costs_adj)
        self.cd.copy_schedule("Ref")
        costs_adj = calculate_adj_costs(self.cd, "Ref", prices=prices)
        self.assertEqual(0, costs_adj)

    def test_autarky(self):
        pv = Photovoltaic(self.cd.environment, 0, 0)
        self.cd.addEntity(pv, Point(0, 0))
        self.cd.P_El_Schedule = np.array([4]*2 + [-4]*2 + [-10]*2 + [-2]*2)
        self.cd.P_El_Ref_Schedule = - np.array([0]*2 + [8]*4 + [0]*2)
        pv.P_El_Schedule = - np.array([0]*2 + [8]*4 + [0]*2)
        pv.P_El_Ref_Schedule = - np.array([0]*2 + [8]*4 + [0]*2)

        self.assertEqual(0.5, autarky(self.cd))
        self.assertEqual(0, autarky(self.cd, timestep=2))
        self.cd.load_schedule("Ref")
        self.assertEqual(1, autarky(self.cd))


class TestCombinedHeatPower(unittest.TestCase):
    def setUp(self):
        e = get_env(4, 8)
        self.chp = CombinedHeatPower(e, 10, 10, 0.8)

    def test_calculate_co2(self):
        self.chp.P_Th_Schedule = - np.array([10] * 8)
        self.chp.P_Th_Ref_Schedule = - np.array([4] * 8)
        co2_em = np.array([1111]*8)

        co2 = calculate_co2(self.chp, co2_emissions=co2_em)
        self.assertEqual(23750, co2)
        co2 = calculate_co2(self.chp, timestep=4, co2_emissions=co2_em)
        self.assertEqual(11875, co2)
        self.chp.load_schedule("Ref")
        co2 = calculate_co2(self.chp, co2_emissions=co2_em)
        self.assertEqual(9500, co2)

    def test_lower_activation(self):
        e = get_env(4, 8)
        chp = CombinedHeatPower(e, 10, 10, 0.8, 0.5)
        m = gp.Model('CHPModel')
        chp.populate_model(m, "integer")
        chp.update_model(m, "integer")
        m.optimize()


class TestDeferrableLoad(unittest.TestCase):
    def setUp(self):
        self.e = get_env(6, 9)
        self.lt = [0, 1, 1, 1, 0, 1, 1, 1, 0]

    def test_update_model(self):
        dl = DeferrableLoad(self.e, 19, 10, load_time=self.lt)
        model = gp.Model('DLModel')
        dl.populate_model(model)
        obj = gp.QuadExpr()
        obj.addTerms(
            [1] * 6,
            dl.P_El_vars,
            dl.P_El_vars
        )
        model.setObjective(obj)
        dl.update_model(model)
        model.optimize()

        self.assertAlmostEqual(10, gp.quicksum(dl.P_El_vars).getValue() * dl.time_slot, places=5)

        dl.timer.mpc_update()
        dl.update_model(model)
        model.optimize()

        for t, c in enumerate(self.lt[1:7]):
            if c == 1:
                self.assertEqual(19, dl.P_El_vars[t].ub)
            else:
                self.assertEqual(0, dl.P_El_vars[t].ub)
        dl.update_schedule()
        assert_equal_array(dl.P_El_Schedule[:7], [0, 8, 8, 8, 0, 8, 8])

    def test_infeasible_consumption(self):
        feasible = DeferrableLoad(self.e, 10, 10, load_time=self.lt)
        m = gp.Model('DLFeasable')
        feasible.populate_model(m)
        feasible.update_model(m)
        m.optimize()
        self.assertEqual(m.status, 2)

        m = gp.Model('DLInfesable')
        infeasible = DeferrableLoad(self.e, 10, 10.6, load_time=self.lt)
        infeasible.populate_model(m)
        infeasible.update_model(m)
        m.optimize()
        self.assertEqual(m.status, 3)

    def test_update_model_integer(self):
        dl = DeferrableLoad(self.e, 19, 9.5, load_time=self.lt)
        model = gp.Model('DLModel')
        dl.populate_model(model, mode="integer")
        obj = gp.QuadExpr()
        obj.addTerms(
            [0] * 2 + [1] * 2 + [0] * 2,
            dl.P_El_vars,
            dl.P_El_vars
        )
        model.setObjective(obj)
        dl.update_model(model, mode="integer")
        model.optimize()
        dl.update_schedule()

        assert_equal_array(dl.P_El_Schedule[:6], [0, 19, 19, 0, 0, 0])
        for _ in range(3):
            dl.timer.mpc_update()
            dl.update_model(model, mode="integer")
            model.optimize()
            dl.update_schedule()

        assert_equal_array(dl.P_El_Schedule, [0, 19, 19, 0, 0, 0, 19, 19, 0])

    def test_infeasible_integer(self):
        e = get_env(1, 9)
        dl = DeferrableLoad(e, 19, 9.5, load_time=self.lt)
        model = gp.Model('DLModel')
        dl.populate_model(model, mode="integer")
        dl.update_model(model, mode="integer")
        model.optimize()
        self.assertEqual(model.status, 3)

        dl = DeferrableLoad(self.e, 19, 19, load_time=self.lt)
        model = gp.Model('DLModel')
        dl.populate_model(model, mode="integer")
        dl.update_model(model, mode="integer")
        model.optimize()
        self.assertEqual(model.status, 3)

        dl = DeferrableLoad(self.e, 19, 19*3/4, load_time=self.lt)
        model = gp.Model('DLModel')
        dl.populate_model(model, mode="integer")
        dl.update_model(model, mode="integer")
        model.optimize()
        self.assertEqual(model.status, 2)
        dl.update_schedule()
        assert_equal_array(dl.P_El_Schedule[:6], [0, 19, 19, 19, 0, 0])


class TestFixedLoad(unittest.TestCase):
    def setUp(self):
        e = get_env(2, 4)
        load = np.arange(1, 5)
        self.fl = FixedLoad(e, method=0, demand=load)


class TestElectricalEntity(unittest.TestCase):
    def setUp(self):
        e = get_env(4, 8, 4)
        self.ee = ElectricalEntity(e)
        self.ee.environment = e

    def test_update_schedule(self):
        m, var_list = get_model(4)
        m.optimize()
        self.ee.P_El_vars = var_list
        a = np.arange(4)

        self.ee.update_schedule()
        assert_equal_array(self.ee.P_El_Schedule[:4], a)
        self.ee.timer.mpc_update()
        self.ee.update_schedule()
        assert_equal_array(self.ee.P_El_Schedule[4:], a)

    def test_calculate_costs(self):
        self.ee.P_El_Schedule = np.array([10]*4 + [-20]*4)
        self.ee.P_El_Ref_Schedule = np.array([4]*4 + [-4]*4)
        prices = np.array([10]*4 + [20]*4)

        costs = calculate_costs(self.ee, prices=prices, feedin_factor=0.5)
        self.assertEqual(-100, costs)
        costs = calculate_costs(self.ee, timestep=4, prices=prices)
        self.assertEqual(100, costs)
        self.ee.load_schedule("Ref")
        costs = calculate_costs(self.ee, prices=prices)
        self.assertEqual(40, costs)

    def test_calculate_adj_costs(self):
        self.ee.P_El_Schedule = np.array([10] * 4 + [-20] * 4)
        self.ee.P_El_Ref_Schedule = np.array([4] * 4 + [-4] * 4)
        prices = np.array([10] * 4 + [20] * 4)
        costs_adj = calculate_adj_costs(self.ee, "Ref", prices=prices)
        self.assertEqual(6*10 + 16*20, costs_adj)
        costs_adj = calculate_adj_costs(self.ee, "Ref", prices=prices, total_adjustments=False)
        self.assertEqual(16 * 20, costs_adj)
        self.ee.copy_schedule("Ref")
        costs_adj = calculate_adj_costs(self.ee, "Ref", prices=prices)
        self.assertEqual(0, costs_adj)

    def test_calculate_adj_power(self):
        self.ee.P_El_Schedule = np.array([10] * 4 + [-20] * 4)
        self.ee.P_El_Ref_Schedule = np.array([4] * 4 + [-4] * 4)
        adj_power = calculate_adj_power(self.ee, "Ref")
        assert_equal_array(adj_power, [6] * 4 + [16] * 4)
        adj_power = calculate_adj_power(self.ee, "Ref", total_adjustments=False)
        assert_equal_array(adj_power, [0] * 4 + [16] * 4)
        adj_power = calculate_adj_power(self.ee, "default")
        assert_equal_array(adj_power, [0] * 8)
        self.ee.load_schedule("Ref")
        adj_power = calculate_adj_power(self.ee, "Ref")
        assert_equal_array(adj_power, [0] * 8)
        self.ee.copy_schedule("default")
        adj_power = calculate_adj_power(self.ee, "default")
        assert_equal_array(adj_power, [0] * 8)

    def test_calculate_adj_energy(self):
        self.ee.P_El_Schedule = np.array([10] * 4 + [-20] * 4)
        self.ee.P_El_Ref_Schedule = np.array([4] * 4 + [-4] * 4)
        adj_energy = calculate_adj_energy(self.ee, "Ref")
        self.assertEqual(6 + 16, adj_energy)
        adj_energy = calculate_adj_energy(self.ee, "Ref", total_adjustments=False)
        self.assertEqual(16, adj_energy)
        adj_energy = calculate_adj_energy(self.ee, "default")
        self.assertEqual(0, adj_energy)
        self.ee.copy_schedule(src="Ref")
        adj_energy = calculate_adj_energy(self.ee, "Ref")
        self.assertEqual(0, adj_energy)
        adj_energy = calculate_adj_energy(self.ee, "Ref", total_adjustments=False)
        self.assertEqual(0, adj_energy)
        self.ee.load_schedule("Ref")
        adj_energy = calculate_adj_energy(self.ee, "Ref")
        self.assertEqual(0, adj_energy)
        adj_energy = calculate_adj_energy(self.ee, "default")
        self.assertEqual(0, adj_energy)

    def test_metric_delta_g(self):
        self.ee.P_El_Schedule = np.array([10] * 4 + [-20] * 4)
        self.ee.P_El_Ref_Schedule = np.array([4] * 4 + [-4] * 4)
        g = metric_delta_g(self.ee, "Ref")
        self.assertEqual(1-30/8, g)
        g = metric_delta_g(self.ee, "default")
        self.assertEqual(0, g)

    def test_peak_to_average_ratio(self):
        self.ee.P_El_Schedule = np.array([10] * 4 + [-20] * 4)
        self.ee.P_El_Ref_Schedule = np.array([4] * 4 + [-4] * 4)
        ratio = peak_to_average_ratio(self.ee)
        self.assertEqual(20/5, ratio)
        self.ee.load_schedule("Ref")
        ratio = peak_to_average_ratio(self.ee)
        self.assertEqual(np.inf, ratio)

    def test_peak_reduction_ratio(self):
        self.ee.P_El_Schedule = np.array([10] * 4 + [-20] * 4)
        self.ee.P_El_Ref_Schedule = np.array([4] * 4 + [-4] * 4)
        ratio = peak_reduction_ratio(self.ee, "Ref")
        self.assertEqual((20-4)/4, ratio)
        self.ee.P_El_Ref_Schedule = np.array([4] * 8)
        ratio = peak_reduction_ratio(self.ee, "Ref")
        self.assertEqual((20-4)/4, ratio)
        ratio = peak_reduction_ratio(self.ee, "default")
        self.assertEqual(0, ratio)
        self.ee.load_schedule("Ref")
        ratio = peak_reduction_ratio(self.ee, "Ref")
        self.assertEqual(0, ratio)

    def test_self_consumption(self):
        # properly tested in CityDistrict
        self.ee.P_El_Schedule = np.array([10]*4 + [-20]*4)
        self.assertEqual(0, self_consumption(self.ee))

    def test_autarky(self):
        # properly tested in CityDistrict
        self.ee.P_El_Schedule = np.array([10]*4 + [-20]*4)
        self.assertEqual(0, autarky(self.ee))


class TestElectricalHeater(unittest.TestCase):
    def setUp(self):
        e = get_env(4, 8)
        self.eh = ElectricalHeater(e, 10, 10, 0.8)

    def test_lower_activation(self):
        e = get_env(4, 8)
        eh = ElectricalHeater(e, 10, lower_activation_limit=0.5)
        m = gp.Model('EHPModel')
        eh.populate_model(m, "integer")
        eh.update_model(m, "integer")
        m.optimize()


class TestElectricVehicle(unittest.TestCase):
    def setUp(self):
        e = get_env(6, 9)
        self.ct = [1, 1, 1, 0, 0, 0, 1, 1, 1]
        self.ev = ElectricalVehicle(e, 10, 20, 0.5, charging_time=self.ct)

    def test_populate_model(self):
        model = gp.Model('EVModel')
        self.ev.populate_model(model)
        model.addConstr(self.ev.E_El_vars[2] == 10)
        model.addConstr(self.ev.E_El_vars[0] == 5)
        obj = gp.QuadExpr()
        obj.addTerms(
            [1] * 6,
            self.ev.P_El_Demand_vars,
            self.ev.P_El_Demand_vars
        )
        model.setObjective(obj)
        model.optimize()

        var_list = [var.varname for var in model.getVars()]
        self.assertEqual(30, len(var_list))
        var_sum = sum(map(lambda v: v.x, self.ev.P_El_vars[1:]))
        self.assertAlmostEqual(20, var_sum, places=5)
        var_sum = sum(map(
            lambda v: v.x,
            self.ev.P_El_Supply_vars[1:] + self.ev.P_El_Demand_vars[1:]
        ))
        self.assertAlmostEqual(20, var_sum, places=5)

    def test_update_model(self):
        model = gp.Model('EVModel')
        self.ev.populate_model(model)
        self.ev.update_model(model)
        model.optimize()

        self.assertAlmostEqual(10, self.ev.E_El_vars[2].x, places=5)
        self.assertAlmostEqual(2, self.ev.E_El_vars[3].x, places=5)

        self.ev.timer.mpc_update()
        self.ev.update_model(model)
        model.optimize()

        for t, c in enumerate(self.ct[1:7]):
            if c:
                self.assertEqual(20, self.ev.P_El_Demand_vars[t].ub)
                self.assertEqual(20, self.ev.P_El_Supply_vars[t].ub)
                self.assertEqual(0, self.ev.P_El_Drive_vars[t].ub)
            else:
                self.assertEqual(0, self.ev.P_El_Demand_vars[t].ub)
                self.assertEqual(0, self.ev.P_El_Supply_vars[t].ub)
                self.assertTrue(np.isinf(self.ev.P_El_Drive_vars[t].ub))
        self.assertAlmostEqual(10, self.ev.E_El_vars[1].x, places=5)
        self.assertAlmostEqual(2, self.ev.E_El_vars[2].x, places=5)
        self.assertLessEqual(1.6, self.ev.E_El_vars[-1].x)

        self.ev.timer.mpc_update()
        self.ev.timer.mpc_update()
        self.ev.update_model(model)
        model.optimize()

        self.assertAlmostEqual(5, self.ev.E_El_vars[-1].x, places=5)

    def test_get_objective(self):
        model = gp.Model('EVModel')
        self.ev.P_El_vars.append(model.addVar())
        self.ev.P_El_vars.append(model.addVar())
        self.ev.P_El_vars.append(model.addVar())
        self.ev.P_El_vars.append(model.addVar())
        self.ev.P_El_vars.append(model.addVar())
        self.ev.P_El_vars.append(model.addVar())
        obj = self.ev.get_objective(11)
        for i in range(6):
            ref = (i + 1) / 21 * 6 * 11
            coeff = obj.getCoeff(i)
            self.assertAlmostEqual(ref, coeff, places=5)


class TestHeatPump(unittest.TestCase):
    def setUp(self):
        e = get_env(4, 8)
        self.hp = HeatPump(e, 10, cop=np.full(8, 11))

    def test_populate_model(self):
        m = gp.Model()
        self.hp.populate_model(m)
        m.update()

        c = self.hp.coupl_constrs[0]
        self.assertEqual(1, m.getCoeff(c, self.hp.P_El_vars[0]))
        self.assertEqual(1, m.getCoeff(c, self.hp.P_Th_vars[0]))

    def test_update_model(self):
        m = gp.Model()
        self.hp.populate_model(m)
        self.hp.update_model(m)
        m.update()

        c = self.hp.coupl_constrs[0]
        self.assertEqual(11, m.getCoeff(c, self.hp.P_El_vars[0]))
        self.assertEqual(1, m.getCoeff(c, self.hp.P_Th_vars[0]))

    def test_lower_activation(self):
        e = get_env(4, 8)
        hp = HeatPump(e, 10, lower_activation_limit=0.5)
        m = gp.Model('HPModel')
        hp.populate_model(m, "integer")
        hp.update_model(m, "integer")
        m.optimize()


class TestPhotovoltaic(unittest.TestCase):
    def setUp(self):
        e = get_env(4, 8)
        self.pv = Photovoltaic(e, 30, 0.3)

    def test_calculate_co2(self):
        self.pv.P_El_Schedule = - np.array([10]*8)
        self.pv.P_El_Ref_Schedule = - np.array([4]*8)
        co2_em = np.array([1111]*8)

        co2 = calculate_co2(self.pv, co2_emissions=co2_em)
        self.assertEqual(1500, co2)
        co2 = calculate_co2(self.pv, timestep=4, co2_emissions=co2_em)
        self.assertEqual(750, co2)
        self.pv.load_schedule("Ref")
        co2 = calculate_co2(self.pv, co2_emissions=co2_em)
        self.assertEqual(600, co2)


class TestPrices(unittest.TestCase):
    def test_cache(self):
        Prices.co2_price_cache = None
        Prices.da_price_cache = None
        Prices.tou_price_cache = None
        ti = Timer(op_horizon=4, mpc_horizon=8, step_size=3600,
                   initial_date=(2015, 1, 1), initial_time=(1, 0, 0))
        pr = Prices(ti)

        self.assertEqual(35040, len(pr.da_price_cache))
        self.assertEqual(35040, len(pr.tou_price_cache))
        self.assertEqual(35040, len(pr.co2_price_cache))
        self.assertTrue(np.allclose(pr.tou_prices, [23.2621]*6 + [42.2947]*2))

        Prices.da_price_cache[4] = 20
        ti = Timer(op_horizon=4, mpc_horizon=8, step_size=900,
                   initial_date=(2015, 1, 1), initial_time=(1, 0, 0))
        pr = Prices(ti)

        self.assertAlmostEqual(20, pr.da_prices[0], places=4)


class TestThermalEnergyStorage(unittest.TestCase):
    def setUp(self):
        e = get_env(3)
        self.tes = ThermalEnergyStorage(e, 40, 0.5)

    def test_update_schedule(self):
        m1, var_list = get_model(3)
        m1.optimize()
        self.tes.P_Th_vars = var_list
        m2, var_list = get_model(3, 2)
        m2.optimize()
        self.tes.E_Th_vars = var_list
        a = np.arange(3)

        self.tes.update_schedule()
        assert_equal_array(self.tes.P_Th_Schedule, a)
        assert_equal_array(self.tes.E_Th_Schedule, a * 2)


class TestThermalEntity(unittest.TestCase):
    def setUp(self):
        e = get_env(4, 8, 4)
        self.th = ThermalEntity(e)
        self.th.environment = e

    def test_update_schedule(self):
        m, var_list = get_model(4)
        m.optimize()
        self.th.P_Th_vars = var_list
        a = np.arange(4)

        self.th.update_schedule()
        assert_equal_array(self.th.P_Th_Schedule[:4], a)
        self.th.timer.mpc_update()
        self.th.update_schedule()
        assert_equal_array(self.th.P_Th_Schedule[4:], a)


class TestSpaceHeating(unittest.TestCase):
    def setUp(self):
        e = get_env(2, 4)
        load = np.arange(1, 5)
        self.sh = SpaceHeating(e, method=0, loadcurve=load)


class TestTimer(unittest.TestCase):
    def setUp(self):
        self.timer = Timer(mpc_horizon=192, mpc_step_width=4,
                           initial_date=(2015, 1, 15), initial_time=(12, 0, 0))
        self.timer._dt = datetime.datetime(2015, 1, 15, 13)

    def test_time_in_year(self):
        self.assertEqual(1396, self.timer.time_in_year())
        self.assertEqual(1392, self.timer.time_in_year(from_init=True))

    def test_time_in_week(self):
        self.assertEqual(340, self.timer.time_in_week())
        self.assertEqual(336, self.timer.time_in_week(from_init=True))

    def test_time_in_day(self):
        self.assertEqual(52, self.timer.time_in_day())
        self.assertEqual(48, self.timer.time_in_day(from_init=True))


class TestWindEnergyConverter(unittest.TestCase):
    def setUp(self):
        e = get_env(4, 8)
        self.wec = WindEnergyConverter(e, [0, 10], [0, 10])

    def test_calculate_co2(self):
        self.wec.P_El_Schedule = - np.array([10] * 8)
        self.wec.P_El_Ref_Schedule = - np.array([4] * 8)
        co2_em = np.array([1111]*8)

        co2 = calculate_co2(self.wec, co2_emissions=co2_em)
        self.assertEqual(500, co2)
        co2 = calculate_co2(self.wec, timestep=4, co2_emissions=co2_em)
        self.assertEqual(250, co2)
        self.wec.load_schedule("Ref")
        co2 = calculate_co2(self.wec, co2_emissions=co2_em)
        self.assertEqual(200, co2)


def get_env(op_horizon, mpc_horizon=None, mpc_step_width=1):
    ti = Timer(op_horizon=op_horizon,
               mpc_horizon=mpc_horizon,
               mpc_step_width=mpc_step_width)
    we = Weather(ti)
    pr = Prices(ti)
    return Environment(ti, we, pr)


def get_model(var_length, factor=1):
    m = gp.Model()
    var_list = []
    for i in range(var_length):
        b = i*factor
        var_list.append(m.addVar(lb=b, ub=b))
    return m, var_list


def assert_equal_array(a: np.ndarray, expected):
    if not np.allclose(a, expected):
        expected = np.array(expected)
        msg = "Array {} does not equal expected array {}".format(np.array2string(a), np.array2string(expected))
        raise AssertionError(msg)
