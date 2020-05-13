import argparse
import multiprocessing
import os
import re
import sys
import time

import automate_base as automate
from main_tevc import *

def time_run(step, scenario, patch=None):
    if step == 'analyse':
        return scenario.APPROX_TIME*10
    elif step == 'check':
        return scenario.APPROX_TIME/scenario.FOLDS*10
    elif step == 'training':
        return 1.1*(100*scenario.APPROX_TIME/scenario.FOLDS)
    elif step == 'validation':
        return (1+1+2*(patch.count("|")+1))*scenario.APPROX_TIME/scenario.FOLDS
    elif step in ['test', 'assess-gi-valid', 'assess-gp-valid', 'assess-gp-test']:
        return (1+1+1)*scenario.APPROX_TIME/scenario.FOLDS
    elif step in ['assess-gi-training', 'assess-gp-training']:
        return (1+1+1)*(scenario.FOLDS-2)*scenario.APPROX_TIME/scenario.FOLDS
    elif step in ['assess-gi-all', 'assess-gp-all']:
        return (1+1+1)*scenario.APPROX_TIME

algos = []
algos.append('rand-1')
algos.append('rand-2')
algos.append('rand-5')
algos.append('rand-10')
algos.append('gpc-100')
algos.append('gp1p-100')
algos.append('gpuc-100')
algos.append('gpui-100')
algos.append('gpc-100r')
algos.append('gp1p-100r')
algos.append('gpuc-100r')
algos.append('gpui-100r')
algos.append('first-1pb')
algos.append('best-1pb')
algos.append('tabu-1pb')
algos.append('first-2pb')
algos.append('best-2pb')
algos.append('tabu-2pb')

automate.time_run = time_run
automate.algos = algos
automate.scenarios = [
    Scenario_MinisatCit2,
    Scenario_MinisatUniform,
    # Scenario_Sat4jCit2,
    Scenario_Sat4jUniform,
    Scenario_OptipngColor,
    Scenario_OptipngGray,
    Scenario_OptipngBoth,
    Scenario_Moea11,
    Scenario_Nsga11,
    # Scenario_Moea15,
    # Scenario_Nsga15,
]
automate.main_seed = 123

if __name__ == "__main__":
    # process arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--step', type=str, default='check',
                        choices=['analyse', 'check', 'training', 'validation', 'test', 'assess-gi-valid', 'assess-gp-valid', 'assess-gp-test', 'assess-gi-training', 'assess-gp-training', 'assess-gi-all', 'assess-gp-all'])
    parser.add_argument('--seed', type=int, default=123)
    parser.add_argument('--context', type=str, default='')
    parser.add_argument('--cores', type=int, default=0)
    parser.add_argument('--delay', type=int, default=2)
    parser.add_argument('--run', default=False, action='store_true')
    parser.add_argument('--force', default=False, action='store_true')
    args = parser.parse_args()

    if args.cores == 0: # auto
        if args.step == 'test' or args.step.startswith('assess'):
            args.cores = 1
        else:
            args.cores = 4
    automate.dwim(args, automate.scenarios, automate.algos, args.cores, entry='./main_tevc.py')

