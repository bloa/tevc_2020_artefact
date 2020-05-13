import os
import random
import time

from pyggi.base import AbstractProgram
from pyggi.tree import StmtReplacement, StmtInsertion, StmtDeletion, StmtMoving
from pyggi.utils import Logger

from .srcml import SrcmlEngine

class MytreeProgram(AbstractProgram):
    @classmethod
    def get_engine(cls, file_name):
        return SrcmlEngine

    def setup(self):
        self.create_tmp_variant = super().create_tmp_variant
        for h in list(self.logger._logger.handlers):
            self.logger._logger.removeHandler(h)

    @property
    def tmp_path(self):
        if os.getenv("JOB_ID") is not None:
            a = [self.name, os.getenv("JOB_ID")+'_'+self.name]
        else:
            a = [self.name, self.timestamp]

        return os.path.join(self.__class__.TMP_DIR, *a)

    def create_tmp_variant(self):
        # we want to prevent the very first tmp_variant...
        pass

    def create_edit(self):
        operator = random.choice(self.possible_edits)
        # ensure coherent edits
        while True:
            try:
                edit = operator.create(self)
                if edit.ingredient:
                    target_file, target_point = edit.target
                    ingredient_file, ingredient_point = edit.ingredient
                    target_tag = self.contents[target_file].find(self.modification_points[target_file][target_point]).tag
                    ingredient_tag = self.contents[ingredient_file].find(self.modification_points[ingredient_file][ingredient_point]).tag
                    if target_tag == ingredient_tag:
                        break
            except AttributeError:
                break
        return edit

    def with_misc(self, result, start):
        result.walltime = round(time.time() - start, 3)
        result.budget = result.runtime_compile + result.runtime
        if result.fitness is not None:
            if self.base_fitness is None:
                self.base_fitness = result.fitness
                result.percentage = round(100.0, 2)
            else:
                result.percentage = round(100*result.fitness/self.base_fitness, 2)
        result.runtime_compile = round(result.runtime_compile, 3)
        result.runtime = round(result.runtime, 3)
        return result

    def debug_exec(self, cmd, status, return_code, stdout, stderr, elapsed_time):
        self.logger.debug('CMD: %s', repr(cmd))
        self.logger.debug('STATUS: %s', str(status))
        self.logger.debug('CODE: %s', str(return_code))
        self.logger.debug('STDOUT: %s', str(stdout))
        self.logger.debug('STDERR: %s', str(stderr))
        self.logger.debug('TIME: %s', str(elapsed_time))
