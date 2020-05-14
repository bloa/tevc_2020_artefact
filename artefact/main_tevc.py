#!/usr/bin/python

import argparse
import ast
import copy
import math
import os
import random
import re
import sys
# sys.path.append(os.getcwd())

import pyggi
pyggi.PYGGI_DIR = './logs_tevc'
from pyggi.base import Patch
from pyggi.tree import StmtReplacement, StmtInsertion, StmtDeletion

import main_base as main

# ================================================================================

from mypyggi.scenario import Scenario
from programs import MinisatProgram, Sat4jProgram, OptipngProgram, MoeaNsgaProgram

class Scenario_Tevc(Scenario):
    CORES = 1
    def setup_gi(self, step, algo):
        algo.stop['wall'] = None
        if step == 'analyse':
            algo.config['warmup'] = 9
            algo.stop['steps'] = 0
        elif step == 'training':
            algo.config['warmup'] = 3
            algo.stop['steps'] = None
            algo.stop['budget'] = 100*self.APPROX_TIME/self.FOLDS
        elif step in ['validation', 'test', 'assess-gi-training', 'assess-gp-training', 'assess-gp-test', 'assess-gp-all', 'assess-gi-all']:
            algo.config['warmup'] = 1
            algo.stop['steps'] = None
        else:
            algo.config['warmup'] = 0
            algo.stop['steps'] = 10
            algo.stop['wall'] = 3*60

class Scenario_Sat(Scenario_Tevc):
    def my_setup(self, algo):
        self.program.timeout_make = self.TIMEOUT_MAKE
        self.program.timeout_inst = self.TIMEOUT_INST

        self.program.instances_folder = self.proxify(self.INST_PATH)
        self.program.instances = self.INSTS

class Scenario_Minisat(Scenario_Sat):
    PATH = 'code/minisat-2.2.0'
    TARGETS = ['core/Solver.cc.xml']
    TIMEOUT_MAKE = 20

    def my_init(self):
        self.program = MinisatProgram(self.proxify(self.PATH), {'target_files' : self.TARGETS})

# class Scenario_MinisatCit1(Scenario_Minisat):
#     SCENARIO_NAME = 'SAT_CIT'
#     FOLDS = 5
#     TIMEOUT_INST = 45
#     APPROX_TIME = 240

#     from benchmarks.sat_cit import INST_PATH, INSTS

class Scenario_MinisatCit2(Scenario_Minisat):
    SCENARIO_NAME = 'SAT_CIT'
    FOLDS = 8
    TIMEOUT_INST = 80
    APPROX_TIME = 330

    from benchmarks.sat_cit2 import INST_PATH, INSTS

class Scenario_MinisatUniform(Scenario_Minisat):
    SCENARIO_NAME = 'SAT_Uniform'
    FOLDS = 10
    TIMEOUT_INST = 20
    APPROX_TIME = 650

    from benchmarks.sat_uniform import INST_PATH, INSTS

class Scenario_Sat4j(Scenario_Sat):
    PATH = 'code/sat4j'
    TARGETS = ['org.sat4j.core/src/main/java/org/sat4j/minisat/core/Solver.java.xml']
    TIMEOUT_MAKE = 80
    CORES = 2

    def my_init(self):
        self.program = Sat4jProgram(self.proxify(self.PATH), {'target_files' : self.TARGETS})

class Scenario_Sat4jCit2(Scenario_Sat4j):
    SCENARIO_NAME = 'SAT4J_CIT'
    FOLDS = 8
    TIMEOUT_INST = 300
    APPROX_TIME = 2130

    from benchmarks.sat_cit2 import INST_PATH, INSTS

    def my_setup(self, algo):
        super().my_setup(algo)
        self.program.max_pipesize = 1e9

class Scenario_Sat4jUniform(Scenario_Sat4j):
    SCENARIO_NAME = 'SAT4J_Uniform'
    FOLDS = 10
    TIMEOUT_INST = 30
    APPROX_TIME = 1380

    from benchmarks.sat_uniform import INST_PATH, INSTS

class Scenario_Optipng(Scenario_Tevc):
    SCENARIO_NAME = 'OptiPNG'
    PATH = 'code/optipng-0.7.7'
    TARGETS = ['src/optipng/optim.c.xml', 'src/optipng/optipng.c.xml']
    FOLDS = 5
    TIMEOUT_MAKE = 20
    TIMEOUT_INST = 25
    TIMEOUT_COMPARE = 5
    APPROX_TIME = 355

    from benchmarks.png import INST_PATH_COLOR as INST_PATH, INSTS_COLOR as INSTS

    def my_init(self):
        self.program = OptipngProgram(self.proxify(self.PATH), {'target_files' : self.TARGETS})

    def my_setup(self, algo):
        self.program.timeout_make = self.TIMEOUT_MAKE
        self.program.timeout_inst = self.TIMEOUT_INST
        self.program.timeout_compare = self.TIMEOUT_COMPARE

        self.program.instances_folder = self.proxify(self.INST_PATH)
        self.program.instances = [[os.path.join(key, inst) for inst in self.INSTS[key]] for key in self.INSTS]
        self.program.optimization_level = 3

