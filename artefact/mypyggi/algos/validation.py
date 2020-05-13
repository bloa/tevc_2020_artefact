import copy
import itertools
import random
import time

from pyggi.base import Patch

from . import LocalSearch

class ValidSearch(LocalSearch):
    def clean_patch(self, patch):
        cleaned = copy.deepcopy(patch)
        cleaned_diff = self.program.diff(cleaned)
        for (k,edit) in reversed(list(enumerate(cleaned.edit_list))):
            tmp = copy.deepcopy(cleaned)
            del tmp.edit_list[k]
            if self.program.diff(tmp) == cleaned_diff:
                del cleaned.edit_list[k]
                cleaned_diff = self.program.diff(cleaned)
        return cleaned

class ValidSingle(ValidSearch):
    def setup(self):
        super().setup()
        self.name = 'Validation Single'
        self.debug_patch = None

    def explore(self, current_patch, current_fitness):
        assert self.debug_patch is not None
        cleaned_patch = self.clean_patch(self.debug_patch)
        self.program.logger.debug('CLEAN_PATCH: {}'.format(str(cleaned_patch)))
        self.program.logger.debug('CLEAN_SIZE: %d (was %d)', len(cleaned_patch), len(self.debug_patch))
        self.report['best_fitness'] = None
        self.report['best_patch'] = None

        for edit in cleaned_patch.edit_list:
            # move
            patch = Patch(self.program)
            patch.add(edit)

            # compare
            run = self.evaluate_patch(patch)
            h = [self.stats['steps']+1, run.status, ' ', run.fitness, patch]
            if run.status == 'SUCCESS':
                accept = True
                if self.dominates(run.fitness, self.report['best_fitness']):
                    self.report['best_fitness'] = run.fitness
                    self.report['best_patch'] = patch
                    h[2] = '*'

            # log
            self.program.logger.debug(self.program.diff(patch))
            self.program.logger.debug(run)
            self.program.logger.info('{}\t{}\t{}{}\t{}'.format(*h))

            # next
            self.stats['steps'] += 1

        self.report['stop'] = 'validation end'
        return current_patch, current_fitness

class ValidRanking(ValidSearch):
    def setup(self):
        super().setup()
        self.name = 'Validation Ranking'
        self.debug_patch = None

    def explore(self, current_patch, current_fitness):
        assert self.debug_patch is not None
        cleaned_patch = self.clean_patch(self.debug_patch)
        self.program.logger.debug('CLEAN_PATCH: {}'.format(str(cleaned_patch)))
        self.program.logger.debug('CLEAN_SIZE: %d (was %d)', len(cleaned_patch), len(self.debug_patch))
        self.report['best_fitness'] = None
        self.report['best_patch'] = None

        # ranking
        ranking = list()
        for edit in cleaned_patch.edit_list:
            # move
            patch = Patch(self.program)
            patch.add(edit)

            # compare
            run = self.evaluate_patch(patch)
            h = [self.stats['steps']+1, run.status, ' ', run.fitness, patch]
            if run.status == 'SUCCESS':
                accept = True
                if self.dominates(run.fitness, self.report['best_fitness']):
                    self.report['best_fitness'] = run.fitness
                    self.report['best_patch'] = patch
                    h[2] = '*'
                ranking.append((edit, run.fitness))

            # log
            self.program.logger.debug(self.program.diff(patch))
            self.program.logger.debug(run)
            self.program.logger.info('{}\t{}\t{}{}\t{}'.format(*h))

            # next
            self.stats['steps'] += 1

        # rebuild
        ranking.sort(key=lambda c: c[1])
        rebuild = Patch(self.program)
        # todo: fail if first bad
        for (k,(edit,_)) in enumerate(ranking):
            # move
            patch = copy.deepcopy(rebuild)
            patch.add(edit)

            # compare
            if k == 0:
                rebuild.add(edit)
                continue
            run = self.evaluate_patch(patch)
            h = [self.stats['steps']+1, run.status, ' ', run.fitness, patch]
            if run.status == 'SUCCESS':
                accept = True
                # todo: accept only over a threshold
                if self.dominates(run.fitness, self.report['best_fitness']):
                    self.program.logger.debug(self.program.diff(patch))
                    self.report['best_fitness'] = run.fitness
                    self.report['best_patch'] = patch
                    h[2] = '*'
                    rebuild.add(edit)

            # log
            self.program.logger.debug(run)
            self.program.logger.info('{}\t{}\t{}{}\t{}'.format(*h))

            # next
            self.stats['steps'] += 1

        self.report['stop'] = 'validation end'
        return current_patch, current_fitness
