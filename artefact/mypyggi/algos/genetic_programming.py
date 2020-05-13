import copy
import math
import random
import time

from pyggi.base import Patch

from . import Algorithm

class GeneticProgramming(Algorithm):
    def setup(self):
        self.name = 'Genetic Programming'
        self.config['warmup'] = 3
        self.config['horizon'] = 1
        self.config['pop_size'] = 10
        self.config['offspring_elitism'] = 0.1
        self.config['offspring_crossover'] = 0.5
        self.config['offspring_mutation'] = 0.4
        self.config['rolling'] = True
        self.config['nb_instances'] = None
        self.config['reassess'] = False
        self.config['reassess_nb_instances'] = None
        self.stats['gen'] = 0

    def run(self):
        logger = self.program.logger

        # setup instances
        self.program.instances = self.sample_instances(self.config['nb_instances'])
        logger.debug('INSTANCES: %s', repr(self.program.instances))
        if self.config['reassess']:
            # seed magic to preserve randomness
            rng_state = self.inst_sample_random.getstate()
            self.inst_sample_random.seed(self.inst_sample_random.randrange(2<<31-1))
            self.program.reassess_instances = self.sample_instances(self.config['reassess_nb_instances'])
            logger.debug('REASSESS_INSTANCES: %s', repr(self.program.reassess_instances))
            self.inst_sample_random.setstate(rng_state)

        # warmup
        logger.info('==== WARMUP ====')
        empty_patch = Patch(self.program)
        for i in range(self.config['warmup']+1, 0, -1):
            self.program.base_fitness = None
            self.program.truth_table = {}
            run = self.evaluate_patch(empty_patch, force=True)
            logger.debug(run)
            l = 'WARM' if i > 1 else 'INITIAL'
            logger.info("{}\t{}\t{}".format(l, run.status, run.fitness))
            assert run.status == 'SUCCESS', 'initial solution has failed'
        self.report['initial_fitness'] = run.fitness
        self.report['best_fitness'] = run.fitness
        self.report['best_patch'] = empty_patch
        if self.config['reassess']:
            bak_initial_fitness = self.report['initial_fitness']
            bak_instances = self.program.instances
            self.program.instances = self.program.reassess_instances
            self.program.base_fitness = None
            run = self.evaluate_patch(empty_patch, force=True, forget=True)
            logger.debug(run)
            logger.info("INITIAL\t{}\t{}".format(run.status, run.fitness))
            assert run.status == 'SUCCESS', 'initial solution has failed'
            self.report['reassess_initial_fitness'] = run.fitness
            self.report['best_fitness'] = run.fitness
            self.program.base_fitness = bak_initial_fitness
            self.program.instances = bak_instances

        # start!
        self.stats['steps'] = 0
        self.stats['wallclock_start'] = time.time()
        logger.info('==== {} ===='.format(self.name))

        try:
            # initial pop
            pop = dict()
            local_best = None
            local_best_fitness = None
            while len(pop) < self.config['pop_size']:
                dist = 1 + int(random.random()*self.config['horizon']-1)
                sol = copy.deepcopy(empty_patch)
                for _ in range(dist):
                    self.mutate(sol)
                if sol in pop:
                    continue
                run = self.evaluate_patch(sol)
                h = [self.stats['gen'], self.stats['steps']+1, run.status, ' ', run.fitness, sol]
                if run.status == 'SUCCESS':
                    if self.dominates(run.fitness, local_best_fitness):
                        self.program.logger.debug(self.program.diff(sol))
                        local_best_fitness = run.fitness
                        local_best = sol
                        h[3] = '+'
                logger.debug(run)
                logger.info('{}\t{}\t{}\t{}{}\t{}'.format(*h))
                pop[sol] = run
                self.stats['steps'] += 1
            if local_best is not None:
                if self.config['reassess']:
                    bak_initial_fitness = self.report['initial_fitness']
                    bak_instances = self.program.instances
                    self.program.instances = self.program.reassess_instances
                    self.program.base_fitness = self.report['reassess_initial_fitness']
                    run = self.evaluate_patch(local_best, force=True, forget=True)
                    h = [self.stats['gen']+1, self.stats['steps']+1, run.status, ' ', run.fitness, local_best]
                    if run.status == 'SUCCESS':
                        if self.dominates(run.fitness, self.report['best_fitness']):
                            self.program.logger.debug(self.program.diff(local_best))
                            self.report['best_fitness'] = run.fitness
                            self.report['best_patch'] = local_best
                            h[3] = '*'
                    logger.debug(run)
                    logger.info('{}\t{}\t{}\t{}{}\t{}'.format(*h))
                    self.stats['steps'] += 1
                    self.program.instances = bak_instances
                    self.program.base_fitness = bak_initial_fitness
                else:
                    self.report['best_fitness'] = local_best_fitness
                    self.report['best_patch'] = local_best

            # main loop
            while not self.stopping_condition():
                offsprings = list()
                parents = self.select(pop)
                # elitism
                copy_parents = copy.deepcopy(parents)
                for parent in copy_parents[:self.config['offspring_elitism']]:
                    offsprings.append(parent)
                # crossover
                copy_pop = copy.deepcopy(self.filter(pop))
                copy_parents = copy.deepcopy(parents)
                for parent in copy_parents[:self.config['offspring_crossover']]:
                    sol = random.sample(copy_pop, 1)[0]
                    if random.random() > 0.5:
                        sol = self.crossover(parent, sol)
                    else:
                        sol = self.crossover(sol, parent)
                    offsprings.append(sol)
                # mutation
                copy_parents = copy.deepcopy(parents)
                for parent in copy_parents[:self.config['offspring_mutation']]:
                    self.mutate(parent)
                    offsprings.append(parent)
                # regrow
                while len(offsprings) < self.config['pop_size']:
                    dist = 1 + int(random.random()*self.config['horizon']-1)
                    sol = copy.deepcopy(empty_patch)
                    for _ in range(dist):
                        self.mutate(sol)
                    if sol in pop:
                        continue
                    offsprings.append(sol)
                # update instances
                if self.config['rolling']:
                    self.program.instances = self.sample_instances(self.config['nb_instances'])
                    logger.debug('INSTANCES: %s', repr(self.program.instances))
                    self.program.base_fitness = None
                    self.program.truth_table = {}
                    self.cache_reset()
                    run = self.evaluate_patch(empty_patch)
                    logger.debug(run)
                    logger.info("{}\t{}\t{}".format('INITIAL', run.status, run.fitness))
                    self.report['initial_fitness'] = run.fitness
                    if not self.config['reassess']:
                        self.report['best_fitness'] = run.fitness
                        self.report['best_patch'] = empty_patch
                # replace
                pop.clear()
                local_best = None
                local_best_fitness = None
                for sol in offsprings:
                    if self.stopping_condition():
                        break
                    run = self.evaluate_patch(sol)
                    h = [self.stats['gen']+1, self.stats['steps']+1, run.status, ' ', run.fitness, sol]
                    if run.status == 'SUCCESS':
                        if self.dominates(run.fitness, local_best_fitness):
                            self.program.logger.debug(self.program.diff(sol))
                            local_best = sol
                            local_best_fitness = run.fitness
                            h[3] = '+'
                    logger.debug(run)
                    logger.info('{}\t{}\t{}\t{}{}\t{}'.format(*h))
                    pop[sol] = run
                    self.stats['steps'] += 1
                if local_best is not None:
                    if self.config['reassess']:
                        bak_initial_fitness = self.report['initial_fitness']
                        bak_instances = self.program.instances
                        self.program.instances = self.program.reassess_instances
                        self.program.base_fitness = self.report['reassess_initial_fitness']
                        run = self.evaluate_patch(local_best, force=True, forget=True)
                        h = [self.stats['gen']+1, self.stats['steps']+1, run.status, ' ', run.fitness, local_best]
                        if run.status == 'SUCCESS':
                            if self.dominates(run.fitness, self.report['best_fitness']):
                                self.program.logger.debug(self.program.diff(local_best))
                                self.report['best_fitness'] = run.fitness
                                self.report['best_patch'] = local_best
                                h[3] = '*'
                        logger.debug(run)
                        logger.info('{}\t{}\t{}\t{}{}\t{}'.format(*h))
                        self.stats['steps'] += 1
                        self.program.instances = bak_instances
                        self.program.base_fitness = bak_initial_fitness
                    else:
                        self.report['best_fitness'] = local_best_fitness
                        self.report['best_patch'] = local_best
                # next
                self.stats['gen'] += 1

        finally:
            # the end
            if self.config['reassess']:
                self.report['initial_fitness'] = self.report['reassess_initial_fitness']
                del self.report['reassess_initial_fitness']
            self.stats['wallclock_end'] = time.time()
            logger.info('==== END ====')

    def mutate(self, patch):
        if len(patch) > 0 and random.random() < 0.5:
            patch.remove(random.randrange(0, len(patch)))
        else:
            patch.add(self.program.create_edit())

    def crossover(self, sol1, sol2):
        c = copy.deepcopy(sol1)
        for edit in sol2.edit_list:
            c.add(edit)
        return c

    def filter(self, pop):
        tmp = {sol for sol in pop if pop[sol].status == 'SUCCESS'}
        tmp = {sol for sol in tmp if pop[sol].percentage < 150}
        return tmp

    def select(self, pop):
        """ returns possible parents ordered by fitness """
        tmp = self.filter(pop)
        tmp = sorted(tmp, key=lambda sol: pop[sol].fitness)
        return tmp