class Scenario_OptipngColor(Scenario_Optipng):
    SCENARIO_NAME = 'OptiPNG_Color'
    APPROX_TIME = 335
    from benchmarks.png import INST_PATH_COLOR as INST_PATH, INSTS_COLOR as INSTS

class Scenario_OptipngGray(Scenario_Optipng):
    SCENARIO_NAME = 'OptiPNG_Gray'
    APPROX_TIME = 165
    from benchmarks.png import INST_PATH_GREYSCALE as INST_PATH, INSTS_GREYSCALE as INSTS

class Scenario_OptipngBoth(Scenario_Optipng):
    SCENARIO_NAME = 'OptiPNG_Both'
    FOLDS = 10
    APPROX_TIME = 500
    from benchmarks.png import INST_PATH_COLOR, INSTS_COLOR
    from benchmarks.png import INST_PATH_GREYSCALE, INSTS_GREYSCALE

    def my_setup(self, algo):
        self.program.timeout_make = self.TIMEOUT_MAKE
        self.program.timeout_inst = self.TIMEOUT_INST
        self.program.timeout_compare = self.TIMEOUT_COMPARE

        self.program.instances_folder = os.path.dirname(self.proxify(self.INST_PATH_COLOR))
        self.proxify(self.INST_PATH_GREYSCALE)
        basedir_color = os.path.basename(self.INST_PATH_COLOR)
        insts_color = [[os.path.join(basedir_color, key, inst) for inst in self.INSTS_COLOR[key]] for key in self.INSTS_COLOR]
        basedir_gray = os.path.basename(self.INST_PATH_GREYSCALE)
        insts_gray = [[os.path.join(basedir_gray, key, inst) for inst in self.INSTS_GREYSCALE[key]] for key in self.INSTS_GREYSCALE]
        self.program.instances = insts_color + insts_gray
        self.program.optimization_level = 3

class Scenario_MoeaNsga(Scenario_Tevc):
    SCENARIO_NAME = 'XXX'
    PATH = 'code/moead-2007-edited'
    TARGETS = []
    FOLDS = 9
    APPROX_TIME = 999

    def my_init(self):
        self.program = MoeaNsgaProgram(self.proxify(self.PATH), {'target_files' : self.TARGETS})

class Scenario_Moea(Scenario_MoeaNsga):
    SCENARIO_NAME = 'MOEA'
    TARGETS = ['DMOEA/dmoeafunc.h.xml', 'common/recombination.h.xml']
    APPROX_TIME = 175

    def my_setup(self, algo):
        self.program.moea_algo = 1
        self.program.seeds = list(range(1, 6)) # 1, 2, ... 5
        self.program.timeout_instance = 10

class Scenario_Nsga(Scenario_MoeaNsga):
    SCENARIO_NAME = 'NSGA-II'
    TARGETS = ['NSGA2/nsga2func.h.xml', 'common/recombination.h.xml']
    APPROX_TIME = 875

    def my_setup(self, algo):
        self.program.moea_algo = 0
        self.program.seeds = list(range(1, 6)) # 1, 2, ... 5
        self.program.timeout_instance = 80

class Scenario_Moea11(Scenario_Moea):
    SCENARIO_NAME = 'MOEA-11'
    def my_setup(self, algo):
        super().my_setup(algo)
        self.program.distance_tolerance_ratio = 1.1

class Scenario_Moea15(Scenario_Moea):
    SCENARIO_NAME = 'MOEA-15'
    def my_setup(self, algo):
        super().my_setup(algo)
        self.program.distance_tolerance_ratio = 1.5

class Scenario_Nsga11(Scenario_Nsga):
    SCENARIO_NAME = 'NSGA-II-11'
    def my_setup(self, algo):
        super().my_setup(algo)
        self.program.distance_tolerance_ratio = 1.1

class Scenario_Nsga15(Scenario_Nsga):
    SCENARIO_NAME = 'NSGA-II-15'
    def my_setup(self, algo):
        super().my_setup(algo)
        self.program.distance_tolerance_ratio = 1.5

