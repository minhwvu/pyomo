#  ___________________________________________________________________________
#
#  Pyomo: Python Optimization Modeling Objects
#  Copyright (c) 2008-2022
#  National Technology and Engineering Solutions of Sandia, LLC
#  Under the terms of Contract DE-NA0003525 with National Technology and
#  Engineering Solutions of Sandia, LLC, the U.S. Government retains certain
#  rights in this software.
#  This software is distributed under the 3-clause BSD License.
#  ___________________________________________________________________________

import pyomo.common.unittest as unittest

from pyomo.environ import (
    ConcreteModel, Constraint, NonNegativeIntegers,  SolverFactory, Suffix,
    TransformationFactory, value, Var
)
from pyomo.gdp import Disjunct, Disjunction
from pyomo.gdp.tests.common_tests import (
    check_linear_coef, check_obj_in_active_tree)
from pyomo.repn import generate_standard_repn

gurobi_available = SolverFactory('gurobi').available()

class LinearModelDecisionTreeExample(unittest.TestCase):
    def make_model(self):
        m = ConcreteModel()
        m.x1 = Var(bounds=(-10, 10))
        m.x2 = Var(bounds=(-20, 20))
        m.d = Var(bounds=(-1000, 1000))

        m.d1 = Disjunct()
        m.d1.x1_bounds = Constraint(expr=(0.5, m.x1, 2))
        m.d1.x2_bounds = Constraint(expr=(0.75, m.x2, 3))
        m.d1.func = Constraint(expr=m.x1 + m.x2 == m.d)

        m.d2 = Disjunct()
        m.d2.x1_bounds = Constraint(expr=(0.65, m.x1, 3))
        m.d2.x2_bounds = Constraint(expr=(3, m.x2, 10))
        m.d2.func = Constraint(expr=2*m.x1 + 4*m.x2 + 7 == m.d)

        m.d3 = Disjunct()
        m.d3.x1_bounds = Constraint(expr=(2, m.x1, 10))
        m.d3.x2_bounds = Constraint(expr=(0.55, m.x2, 1))
        m.d3.func = Constraint(expr=m.x1 - 5*m.x2 - 3 == m.d)

        m.disjunction = Disjunction(expr=[m.d1, m.d2, m.d3])

        return m

    def get_Ms(self, m):
        return {
            (m.d1.x1_bounds, m.d2) : (0.15, 1),
            (m.d1.x2_bounds, m.d2) : (2.25, 7),
            (m.d1.x1_bounds, m.d3) : (1.5, 8),
            (m.d1.x2_bounds, m.d3) : (-0.2, -2),
            (m.d2.x1_bounds, m.d1) : (-0.15, -1),
            (m.d2.x2_bounds, m.d1) : (-2.25, -7),
            (m.d2.x1_bounds, m.d3) : (1.35, 7),
            (m.d2.x2_bounds, m.d3) : (-2.45, -9),
            (m.d3.x1_bounds, m.d1) : (-1.5, -8),
            (m.d3.x2_bounds, m.d1) : (0.2, 2),
            (m.d3.x1_bounds, m.d2) : (-1.35, -7),
            (m.d3.x2_bounds, m.d2) : (2.45, 9),
            (m.d1.func, m.d2) : (-40, -16.65),
            (m.d1.func, m.d3) : (6.3, 9),
            (m.d2.func, m.d1) : (9.75, 18),
            (m.d2.func, m.d3) : (16.95, 29),
            (m.d3.func, m.d1) : (-21, -7.5),
            (m.d3.func, m.d2) : (-103, -37.65),
            }

    def check_untightened_bounds_constraint(self, cons, var, parent_disj,
                                            disjunction, Ms, lower=None,
                                            upper=None):
        repn = generate_standard_repn(cons.body)
        self.assertTrue(repn.is_linear())
        self.assertEqual(len(repn.linear_vars), 3)
        self.assertIsNone(cons.lower)
        self.assertEqual(value(cons.upper), 0)
        if lower is not None:
            self.assertEqual(repn.constant, lower)
            check_linear_coef(self, repn, var, -1)
            for disj in disjunction.disjuncts:
                if disj is not parent_disj:
                    check_linear_coef(self, repn, disj.binary_indicator_var,
                                      Ms[disj] - lower)
        if upper is not None:
            self.assertEqual(repn.constant, -upper)
            check_linear_coef(self, repn, var, 1)
            for disj in disjunction.disjuncts:
                if disj is not parent_disj:
                    check_linear_coef(self, repn, disj.binary_indicator_var,
                                       - Ms[disj] + upper)

    def check_all_untightened_bounds_constraints(self, m, mbm):
        # d1.x1_bounds
        cons = mbm.get_transformed_constraints(m.d1.x1_bounds)
        self.assertEqual(len(cons), 2)
        lower = cons[0]
        check_obj_in_active_tree(self, lower)
        self.check_untightened_bounds_constraint(lower, m.x1, m.d1,
                                                 m.disjunction, {m.d2: 0.65,
                                                                 m.d3: 2},
                                                 lower=0.5)
        upper = cons[1]
        check_obj_in_active_tree(self, upper)
        self.check_untightened_bounds_constraint(upper, m.x1, m.d1,
                                                 m.disjunction, {m.d2: 3, m.d3:
                                                                 10}, upper=2)

        # d1.x2_bounds
        cons = mbm.get_transformed_constraints(m.d1.x2_bounds)
        self.assertEqual(len(cons), 2)
        lower = cons[0]
        check_obj_in_active_tree(self, lower)
        self.check_untightened_bounds_constraint(lower, m.x2, m.d1,
                                                 m.disjunction, {m.d2: 3,
                                                                 m.d3: 0.55},
                                                 lower=0.75)
        upper = cons[1]
        check_obj_in_active_tree(self, upper)
        self.check_untightened_bounds_constraint(upper, m.x2, m.d1,
                                                 m.disjunction, {m.d2: 10, m.d3:
                                                                 1}, upper=3)

        # d2.x1_bounds
        cons = mbm.get_transformed_constraints(m.d2.x1_bounds)
        self.assertEqual(len(cons), 2)
        lower = cons[0]
        check_obj_in_active_tree(self, lower)
        self.check_untightened_bounds_constraint(lower, m.x1, m.d2,
                                                 m.disjunction, {m.d1: 0.5,
                                                                 m.d3: 2},
                                                 lower=0.65)
        upper = cons[1]
        check_obj_in_active_tree(self, upper)
        self.check_untightened_bounds_constraint(upper, m.x1, m.d2,
                                                 m.disjunction, {m.d1: 2, m.d3:
                                                                 10}, upper=3)

        #d2.x2_bounds
        cons = mbm.get_transformed_constraints(m.d2.x2_bounds)
        self.assertEqual(len(cons), 2)
        lower = cons[0]
        check_obj_in_active_tree(self, lower)
        self.check_untightened_bounds_constraint(lower, m.x2, m.d2,
                                                 m.disjunction, {m.d1: 0.75,
                                                                 m.d3: 0.55},
                                                 lower=3)
        upper = cons[1]
        self.check_untightened_bounds_constraint(upper, m.x2, m.d2,
                                                 m.disjunction, {m.d1: 3, m.d3:
                                                                 1}, upper=10)

        # d3.x1_bounds
        cons = mbm.get_transformed_constraints(m.d3.x1_bounds)
        self.assertEqual(len(cons), 2)
        lower = cons[0]
        self.check_untightened_bounds_constraint(lower, m.x1, m.d3,
                                                 m.disjunction, {m.d1: 0.5,
                                                                 m.d2: 0.65},
                                                 lower=2)
        upper = cons[1]
        check_obj_in_active_tree(self, upper)
        self.check_untightened_bounds_constraint(upper, m.x1, m.d3,
                                                 m.disjunction, {m.d1: 2, m.d2:
                                                                 3}, upper=10)

        #d3.x2_bounds
        cons = mbm.get_transformed_constraints(m.d3.x2_bounds)
        self.assertEqual(len(cons), 2)
        lower = cons[0]
        check_obj_in_active_tree(self, lower)
        self.check_untightened_bounds_constraint(lower, m.x2, m.d3,
                                                 m.disjunction, {m.d1: 0.75,
                                                                 m.d2: 3},
                                                 lower=0.55)
        upper = cons[1]
        check_obj_in_active_tree(self, upper)
        self.check_untightened_bounds_constraint(upper, m.x2, m.d3,
                                                 m.disjunction, {m.d1: 3, m.d2:
                                                                 10}, upper=1)

    def check_linear_func_constraints(self, m, mbm, Ms=None):
        if Ms is None:
            Ms = self.get_Ms(m)

        #d1.func
        cons = mbm.get_transformed_constraints(m.d1.func)
        self.assertEqual(len(cons), 2)
        lower = cons[0]
        check_obj_in_active_tree(self, lower)
        self.assertEqual(value(lower.upper), 0)
        self.assertIsNone(lower.lower)
        repn = generate_standard_repn(lower.body)
        self.assertTrue(repn.is_linear())
        self.assertEqual(len(repn.linear_vars), 5)
        self.assertEqual(repn.constant, 0)
        check_linear_coef(self, repn, m.x1, -1)
        check_linear_coef(self, repn, m.x2, -1)
        check_linear_coef(self, repn, m.d, 1)
        check_linear_coef(self, repn, m.d2.binary_indicator_var, Ms[m.d1.func,
                                                                    m.d2][0])
        check_linear_coef(self, repn, m.d3.binary_indicator_var, Ms[m.d1.func,
                                                                    m.d3][0])
        upper = cons[1]
        check_obj_in_active_tree(self, upper)
        self.assertEqual(value(upper.upper), 0)
        self.assertIsNone(upper.lower)
        repn = generate_standard_repn(upper.body)
        self.assertTrue(repn.is_linear())
        self.assertEqual(len(repn.linear_vars), 5)
        self.assertEqual(repn.constant, 0)
        check_linear_coef(self, repn, m.x1, 1)
        check_linear_coef(self, repn, m.x2, 1)
        check_linear_coef(self, repn, m.d, -1)
        check_linear_coef(self, repn, m.d2.binary_indicator_var, -Ms[m.d1.func,
                                                                     m.d2][1])
        check_linear_coef(self, repn, m.d3.binary_indicator_var, -Ms[m.d1.func,
                                                                     m.d3][1])

        #d2.func
        cons = mbm.get_transformed_constraints(m.d2.func)
        self.assertEqual(len(cons), 2)
        lower = cons[0]
        check_obj_in_active_tree(self, lower)
        self.assertEqual(value(lower.upper), 0)
        self.assertIsNone(lower.lower)
        repn = generate_standard_repn(lower.body)
        self.assertTrue(repn.is_linear())
        self.assertEqual(len(repn.linear_vars), 5)
        self.assertEqual(repn.constant, -7)
        check_linear_coef(self, repn, m.x1, -2)
        check_linear_coef(self, repn, m.x2, -4)
        check_linear_coef(self, repn, m.d, 1)
        check_linear_coef(self, repn, m.d1.binary_indicator_var, Ms[m.d2.func,
                                                                    m.d1][0])
        check_linear_coef(self, repn, m.d3.binary_indicator_var, Ms[m.d2.func,
                                                                    m.d3][0])
        upper = cons[1]
        check_obj_in_active_tree(self, upper)
        self.assertEqual(value(upper.upper), 0)
        self.assertIsNone(upper.lower)
        repn = generate_standard_repn(upper.body)
        self.assertTrue(repn.is_linear())
        self.assertEqual(len(repn.linear_vars), 5)
        self.assertEqual(repn.constant, 7)
        check_linear_coef(self, repn, m.x1, 2)
        check_linear_coef(self, repn, m.x2, 4)
        check_linear_coef(self, repn, m.d, -1)
        check_linear_coef(self, repn, m.d1.binary_indicator_var, -Ms[m.d2.func,
                                                                     m.d1][1])
        check_linear_coef(self, repn, m.d3.binary_indicator_var, -Ms[m.d2.func,
                                                                     m.d3][1])

        #d3.func
        cons = mbm.get_transformed_constraints(m.d3.func)
        self.assertEqual(len(cons), 2)
        lower = cons[0]
        check_obj_in_active_tree(self, lower)
        self.assertEqual(value(lower.upper), 0)
        self.assertIsNone(lower.lower)
        repn = generate_standard_repn(lower.body)
        self.assertTrue(repn.is_linear())
        self.assertEqual(len(repn.linear_vars), 5)
        self.assertEqual(repn.constant, 3)
        check_linear_coef(self, repn, m.x1, -1)
        check_linear_coef(self, repn, m.x2, 5)
        check_linear_coef(self, repn, m.d, 1)
        check_linear_coef(self, repn, m.d1.binary_indicator_var, Ms[m.d3.func,
                                                                    m.d1][0])
        check_linear_coef(self, repn, m.d2.binary_indicator_var, Ms[m.d3.func,
                                                                    m.d2][0])
        upper = cons[1]
        check_obj_in_active_tree(self, upper)
        self.assertEqual(value(upper.upper), 0)
        self.assertIsNone(upper.lower)
        repn = generate_standard_repn(upper.body)
        self.assertTrue(repn.is_linear())
        self.assertEqual(len(repn.linear_vars), 5)
        self.assertEqual(repn.constant, -3)
        check_linear_coef(self, repn, m.x1, 1)
        check_linear_coef(self, repn, m.x2, -5)
        check_linear_coef(self, repn, m.d, -1)
        check_linear_coef(self, repn, m.d1.binary_indicator_var, -Ms[m.d3.func,
                                                                     m.d1][1])
        check_linear_coef(self, repn, m.d2.binary_indicator_var, -Ms[m.d3.func,
                                                                     m.d2][1])

    @unittest.skipUnless(gurobi_available, "Gurobi is not available")
    def test_calculated_Ms_correct(self):
        # Calculating all the Ms is expensive, so we just do it in this one test
        # and then specify them for the others
        m = self.make_model()
        mbm = TransformationFactory('gdp.mbigm')
        mbm.apply_to(m)

        self.check_all_untightened_bounds_constraints(m, mbm)
        self.check_linear_func_constraints(m, mbm)

        self.assertStructuredAlmostEqual(mbm.get_all_M_values(m),
                                         self.get_Ms(m))

    def test_transformed_constraints_correct_Ms_specified(self):
        m = self.make_model()
        mbm = TransformationFactory('gdp.mbigm')
        mbm.apply_to(m, bigM=self.get_Ms(m))

        self.check_all_untightened_bounds_constraints(m, mbm)
        self.check_linear_func_constraints(m, mbm)

    def check_pretty_bound_constraints(self, cons, var, bounds, lb):
        self.assertEqual(value(cons.upper), 0)
        self.assertIsNone(cons.lower)
        repn = generate_standard_repn(cons.body)
        self.assertTrue(repn.is_linear())
        self.assertEqual(len(repn.linear_vars), len(bounds) + 1)
        self.assertEqual(repn.constant, 0)
        if lb:
            check_linear_coef(self, repn, var, -1)
            for disj, bnd in bounds.items():
                check_linear_coef(self, repn, disj.binary_indicator_var, bnd)
        else:
            check_linear_coef(self, repn, var, 1)
            for disj, bnd in bounds.items():
                check_linear_coef(self, repn, disj.binary_indicator_var, -bnd)

    def test_bounds_constraints_correct(self):
        m = self.make_model()

        mbm = TransformationFactory('gdp.mbigm')
        mbm.apply_to(m, bigM=self.get_Ms(m), tighten_bound_constraints=True)

        # Check that all the constraints are mapped to the same transformed
        # constraints.
        cons = mbm.get_transformed_constraints(m.d1.x1_bounds)
        self.assertEqual(len(cons), 2)
        same = mbm.get_transformed_constraints(m.d2.x1_bounds)
        self.assertEqual(len(same), 2)
        self.assertIs(same[0], cons[0])
        self.assertIs(same[1], cons[1])
        sameagain = mbm.get_transformed_constraints(m.d3.x1_bounds)
        self.assertEqual(len(sameagain), 2)
        self.assertIs(sameagain[0], cons[0])
        self.assertIs(sameagain[1], cons[1])

        self.check_pretty_bound_constraints(cons[0], m.x1, {m.d1: 0.5, m.d2:
                                                            0.65, m.d3: 2},
                                            lb=True)
        self.check_pretty_bound_constraints(cons[1], m.x1, {m.d1: 2, m.d2: 3,
                                                            m.d3: 10}, lb=False)

        cons = mbm.get_transformed_constraints(m.d1.x2_bounds)
        self.assertEqual(len(cons), 2)
        same = mbm.get_transformed_constraints(m.d2.x2_bounds)
        self.assertEqual(len(same), 2)
        self.assertIs(same[0], cons[0])
        self.assertIs(same[1], cons[1])
        sameagain = mbm.get_transformed_constraints(m.d3.x2_bounds)
        self.assertEqual(len(sameagain), 2)
        self.assertIs(sameagain[0], cons[0])
        self.assertIs(sameagain[1], cons[1])

        self.check_pretty_bound_constraints(cons[0], m.x2, {m.d1: 0.75, m.d2: 3,
                                                            m.d3: 0.55},
                                            lb=True)
        self.check_pretty_bound_constraints(cons[1], m.x2, {m.d1: 3, m.d2: 10,
                                                            m.d3: 1}, lb=False)

    def test_Ms_specified_as_args_honored(self):
        m = self.make_model()

        Ms = self.get_Ms(m)
        # now modify some of them--these might not be valid and I don't care
        Ms[m.d2.x2_bounds, m.d3] = (-100, 100)
        Ms[m.d3.func, m.d1] = [10, 20]

        mbigm = TransformationFactory('gdp.mbigm')
        mbigm.apply_to(m, bigM=Ms)

        self.assertStructuredAlmostEqual(mbigm.get_all_M_values(m), Ms)
        self.check_linear_func_constraints(m, mbigm, Ms)

        # Just check the constraint we should have changed
        cons = mbigm.get_transformed_constraints(m.d2.x2_bounds)
        self.assertEqual(len(cons), 2)
        # This is a little backwards because I structured these so we give the
        # bound not the value of M. So the logic here is that if we want M to
        # turn out to be -100, we need b - 3 = -100, so we pretend the bound was
        # b=-97. The same logic holds for the next one too.
        self.check_untightened_bounds_constraint(cons[0], m.x2, m.d2,
                                                 m.disjunction, {m.d1: 0.75,
                                                                 m.d3: -97},
                                                 lower=3)
        self.check_untightened_bounds_constraint(cons[1], m.x2, m.d2,
                                                 m.disjunction, {m.d1: 3,
                                                                 m.d3: 110},
                                                 upper=10)

    # TODO: This is failing because I can't figure out if Suffixes actually
    # allow tuples as keys or what I'm going to do if they don't...
    # def test_Ms_specified_as_suffixes_honored(self):
    #     m = self.make_model()
    #     m.BigM = Suffix(direction=Suffix.LOCAL)
    #     m.BigM[(m.d2.x2_bounds, m.d3)] = (-100, 100)
    #     m.d3.BigM = Suffix(direction=Suffix.LOCAL)
    #     m.d3.BigM[(m.d3.func, m.d1)] = [10, 20]

    #     arg_Ms = self.get_Ms(m)
    #     # delete the keys we replaced above
    #     del arg_Ms[m.d2.x2_bounds, m.d3]
    #     del arg_Ms[m.d3.func, m.d1]

    #     mbigm = TransformationFactory('gdp.mbigm')
    #     mbigm.apply_to(m, bigM=arg_Ms)

    #     Ms = self.get_Ms(m)
    #     self.assertStructuredAlmostEqual(mbigm.get_all_M_values(m), Ms)
    #     self.check_linear_func_constraints(m, mbigm, Ms)

    #     # Just check the constraint we should have changed
    #     cons = mbigm.get_transformed_constraints(m.d2.x2_bounds)
    #     self.assertEqual(len(cons), 2)
    #     # This is a little backwards because I structured these so we give the
    #     # bound not the value of M. So the logic here is that if we want M to
    #     # turn out to be -100, we need b - 3 = -100, so we pretend the bound was
    #     # b=-97. The same logic holds for the next one too.
    #     self.check_untightened_bounds_constraint(cons[0], m.x2, m.d2,
    #                                              m.disjunction, {m.d1: 0.75,
    #                                                              m.d3: -97},
    #                                              lower=3)
    #     self.check_untightened_bounds_constraint(cons[1], m.x2, m.d2,
    #                                              m.disjunction, {m.d1: 3,
    #                                                              m.d3: 110},
    #                                              upper=10)

    def add_fourth_disjunct(self, m):
        m.disjunction.deactivate()

        # Add a disjunct
        m.d4 = Disjunct()
        m.d4.x1_ub = Constraint(expr=m.x1 <= 8)
        m.d4.x2_lb = Constraint(expr=m.x2 >= -5)

        # Make a four-term disjunction
        m.disjunction2 = Disjunction(expr=[m.d1, m.d2, m.d3, m.d4])

    def test_deactivated_disjunct(self):
        m = self.make_model()
        # Add a new thing and deactivate it
        self.add_fourth_disjunct(m)
        m.d4.deactivate()

        mbm = TransformationFactory('gdp.mbigm')
        mbm.apply_to(m, bigM=self.get_Ms(m))

        # we don't transform d1
        self.assertIsNone(m.d4.transformation_block)
        # and everything else is the same
        self.check_linear_func_constraints(m, mbm)
        self.check_all_untightened_bounds_constraints(m, mbm)

    @unittest.skipUnless(gurobi_available, "Gurobi is not available")
    def test_var_bounds_substituted_for_missing_bound_constraints(self):
        m = self.make_model()
        # Add a new thing and deactivate it
        self.add_fourth_disjunct(m)

        mbm = TransformationFactory('gdp.mbigm')
        # only calculate the ones we don't know yet
        mbm.apply_to(m, bigM=self.get_Ms(m), tighten_bound_constraints=True)

        # check that the bounds constraints are right
        # for x1:
        cons = mbm.get_transformed_constraints(m.d1.x1_bounds)
        self.assertEqual(len(cons), 2)
        sameish = mbm.get_transformed_constraints(m.d4.x1_ub)
        self.assertEqual(len(sameish), 1)
        self.assertIs(sameish[0], cons[1])

        self.check_pretty_bound_constraints(cons[1], m.x1, {m.d1: 2, m.d2: 3,
                                                            m.d3: 10, m.d4: 8},
                                            lb=False)
        self.check_pretty_bound_constraints(cons[0], m.x1, {m.d1: 0.5, m.d2:
                                                            0.65, m.d3: 2, m.d4:
                                                            -10}, lb=True)

        # and for x2:
        cons = mbm.get_transformed_constraints(m.d1.x2_bounds)
        self.assertEqual(len(cons), 2)
        sameish = mbm.get_transformed_constraints(m.d4.x2_lb)
        self.assertEqual(len(sameish), 1)
        self.assertIs(sameish[0], cons[0])

        self.check_pretty_bound_constraints(cons[1], m.x2, {m.d1: 3, m.d2: 10,
                                                            m.d3: 1, m.d4: 20},
                                            lb=False)
        self.check_pretty_bound_constraints(cons[0], m.x2, {m.d1: 0.75, m.d2: 3,
                                                            m.d3: 0.55, m.d4:
                                                            -5}, lb=True)

    @unittest.skipUnless(gurobi_available, "Gurobi is not available")
    def test_nested_gdp(self):
        # We'll just put another disjunction on one of our disjuncts to test
        # this. There is little that is special here--we transform from leaf to
        # root, so the child Disjuncts do not interfere in the calculation of
        # the M values for their parents. However, their transformed constraints
        # are placed above the parent, so note that this means that for certain
        # models, it would be beneficial to flatten the model before using this
        # transformation, if the children *do* provide insight into the bounds
        # of the parent. (One could use them and in the subproblems and then
        # move them up, but that means the M-value subproblems would be
        # MI(N)LPs, which is a downside.)
        m = self.make_model()

        # add a disjunction
        m.d1.disjunction=Disjunction(NonNegativeIntegers)
        m.d1.disjunction[1] = [m.x1 + m.x2 <= 2, m.x1 + m.x2 == 2.2]

        mbm = TransformationFactory('gdp.mbigm')
        # transform, and use the M values we know, only calculating for the
        # nested stuff.
        mbm.apply_to(m, bigM=self.get_Ms(m))

        # Check that all the parent-Disjunction stuff is as expected
        self.check_linear_func_constraints(m, mbm)
        self.check_all_untightened_bounds_constraints(m, mbm)

        # Check the inner Disjunction
        cons = mbm.get_transformed_constraints(
            m.d1.disjunction[1].disjuncts[0].constraint[1])
        self.assertEqual(len(cons), 1)
        c = cons[0]
        check_obj_in_active_tree(self, c)
        self.assertIsNone(c.lower)
        self.assertEqual(value(c.upper), 0)
        repn = generate_standard_repn(c.body)
        self.assertTrue(repn.is_linear())
        self.assertEqual(value(repn.constant), -2)
        self.assertEqual(len(repn.linear_vars), 3)
        check_linear_coef(self, repn, m.x1, 1)
        check_linear_coef(self, repn, m.x2, 1)
        check_linear_coef(self, repn,
                          m.d1.disjunction[1].disjuncts[1].binary_indicator_var,
                          -0.2)

        cons = mbm.get_transformed_constraints(
            m.d1.disjunction[1].disjuncts[1].constraint[1])
        self.assertEqual(len(cons), 2)
        l = cons[0]
        check_obj_in_active_tree(self, l)
        self.assertIsNone(l.lower)
        self.assertEqual(value(l.upper), 0)
        repn = generate_standard_repn(l.body)
        self.assertTrue(repn.is_linear())
        self.assertEqual(value(repn.constant), 2.2)
        check_linear_coef(self, repn, m.x1, -1)
        check_linear_coef(self, repn, m.x2, -1)
        check_linear_coef(self, repn,
                          m.d1.disjunction[1].disjuncts[0].binary_indicator_var,
                          -32.2)
        u = cons[1]
        check_obj_in_active_tree(self, u)
        self.assertIsNone(u.lower)
        self.assertEqual(value(u.upper), 0)
        repn = generate_standard_repn(u.body)
        self.assertTrue(repn.is_linear())
        self.assertEqual(value(repn.constant), -2.2)
        check_linear_coef(self, repn, m.x1, 1)
        check_linear_coef(self, repn, m.x2, 1)
        check_linear_coef(self, repn,
                          m.d1.disjunction[1].disjuncts[0].binary_indicator_var,
                          0.2)


# TODO:

# test logical constraints on disjuncts
# strip packing would be a good integration test?
# test user-specified M values for bounds constraints: Maybe we should override and just warn that we're doing that. Because if the user knows a tighter M, they should change the bound. If not, then honoring their wishes is dumb.
# Need to think through how to mix and match transformations at constraint level, even... Especially with this and bigm it very much makes sense to mix them.
