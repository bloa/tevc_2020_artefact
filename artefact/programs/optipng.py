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

class OptipngProgram(MytreeProgram):
    @classmethod
    def get_engine(cls, file_name):
        return SrcmlEngine

    def load_config(self, path, config):
        config = config if config is not None else {}
        self.target_files = config.get('target_files')
        self.instances = []
        self.instances_folder = None
        self.truth_table = {}
        self.base_fitness = None
        self.timeout_make = 5
        self.timeout_inst = 15
        self.timeout_compare = 3
        self.pixel_tolerance = 0
        self.optimization_level = 4

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
            os.chdir(os.path.join(self.tmp_path, 'src', 'optipng'))
            cmd = ['make']
            return_code, stdout, stderr, elapsed_time = self.exec_cmd(cmd, timeout=self.timeout_make)
            r.runtime_compile = elapsed_time or self.timeout_make
            self.compute_valid_make(r, return_code, None, None, elapsed_time, self.timeout_make)
            if r.status is not None:
                if self.base_fitness is None:
                    self.logger.debug('FAIL ON FIRST INSTANCE')
                    self.debug_exec(' '.join(cmd), r.status, return_code, stdout, stderr, elapsed_time)
                return self.with_misc(r, start)
            os.chdir('../..')

            # run it
            outputs = []
            for (i, inst) in enumerate(self.instances):
                r.inst = inst
                r.inst_id = i+1
                cmd = [os.path.join('.', 'src', 'optipng', 'optipng'), os.path.join(self.instances_folder, inst), '-o', str(self.optimization_level), '-out', 'out.png', '-clobber']
                cmd = ['perf', 'stat', '-e', 'instructions', *cmd]
                return_code, stdout, stderr, elapsed_time = self.exec_cmd(cmd, timeout=self.timeout_inst)
                r.runtime += elapsed_time or self.timeout_inst
                self.compute_valid(r, return_code, None, stderr, elapsed_time, self.timeout_inst)
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
                r.fitness = None

        except Exception as e:
            r.status = 'WRAPPER_ERROR'
            r.error = str(e)
            return self.with_misc(r, start)

        finally:
            os.chdir(cwd)

        del r.inst
        del r.inst_id
        r.status = 'SUCCESS'
        r.fitness = round(sum(outputs), 3)
        return self.with_misc(r, start)

    def compute_valid_make(self, result, return_code, stdout, stderr, elapsed_time, timeout):
        if elapsed_time is not None and elapsed_time > timeout:
            result.status = 'COMPILE_TIMEOUT'
        elif return_code is None or return_code < 0:
            result.status = 'COMPILE_KILLED'
        elif return_code > 1:
            result.status = 'COMPILE_ERROR'

    def compute_valid(self, result, return_code, stdout, stderr, elapsed_time, timeout):
        if elapsed_time is not None and elapsed_time > timeout:
            result.status = 'INSTANCE_TIMEOUT'
        elif return_code is None or return_code < 0:
            result.status = 'INSTANCE_KILLED'
        elif return_code > 0:
            result.status = 'RUNTIME_ERROR'
        if result.status is not None:
            return
        cmd = ['compare', '-metric', 'MSE', os.path.join(self.instances_folder, result.inst), 'out.png', 'diff.png']
        return_code, _, stderr2, _ = self.exec_cmd(cmd, timeout=self.timeout_compare)
        if return_code is None:
            result.status = 'COMPARE_TIMEOUT'
        elif return_code != 0:
            result.status = 'COMPARE_ERROR'
        else:
            m = re.search(r'\((.*)\)', stderr2.decode('ascii'))
            if m is None:
                result.status = 'COMPARE_FAIL'
            else:
                f = float(m.group(1))
                if f > self.pixel_tolerance:
                    result.status = 'COMPARE_FAIL'
        if result.status is not None:
            return
        size = os.path.getsize('out.png')
        try:
            if size > self.truth_table[result.inst]:
                result.status = 'OUTPUT_ERROR'
        except KeyError:
            m = re.search(r'Output file size.*\((\d+)', stderr.decode('ascii'))
            decrease = int(m.group(1)) if m is not None else 0
            self.logger.debug('TRUTH: {} is {} bytes (-{}, -{}%) in {}'.format(result.inst, size, decrease, round(100*decrease/(size+decrease), 2), elapsed_time))
            self.truth_table[result.inst] = size

    def compute_fitness(self, result, return_code, stdout, stderr, elapsed_time):
        try:
            m = re.search(r'^\s*([0-9,]+)\s+instructions(?::u)?', stderr.decode('ascii'), re.M)
            if m:
                result.fitness = int(m.group(1).replace(',' , ''))
            else:
                result.status = 'PARSE_ERROR'
        except UnicodeDecodeError:
            result.status = 'OUTPUT_ERROR'