class GeneticProgrammingConcat(GeneticProgramming):
    def setup(self):
        super().setup()
        self.name = 'Genetic Programming (Concat)'

    def crossover(self, sol1, sol2):
        c = copy.deepcopy(sol1)
        for edit in sol2.edit_list:
            c.add(edit)
        return c

class GeneticProgramming1Point(GeneticProgramming):
    def setup(self):
        super().setup()
        self.name = 'Genetic Programming (1-point)'

    def crossover(self, sol1, sol2):
        c = Patch(self.program)
        k1 = random.randint(0, len(sol1))
        k2 = random.randint(0, len(sol2))
        for edit in sol1.edit_list[:k1]:
            c.add(edit)
        for edit in sol2.edit_list[k2:]:
            c.add(edit)
        return c

class GeneticProgramming2Point(GeneticProgramming):
    def setup(self):
        super().setup()
        self.name = 'Genetic Programming (2-point)'

    def crossover(self, sol1, sol2):
        c = Patch(self.program)
        k1 = random.randint(0, len(sol1))
        k2 = random.randint(0, len(sol1))
        k3 = random.randint(0, len(sol2))
        k4 = random.randint(0, len(sol2))
        for edit in sol1.edit_list[:min(k1, k2)]:
            c.add(edit)
        for edit in sol2.edit_list[min(k3, k4):max(k3, k4)]:
            c.add(edit)
        for edit in sol1.edit_list[max(k1, k2):]:
            c.add(edit)
        return c

