import unittest

import numpy as np

from pycity_scheduling.classes import *
from pycity_scheduling.algorithms import algorithms


class TestAlgorithms(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestAlgorithms, self).__init__(*args, **kwargs)

        t = Timer(op_horizon=2)
        p = Prices(t)
        w = Weather(t)
        e = Environment(t, w, p)
        cd = CityDistrict(e, objective='valley_filling')

        bd1 = Building(e, objective='peak_shaving')
        cd.addEntity(bd1, [0, 0])
        bes = BuildingEnergySystem(e)
        bd1.addEntity(bes)
        tes = ThermalEnergyStorage(e, 1000, 0.5, 0.5)
        bes.addDevice(tes)
        eh = ElectricalHeater(e, 10)
        bes.addDevice(eh)
        ap = Apartment(e)
        bd1.addEntity(ap)
        load = np.array([10, 10])
        fi = FixedLoad(e, method=0, demand=load)
        ap.addEntity(fi)
        sh = SpaceHeating(e, method=0, loadcurve=load)
        ap.addEntity(sh)

        bd2 = Building(e, objective='peak_shaving')
        cd.addEntity(bd2, [0, 0])
        bes = BuildingEnergySystem(e)
        bd2.addEntity(bes)
        tes = ThermalEnergyStorage(e, 1000, 0.5, 0.5)
        bes.addDevice(tes)
        eh = ElectricalHeater(e, 20)
        bes.addDevice(eh)
        ap = Apartment(e)
        bd2.addEntity(ap)
        load = np.array([20, 20])
        fi = FixedLoad(e, method=0, demand=load)
        ap.addEntity(fi)
        sh = SpaceHeating(e, method=0, loadcurve=load)
        ap.addEntity(sh)

        self.timer = t
        self.cd = cd
        self.bd1 = bd1
        self.bd2 = bd2

    def setUp(self):
        self.timer.reset()
        self.cd.reset()
        self.bd1.reset()
        self.bd2.reset()

    def test_exchange_admm(self):
        f = algorithms['exchange-admm']
        r = f(self.cd, rho=2, eps_primal=0.001)

        self.assertEqual(20, self.bd1.P_El_Schedule[0])
        self.assertEqual(20, self.bd1.P_El_Schedule[1])
        self.assertEqual(40, self.bd2.P_El_Schedule[0])
        self.assertEqual(40, self.bd2.P_El_Schedule[1])
        self.assertAlmostEqual(60, self.cd.P_El_Schedule[0], 2)
        self.assertAlmostEqual(60, self.cd.P_El_Schedule[1], 2)

        # print(r[0])
        # print(r[1][-5:])
        # print(r[2][-5:])
        # print(r[3])
        #
        # print(self.cd.P_El_Schedule)
        # for bd in self.cd.get_lower_entities():
        #     print(bd.P_El_Schedule)

    def test_dual_decomposition(self):
        f = algorithms['dual-decomposition']
        f(self.cd, eps_primal=0.001)

        self.assertEqual(20, self.bd1.P_El_Schedule[0])
        self.assertEqual(20, self.bd1.P_El_Schedule[1])
        self.assertEqual(40, self.bd2.P_El_Schedule[0])
        self.assertEqual(40, self.bd2.P_El_Schedule[1])
        self.assertAlmostEqual(60, self.cd.P_El_Schedule[0], 2)
        self.assertAlmostEqual(60, self.cd.P_El_Schedule[1], 2)

    def test_stand_alone_algorithm(self):
        f = algorithms['stand-alone']
        f(self.cd)

        self.assertEqual(20, self.bd1.P_El_Schedule[0])
        self.assertEqual(20, self.bd1.P_El_Schedule[1])
        self.assertEqual(40, self.bd2.P_El_Schedule[0])
        self.assertEqual(40, self.bd2.P_El_Schedule[1])
        self.assertEqual(60, self.cd.P_El_Schedule[0], 2)
        self.assertEqual(60, self.cd.P_El_Schedule[1], 2)

    def test_local_algorithm(self):
        f = algorithms['local']
        f(self.cd)

        self.assertEqual(20, self.bd1.P_El_Schedule[0])
        self.assertEqual(20, self.bd1.P_El_Schedule[1])
        self.assertEqual(40, self.bd2.P_El_Schedule[0])
        self.assertEqual(40, self.bd2.P_El_Schedule[1])
        self.assertEqual(60, self.cd.P_El_Schedule[0], 2)
        self.assertEqual(60, self.cd.P_El_Schedule[1], 2)

    def test_central_algorithm(self):
        f = algorithms['central']
        f(self.cd)

        self.assertEqual(20, self.bd1.P_El_Schedule[0])
        self.assertEqual(20, self.bd1.P_El_Schedule[1])
        self.assertEqual(40, self.bd2.P_El_Schedule[0])
        self.assertEqual(40, self.bd2.P_El_Schedule[1])
        self.assertEqual(60, self.cd.P_El_Schedule[0], 2)
        self.assertEqual(60, self.cd.P_El_Schedule[1], 2)
