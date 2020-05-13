import os
import random
import re
import subprocess
import sys
import time

from pyggi.base import Patch, AbstractProgram, RunResult
from pyggi.tree import XmlEngine

from mypyggi.programs import SrcmlEngine
from mypyggi.programs import MytreeProgram

class MoeaNsgaProgram(MytreeProgram):
    @classmethod
    def get_engine(cls, file_name):
        return SrcmlEngine

    def load_config(self, path, config):
        config = config if config is not None else {}
        self.target_files = config.get('target_files')
        self.instances = [str(k) for k in range(0, 9)]
        self.seeds = list(range(1, 11)) # 1, 2, ... 10
        self.truth_table = {}
        self.base_fitness = None
        self.timeout_make = 5
        self.timeout_inst = 100
        self.timeout_compare = 1
        self.moea_algo = 1 # 0: NSGA-II  1: MOEA
        self.distance_tolerance_ratio = 1.5

    def evaluate_patch(self, patch):
        start = time.time()
        cwd = os.getcwd()
        self.apply(patch)
        try:
            r = RunResult(None)
            r.walltime_apply = round(time.time() - start, 3)
            r.runtime_compile = 0
            r.runtime = 0

            # compile it
            os.chdir(os.path.join(self.tmp_path))
            env = dict(os.environ, MROOT='..', CFLAGS='-fpermissive')
            cmd = ['g++', 'main_moea.cpp', '-o', 'main_moea']
            return_code, stdout, stderr, elapsed_time = self.exec_cmd(cmd, timeout=self.timeout_make, env=env)
            r.runtime_compile = elapsed_time or self.timeout_make
            self.compute_valid_make(r, return_code, None, None, None)
            if r.status is not None:
                if self.base_fitness is None:
                    self.logger.debug('FAIL ON FIRST INSTANCE')
                    self.debug_exec(' '.join(cmd), r.status, return_code, stdout, stderr, elapsed_time)
                return self.with_misc(r, start)

            # run it
            outputs = []
            outputs_inst = []
            outputs_inst_ref = []
            for (i, inst) in enumerate(self.instances):
                for seed in self.seeds:
                    r.inst = '{}+{}'.format(inst, seed)
                    r.inst_id = i+1
                    cmd = [os.path.join('.', 'main_moea'), str(inst), str(seed), str(self.moea_algo), '1']
                    cmd = ['perf', 'stat', '-e', 'instructions', *cmd]
                    return_code, stdout, stderr, elapsed_time = self.exec_cmd(cmd, timeout=self.timeout_inst)
                    r.runtime += elapsed_time or self.timeout_inst
                    r.cmd = cmd
                    self.compute_valid(r, return_code, None, None, elapsed_time)
                    if r.status is not None:
                        if self.base_fitness is None:
                            self.logger.debug('FAIL ON FIRST INSTANCE')
                            self.debug_exec(' '.join(cmd), r.status, return_code, stdout, stderr, elapsed_time)
                        return self.with_misc(r, start)
                    self.compute_fitness(r, return_code, None, stderr, elapsed_time)
                    if r.status is not None:
                        if self.base_fitness is None:
                            self.logger.debug('FAIL ON FIRST INSTANCE')
                            self.debug_exec(' '.join(cmd), r.status, return_code, stdout, stderr, elapsed_time)
                        return self.with_misc(r, start)
                    outputs.append(r.fitness)
                    outputs_inst.append(r.inst_fitness)
                    outputs_inst_ref.append(r.inst_fitness_ref)
                    r.fitness = None
                    del r.inst_fitness
                    del r.inst_fitness_ref

        except Exception as e:
            r.status = 'WRAPPER_ERROR'
            r.error = str(e)
            return self.with_misc(r, start)

        finally:
            os.chdir(cwd)

        del r.inst
        del r.inst_id
        del r.cmd
        r.inst_fitness = round(sum(outputs_inst), 6)
        r.inst_fitness_ref = round(sum(outputs_inst_ref), 6)
        if r.inst_fitness > self.distance_tolerance_ratio*r.inst_fitness_ref:
            r.status = 'OUTPUT_BAD'
        else:
            r.status = 'SUCCESS'
            r.fitness = round(sum(outputs), 3)
        return self.with_misc(r, start)

    def compute_valid_make(self, result, return_code, stdout, stderr, elapsed_time):
        if return_code is None:
            result.status = 'COMPILE_TIMEOUT'
        elif return_code > 1:
            result.status = 'COMPILE_ERROR'

    def compute_valid(self, result, return_code, stdout, stderr, elapsed_time):
        if return_code is None:
            result.status = 'INSTANCE_TIMEOUT'
            return
        cmd = result.cmd
        cmd[-1] = '0'
        return_code, stdout2, _, _ = self.exec_cmd(cmd, timeout=self.timeout_compare)
        if return_code is None:
            result.status = 'COMPARE_TIMEOUT'
        elif return_code != 0:
            result.status = 'COMPARE_ERROR'
        else:
            m = re.search(r'Final reassess: (.*)', stdout2.decode('ascii'))
            if m is None:
                result.status = 'COMPARE_FAIL'
            elif m.group(1) == '1e+10':
                result.status = 'COMPARE_FAIL'
            else:
                result.inst_fitness = float(m.group(1))
        if result.status is not None:
            return
        try:
            result.inst_fitness_ref = self.truth_table[result.inst]
        except KeyError:
            self.logger.debug('TRUTH: {} is {} in {}'.format(result.inst, result.inst_fitness, elapsed_time))
            self.truth_table[result.inst] = result.inst_fitness
            result.inst_fitness_ref = result.inst_fitness


    def compute_fitness(self, result, return_code, stdout, stderr, elapsed_time):
        try:
            m = re.search(r'^\s*([0-9,]+)\s+instructions(?::u)?', stderr.decode('ascii'), re.M)
            if m:
                result.fitness = int(m.group(1).replace(',' , ''))
            else:
                result.status = 'PARSE_ERROR'
        except UnicodeDecodeError:
            result.status = 'OUTPUT_ERROR'