def get_scenario(name):
    scenario = None
    if name == 'satcit':
    #     return Scenario_MinisatCit1()
    # elif name == 'satcit2':
        return Scenario_MinisatCit2()
    elif name == 'satuniform':
        return Scenario_MinisatUniform()
    elif name == 'sat4jcit':
        return Scenario_Sat4jCit2()
    elif name == 'sat4juniform':
        return Scenario_Sat4jUniform()
    elif name == 'optipng':
        return Scenario_Optipng()
    elif name == 'optipngcolor':
        return Scenario_OptipngColor()
    elif name == 'optipnggray':
        return Scenario_OptipngGray()
    elif name == 'optipngboth':
        return Scenario_OptipngBoth()
    elif name == 'moea-11':
        return Scenario_Moea11()
    elif name == 'nsga-ii-11':
        return Scenario_Nsga11()
    elif name == 'moea-15':
        return Scenario_Moea15()
    elif name == 'nsga-ii-15':
        return Scenario_Nsga15()
    assert False, 'unknown scenario: {}'.format(name)

main.get_scenario = get_scenario

# ================================================================================

from mypyggi.algos import *

def get_algo(name):
    algo = None
    if name == 'dummy':
        algo = DummySearch()
        algo.config['nb_instances'] = None # use all instances
    elif name == 'valid':
        algo = ValidRanking()
        algo.config['nb_instances'] = None # use all instances
    elif re.search(r'^first', name):
        algo = FirstImprovement()
        m = re.search(r'first-(\d+)pb', name)
        if m:
            algo.config['nb_instances_perbin'] = int(m.group(1))
        else:
            algo.config['nb_instances_perbin'] = 2
    elif re.search(r'^best', name):
        algo = BestImprovement()
        m = re.search(r'best-(\d+)pb', name)
        if m:
            algo.config['nb_instances_perbin'] = int(m.group(1))
        else:
            algo.config['nb_instances_perbin'] = 2
    elif re.search(r'^tabu', name):
        algo = TabuSearch()
        m = re.search(r'tabu-(\d+)pb', name)
        if m:
            algo.config['nb_instances_perbin'] = int(m.group(1))
        else:
            algo.config['nb_instances_perbin'] = 2
    elif re.search(r'^rand', name):
        algo = RandomSearch()
        m = re.search(r'rand-(\d+)', name)
        if m:
            algo.config['horizon'] = int(m.group(1))
        algo.config['nb_instances_perbin'] = 2
    elif re.search(r'^gp', name):
        if re.search(r'gpc-', name):
            algo = GeneticProgrammingConcat()
        elif re.search(r'gp1p-', name):
            algo = GeneticProgramming1Point()
        elif re.search(r'gpuc-', name):
            algo = GeneticProgrammingUniformConcat()
        elif re.search(r'gpui-', name):
            algo = GeneticProgrammingUniformInter()
        algo.config['nb_instances_perbin'] = 1
        m = re.search(r'gp..?-(\d+)(r?)', name)
        if m:
            pop = int(m.group(1))
            algo.config['pop_size'] = pop
            algo.config['offspring_elitism'] = 0
            algo.config['offspring_crossover'] = math.ceil(0.5*pop)
            algo.config['offspring_mutation'] = math.floor(0.5*pop)
            if m.group(2) == 'r':
                algo.config['reassess'] = True
                algo.config['reassess_nb_instances_perbin'] = 4
    if algo is None:
        assert False, 'unknown algorithm: {}'.format(name)
    return algo

main.get_algo = get_algo

# ================================================================================

from main_base import *

if __name__ == "__main__":
    # process arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', type=str, default='satuniform')
    parser.add_argument('--step', type=str, default='check',)
    parser.add_argument('--algo', type=str, default='dummy')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--inst-seed', type=int, default=0)
    parser.add_argument('--replication', type=int, default=0)
    parser.add_argument('--patch', type=str, default='')
    args = parser.parse_args()

    if args.seed == -1:
        args.seed = random.randint(0, sys.maxsize)
    if args.inst_seed == -1:
        args.inst_seed = random.randint(0, sys.maxsize)

    # setup
    random.seed(args.inst_seed)
    scenario = main.get_scenario(args.scenario)
    if args.step == 'validation':
        algo = main.get_algo('valid')
        algo.debug_patch = main.eval_patch(scenario.program, args.patch)
    elif args.step == 'test' or args.step.startswith('assess'):
        algo = main.get_algo('dummy')
    else:
        algo = main.get_algo(args.algo)
    scenario.setup(args.step, algo, args.seed, args.replication, name=args.algo)

    # run
    random.seed(args.seed)
    main.run_scenario(scenario, algo, args)
