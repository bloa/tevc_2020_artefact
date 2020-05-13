import copy
import random
import time

from pyggi.base import Patch

from . import Algorithm

class Cleaner(Algorithm):
    def setup(self):
        self.name = 'Cleaner'

    def run(self):
        logger = self.program.logger

        # start!
        self.stats['steps'] = 0
        self.stats['neighbours'] = 0
        self.stats['wallclock_start'] = time.time()
        logger.info('==== {} ===='.format(self.name))

        try:
            # initial fitness
            empty_patch = Patch(self.program)
            current_patch = empty_patch
            current_fitness = None
            if self.report['initial_fitness'] is None:
                for i in range(self.config['warmup']+1, 0, -1):
                    run = self.evaluate_patch(empty_patch, force=True)
                    l = 'WARM' if i > 1 else 'INITIAL'
                    logger.info("{}\t{}\t{}".format(l, run.status, run.fitness))
                    assert run.status == 'SUCCESS', 'initial solution has failed'
                    current_fitness = run.fitness
            self.report['best_patch'] = current_patch
            self.report['best_fitness'] = current_fitness
            self.report['initial_fitness'] = current_fitness
            self.program.base_fitness = current_fitness

            # main loop
            while not self.stopping_condition():
                current_patch, current_fitness = self.explore(current_patch, current_fitness)

        finally:
            # the end
            self.stats['wallclock_end'] = time.time()
            logger.info('==== END ====')

    def mutate(self, patch, force_grow=False):
        for _ in range(random.randint(1, self.config['horizon'])):
            if not force_grow and len(patch) > 0 and random.random() < self.config['delete_prob']:
                patch.remove(random.randrange(0, len(patch)))
            else:
                patch.add(self.program.create_edit())

    def check_if_trapped(self):
        if self.config['max_neighbours'] is None:
            return
        if self.stats['neighbours'] < self.config['max_neighbours']:
            return
        if self.config['trapped_strategy'] == 'fail':
            self.report['stop'] = 'trapped'
        # elif self.config['trapped_strategy'] == 'continue':
        #     pass
        # else:
        #     assert(False, 'unknown strategy: {}'.format(self.config['trapped_strategy']))
