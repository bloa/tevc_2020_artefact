from abc import ABC, abstractmethod
import copy
import itertools
import random
import time

class Algorithm(ABC):
    def __init__(self):
        self.config = {}
        self.config['cache'] = True
        self.config['cache_maxsize'] = 40
        self.config['cache_keep'] = 0.2
        self.stats = {}
        self.stats['cache_hits'] = 0
        self.stats['cache_misses'] = 0
        self.stats['budget'] = 0
        self.report = {}
        self.report['initial_patch'] = None
        self.report['initial_fitness'] = None
        self.report['best_fitness'] = None
        self.report['best_patch'] = None
        self.report['stop'] = None
        self.stop = {}
        self.stop['wall'] = 10 # seconds
        self.stop['steps'] = 3
        self.stop['budget'] = None
        self.setup()
        self.cache_reset()
        # duplicate separate RNG for sampling instances
        self.inst_sample_random = random.Random()
        self.inst_sample_random.setstate(random.getstate())

    def setup(self):
        pass

    @abstractmethod
    def run(self):
        pass

    def sample_instances(self, k=None):
        full = [i for b in self.instance_bins for i in b]
        if k is None or not (0 < k < len(full)):
            return full
        else:
            tmp = [self.inst_sample_random.sample(b, k=len(b)) for b in self.instance_bins]
            tmp = itertools.zip_longest(*tmp)
            tmp = [i for t in tmp for i in list(t) if t is not None]
            tmp = tmp[:k]
            return [i for i in full if i in tmp]

    def evaluate_patch(self, patch, force=False, forget=False):
        if self.config['cache'] and not force:
            run = self.cache_get(patch)
            if run:
                return run
        run = self.program.evaluate_patch(patch)
        if self.config['cache'] and not forget:
            self.cache_set(patch, run)
        self.stats['budget'] += getattr(run, 'budget', 0) or 0
        return run

    def cache_get(self, patch):
        try:
            run = self.cache[patch]
            self.stats['cache_hits'] += 1
            if self.config['cache_maxsize'] > 0:
                self.cache_hits[patch] += 1
            return run
        except KeyError:
            self.stats['cache_misses'] += 1
            return None

    def cache_set(self, patch, run):
        msize = self.config['cache_maxsize']
        if msize > 0 and len(self.cache_hits) > msize:
            keep = self.config['cache_keep']
            hits = sorted(self.cache.keys(), key=lambda k: 999 if len(k) == 0 else self.cache_hits[k])
            for k in hits[:int(msize*(1-keep))]:
                del self.cache[k]
            self.cache_hits = { p: 0 for p in self.cache.keys()}
        if not patch in self.cache:
            self.cache_hits[patch] = 0
        self.cache[patch] = run

    def cache_copy(self, algo):
        self.cache = algo.cache
        self.cache_hits = algo.cache_hits

    def cache_reset(self):
        self.cache = {}
        self.cache_hits = {}

    def dominates(self, fit1, fit2):
        if fit1 is None:
            return False
        if fit2 is None:
            return True
        if isinstance(fit1, list):
            for x,y in zip(fit1, fit2):
                if x < y:
                    return True
                if x > y:
                    return False
            return False
        else:
            return fit1 < fit2

    def stopping_condition(self):
        if self.report['stop'] is not None:
            return True
        if self.stop['budget'] is not None:
            if self.stats['budget'] >= self.stop['budget']:
                self.report['stop'] = 'budget'
                return True
        if self.stop['wall'] is not None:
            now = time.time()
            if now >= self.stats['wallclock_start'] + self.stop['wall']:
                self.report['stop'] = 'time budget'
                return True
        if self.stop['steps'] is not None:
            if self.stats['steps'] >= self.stop['steps']:
                self.report['stop'] = 'step budget'
                return True
        return False
