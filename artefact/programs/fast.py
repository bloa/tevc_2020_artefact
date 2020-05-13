import os
import random
import re
import subprocess
import sys
import time

from pyggi.base import AbstractProgram, RunResult, AbstractEdit
from pyggi.utils import Logger

FAST_MAX = 100000

class FastEdit(AbstractEdit):
    def __init__(self):
        self.rand = int(random.random()*FAST_MAX)

    def __str__(self):
        return str(self.rand)

    def apply(self): pass
    def create(self): pass
    def domain(self): pass


class FastProgram(AbstractProgram):
    def __init__(self):
        self.name = 'FAST'
        self.timestamp = str(int(time.time()))
        self.logger = Logger(self.name + '_' + self.timestamp)
        self.base_fitness = 1

    def __str__(self):
        return "{}({})".format(self.__class__.__name__, self.name)

    def evaluate_patch(self, patch):
        r = RunResult('SUCCESS')
        if len(patch) == 0 or random.random() < 0.5:
            last = FAST_MAX
            xs = [e.rand for e in patch.edit_list]
            for i, x in enumerate(xs):
                if x >= last:
                    r.status = 'WRONG'
                    break
                else:
                    last = x
            else:
                if len(xs) > 0:
                    r.fitness = round((FAST_MAX - xs[len(xs)//3] + xs[2*len(xs)//3])/len(xs), 3)
                else:
                    r.fitness = FAST_MAX
        else:
            r.status = 'FAIL'
        return r

    def create_edit(self):
        return FastEdit()

    @classmethod
    def get_engine(cls, file_name): pass
    def create_tmp_variant(self): pass
    def remove_tmp_variant(self): pass
    def diff(self, patch): return ''

