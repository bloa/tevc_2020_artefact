#!/usr/bin/python

import ast
import random
import re
import sys

import pyggi
from pyggi.base import Patch
from pyggi.tree import StmtReplacement, StmtInsertion, StmtDeletion

def get_scenario(name):
    assert False, 'not implemented (imported the wrong file?)'

def get_algo(name):
    assert False, 'not implemented (imported the wrong file?)'

def eval_edit(s):
    match = re.search(r"^(\w+)\((.+)\)$", s)
    cls = getattr(sys.modules[__name__], match.group(1))
    args = ast.literal_eval(match.group(2))
    edit = cls(**args)
    return edit

def eval_patch(program, string):
    patch = Patch(program)
    for s in string.split(' | '):
        patch.add(eval_edit(s))
    return patch

def run_scenario(scenario, algo, args):
    try:
        scenario.enter()

        program = scenario.program
        logger = program.logger
        logger.debug('ARGS: %s', repr(args))

        try:
            # best patch
            if args.patch != '':
                algo.report['best_patch'] = eval_patch(program, args.patch)

            # training / validation / test step
            random.seed(args.seed)
            logger.debug('ALL_INSTANCES: %s', repr(algo.program.instances))
            try:
                algo.run()
            except KeyboardInterrupt:
                algo.report['stop'] = 'keyboard interrupt'

            # log results
            logger.debug(algo.config)
            logger.debug(algo.stats)
            logger.debug(algo.report)
            logger.info('INIT_FITNESS: %s', str(algo.report['initial_fitness']))
            logger.info('BEST_FITNESS: %s', str(algo.report['best_fitness']))
            if algo.report['best_patch'] is not None:
                initial_fitness = algo.report['initial_fitness']
                if isinstance(initial_fitness, list):
                    r = [100*b/f for b,f in zip(algo.report['best_fitness'], initial_fitness)]
                else:
                    r = 100*algo.report['best_fitness']/initial_fitness
                    logger.info('FINAL: %.3f%%', r)
                    logger.info('BEST_PATCH: %s', str(algo.report['best_patch']))

                if len(algo.report['best_patch']) > 0:
                    logger.debug(program.diff(algo.report['best_patch']))

        except Exception as e:
            logger.exception('Exception at top level?!', exc_info=sys.exc_info())

        finally:
            program.remove_tmp_variant()

    finally:
        scenario.exit()

