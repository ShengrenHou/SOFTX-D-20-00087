"""
The pycity_scheduling framework


Copyright (C) 2021,
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

from pycity_scheduling.classes import (CityDistrict, Building, Photovoltaic, WindEnergyConverter)
from pycity_scheduling.util import extract_pyomo_values, mpi_interface, write_schedules
from pycity_scheduling.algorithms.algorithm import IterationAlgorithm, DistributedAlgorithm, SolverNode
from pycity_scheduling.solvers import DEFAULT_SOLVER, DEFAULT_SOLVER_OPTIONS


class DualDecompositionMPI(IterationAlgorithm, DistributedAlgorithm):
    """Implementation of the Dual Decomposition MPI Algorithm.

    """
    def __init__(self, city_district, solver=DEFAULT_SOLVER, solver_options=DEFAULT_SOLVER_OPTIONS, mode="convex",
                 eps_primal=0.1, rho=2.0, max_iterations=10000, robustness=None):
        """
        Set up the Dual Decomposition Algorithm for optimizing a specific city district.

        Parameters
        ----------
        city_district : CityDistrict
        solver : str, optional
            Solver to use for solving (sub)problems.
        solver_options : dict, optional
            Options to pass to calls to the solver. Keys are the name of
            the functions being called and are one of `__call__`, `set_instance_`,
            `solve`.
            `__call__` is the function being called when generating an instance
            with the pyomo SolverFactory.  Additionally to the options provided,
            `node_ids` is passed to this call containing the IDs of the entities
            being optimized.
            `set_instance` is called when a pyomo Model is set as an instance of
            a persistent solver. `solve` is called to perform an optimization. If
            not set, `save_results` and `load_solutions` may be set to false to
            provide a speedup.
        mode : str, optional
            Specifies which set of constraints to use.
            - `convex`  : Use linear constraints
            - `integer`  : May use non-linear constraints
        eps_primal : float, optional
            Primal stopping criterion for the dual decomposition algorithm.
        rho : float, optional
            Stepsize for the dual decomposition algorithm.
        max_iterations : int, optional
            Maximum number of ADMM iterations.
        robustness : tuple, optional
            Tuple of two floats. First entry defines how many time steps are
            protected from deviations. Second entry defines the magnitude of
            deviations which are considered.
        """
        super(DualDecompositionMPI, self).__init__(city_district, solver, solver_options, mode)

        self.mpi_interface = mpi_interface.MPI_Interface()

        self.eps_primal = eps_primal
        self.rho = rho
        self.max_iterations = max_iterations
        # create solver nodes for each entity
        self.nodes = [
            SolverNode(solver, solver_options, [entity], mode, robustness=robustness)
            for entity in self.entities
        ]
        # create pyomo parameters for each entity
        for node, entity in zip(self.nodes, self.entities):
            node.model.beta = pyomo.Param(mutable=True, initialize=1)
            node.model.lambdas = pyomo.Param(entity.model.t, mutable=True, initialize=0)
        self._add_objective()

    def _add_objective(self):
        for i, node, entity in zip(range(len(self.entities)), self.nodes, self.entities):
            obj = node.model.beta * entity.get_objective()
            if i == 0:
                # penalty term is expanded and constant is omitted
                # invert sign of p_el_schedule and p_el_vars (omitted for quadratic
                # term)
                obj -= pyomo.sum_product(node.model.lambdas, entity.model.p_el_vars)
            else:
                obj += pyomo.sum_product(node.model.lambdas, entity.model.p_el_vars)
            node.model.o = pyomo.Objective(expr=obj)
        return

    def _presolve(self, full_update, beta, robustness, debug):
        results, params = super()._presolve(full_update, beta, robustness, debug)

        for node, entity in zip(self.nodes, self.entities):
            node.model.beta = self._get_beta(params, entity)
            if full_update:
                node.full_update(robustness)
        results["r_norms"] = []
        results["lambdas"] = []
        return results, params

    def _postsolve(self, results, params, debug):
        if self.mpi_interface.mpi_size > 1:
            # Take actions if the number of MPI processes does not fit the total number of nodes:
            if self.mpi_interface.mpi_size > len(self.nodes):
                rank_id_range = np.array([i for i in range(len(self.nodes))])
            elif self.mpi_interface.mpi_size < len(self.nodes):
                if self.mpi_interface.mpi_size == 1:
                    rank_id_range = np.array([0 for i in range(len(self.nodes))])
                else:
                    a, b = divmod(len(self.nodes) - 1, self.mpi_interface.mpi_size - 1)
                    rank_id_range = np.repeat(np.array([i for i in range(1, self.mpi_interface.mpi_size)]), a)
                    for i in range(b):
                        rank_id_range = np.append(rank_id_range, i + 1)
                    rank_id_range = np.concatenate([[0], rank_id_range])
            else:
                rank_id_range = np.array([i for i in range(len(self.nodes))])
            rank_id_range = np.sort(rank_id_range)

            # Update all models across all MPI instances:
            entity_schedules = [None for i in range(len(self.nodes))]
            for i, node, entity in zip(range(len(self.nodes)), self.nodes, self.entities):
                if not isinstance(
                        entity,
                        (CityDistrict, Building, Photovoltaic, WindEnergyConverter)
                ):
                    continue
                if self.mpi_interface.mpi_rank == rank_id_range[i]:
                    entity.update_schedule()
                    for j in range(self.mpi_interface.mpi_size):
                        if j != self.mpi_interface.mpi_rank:
                            entity_schedules[i] = entity.schedule
                            req = self.mpi_interface.mpi_comm.isend(entity.schedule, dest=j, tag=i)
                            req.wait()
                else:
                    req = self.mpi_interface.mpi_comm.irecv(source=rank_id_range[i], tag=i)
                    data = req.wait()
                    entity_schedules[i] = data
            for i, node, entity in zip(range(len(self.nodes)), self.nodes, self.entities):
                if not isinstance(
                        entity,
                        (CityDistrict, Building, Photovoltaic, WindEnergyConverter)
                ):
                    continue
                self.entities[i].load_schedule_from_dict(entity_schedules[i])
        else:
            super()._postsolve(results, params, debug)
        return

    def _is_last_iteration(self, results, params):
        return results["r_norms"][-1] <= self.eps_primal

    def _iteration(self, results, params, debug):
        super(DualDecompositionMPI, self)._iteration(results, params, debug)
        op_horizon = self.entities[0].op_horizon
        if "lambdas" not in params:
            params["lambdas"] = np.zeros(op_horizon)
        lambdas = params["lambdas"]

        # -----------------
        # 1) optimize all entities
        # -----------------
        to_solve_nodes = []
        variables = []

        # Take actions if the number of MPI processes does not fit the total number of nodes:
        if self.mpi_interface.mpi_size > len(self.nodes):
            rank_id_range = np.array([i for i in range(len(self.nodes))])
            if self.mpi_interface.mpi_rank > len(self.nodes):
                results["r_norms"].append(np.zeros(op_horizon))
                results["lambdas"].append(np.zeros(op_horizon))
                return
        elif self.mpi_interface.mpi_size < len(self.nodes):
            if self.mpi_interface.mpi_size == 1:
                rank_id_range = np.array([0 for i in range(len(self.nodes))])
            else:
                a, b = divmod(len(self.nodes) - 1, self.mpi_interface.mpi_size - 1)
                rank_id_range = np.repeat(np.array([i for i in range(1, self.mpi_interface.mpi_size)]), a)
                for i in range(b):
                    rank_id_range = np.append(rank_id_range, i + 1)
                rank_id_range = np.concatenate([[0], rank_id_range])
        else:
            rank_id_range = np.array([i for i in range(len(self.nodes))])
        rank_id_range = np.sort(rank_id_range)

        p_el_schedules = np.empty((len(self.entities), op_horizon))
        for i, node, entity in zip(range(len(self.nodes)), self.nodes, self.entities):
            if self.mpi_interface.mpi_rank == rank_id_range[i]:
                if not isinstance(
                        entity,
                        (CityDistrict, Building, Photovoltaic, WindEnergyConverter)
                ):
                    continue

                for t in range(op_horizon):
                    node.model.lambdas[t] = lambdas[t]
                node.obj_update()
                to_solve_nodes.append(node)
                variables.append([entity.model.p_el_vars[t] for t in range(op_horizon)])
        self._solve_nodes(results, params, to_solve_nodes, variables=variables, debug=debug)

        if self.mpi_interface.mpi_rank == 0:
            p_el_schedules[0] = np.array(extract_pyomo_values(self.entities[0].model.p_el_vars, float),
                                         dtype=np.float64)
        for j in range(1, len(self.nodes)):
            if not isinstance(
                    self.entities[j],
                    (CityDistrict, Building, Photovoltaic, WindEnergyConverter)
            ):
                continue

            if self.mpi_interface.mpi_rank == 0:
                if self.mpi_interface.mpi_size > 1:
                    data = np.empty(op_horizon, dtype=np.float64)
                    self.mpi_interface.mpi_comm.Recv(data, source=rank_id_range[j],
                                                     tag=int(results["iterations"][-1]) * len(self.nodes) + j)
                    p_el_schedules[j] = np.array(data, dtype=np.float64)
                else:
                    p_el_schedules[j] = np.array(extract_pyomo_values(self.entities[j].model.p_el_vars, float),
                                                 dtype=np.float64)
            else:
                if self.mpi_interface.mpi_rank == rank_id_range[j]:
                    p_el_schedules[j] = np.array(extract_pyomo_values(self.entities[j].model.p_el_vars, float),
                                                 dtype=np.float64)
                    if self.mpi_interface.mpi_size > 1:
                        self.mpi_interface.mpi_comm.Send(p_el_schedules[j], dest=0,
                                                         tag=int(results["iterations"][-1]) * len(self.nodes) + j)

        # --------------------------
        # 2) incentive signal update
        # --------------------------
        if self.mpi_interface.mpi_rank == 0:
            lambdas -= self.rho * p_el_schedules[0]
            lambdas += self.rho * np.sum(p_el_schedules[1:], axis=0)
            r = np.zeros(op_horizon)
            r -= p_el_schedules[0]
            r += np.sum(p_el_schedules[1:], axis=0)
        else:
            lambdas = np.empty(op_horizon, dtype=np.float64)
            r = np.empty(op_horizon, dtype=np.float64)
        if self.mpi_interface.mpi_size > 1:
            self.mpi_interface.mpi_comm.Bcast(lambdas, root=0)
            self.mpi_interface.mpi_comm.Bcast(r, root=0)

        # ------------------------------------------
        # 3) Calculate parameters for stopping criteria
        # ------------------------------------------
        results["r_norms"].append(np.linalg.norm(r, np.inf))
        results["lambdas"].append(np.copy(lambdas))

        # save other parameters for another iteration
        params["lambdas"] = lambdas

        return