class GeneticProgrammingUniformConcat(GeneticProgramming):
    def setup(self):
        super().setup()
        self.name = 'Genetic Programming (uniform+concatenation)'
        self.config['uniform_rate'] = 0.5

    def crossover(self, sol1, sol2):
        c = Patch(self.program)
        for edit in sol1.edit_list:
            if random.random() > self.config['uniform_rate']:
                c.add(edit)
        for edit in sol2.edit_list:
            if random.random() > self.config['uniform_rate']:
                c.add(edit)
        if len(c) == 0:
            sol3, sol4 = [sol1, sol2] if random.random() > 0.5 else [sol2, sol1]
            if len(sol3) > 0:
                c.add(random.choice(sol3.edit_list))
            elif len(sol4) > 0:
                c.add(random.choice(sol4.edit_list))
        return c

class GeneticProgrammingUniformInter(GeneticProgramming):
    def setup(self):
        super().setup()
        self.name = 'Genetic Programming (uniform+interleaved)'
        self.config['uniform_rate'] = 0.5

    def crossover(self, sol1, sol2):
        c = Patch(self.program)
        l1 = [(i/len(sol1), 0) for i in sorted(random.sample(range(len(sol1)), math.ceil(len(sol1)*self.config['uniform_rate'])))]
        l2 = [(i/len(sol2), 1) for i in sorted(random.sample(range(len(sol2)), math.ceil(len(sol2)*self.config['uniform_rate'])))]
        for (x, k) in sorted(l1+l2):
            sol = [sol1, sol2][k]
            edit = sol.edit_list[int(x*len(sol))]
            c.add(edit)
        if len(c) == 0:
            sol3, sol4 = [sol1, sol2] if random.random() > 0.5 else [sol2, sol1]
            if len(sol3) > 0:
                c.add(random.choice(sol3.edit_list))
            elif len(sol4) > 0:
                c.add(random.choice(sol4.edit_list))
        return c
