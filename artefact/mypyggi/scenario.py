import datetime
import distutils.dir_util
import glob
import logging
import os
import random
import re
import shutil

import pyggi
from pyggi.tree import StmtReplacement, StmtInsertion, StmtDeletion, StmtMoving
from pyggi.utils import Logger

class Scenario:
    SCENARIO_NAME = 'UNKNOWN'
    PROXY_PATH = ''
    DATA = []
    APPROX_TIME = 10
    FOLDS = 10

    def __init__(self):
        self.program = None
        self.ensure_sane_proxy()
        self.my_init()

    def enter(self):
        if self.PROXY_PATH != '':
            self.old_pwd = os.getcwd()
            os.chdir(self.PROXY_PATH)
            print('[{}] Chdir to "{}"'.format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.PROXY_PATH))
        self.program.create_tmp_variant()
        self.fix_logging()

    def exit(self):
        if self.PROXY_PATH != '':
            log_dir = os.path.join(self.old_pwd, pyggi.PYGGI_DIR, 'logs')
            os.makedirs(log_dir, exist_ok=True)

            for f in glob.iglob(os.path.join(pyggi.PYGGI_DIR, 'logs', '*')):
                k = 0
                while True:
                    fk = f if k == 0 else '{}_{}'.format(f, str(k))
                    try:
                        os.close(os.open(os.path.join(self.old_pwd, fk), os.O_CREAT | os.O_EXCL))
                        shutil.move(f, os.path.join(self.old_pwd, fk))
                        break
                    except FileExistsError:
                        k += 1
                print('[{}] Copy back "{}"'.format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), fk))
            os.chdir(self.old_pwd)
            print('[{}] Chdir back to "{}"'.format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.old_pwd))
            shutil.rmtree(self.PROXY_PATH)

    def fix_logging(self):
        log_filename = self.name
        log = Logger(log_filename)
        for h in list(log._logger.handlers):
            log._logger.removeHandler(h)
        formatter = logging.Formatter('%(asctime)s\t[%(levelname)s]\t%(message)s')
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        if 'JOB_ID' not in os.environ:
            file_handler = logging.FileHandler(log.log_file_path, delay=True)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)
            log._logger.addHandler(file_handler)
        else:
            stream_handler.setFormatter(formatter)
        log._logger.addHandler(stream_handler)
        self.program.logger = log

    def auto_bin(self, data, replication=0):
        bins = data
        if len(data) > 0 and not isinstance(data[0], list):
            bins = [data]
        for _ in range(0, replication):
            bins = [random.sample(b, k=len(b)) for b in bins]
        return bins

    def sample_bins(self, bins, sample=None):
        out = []
        for (i,b) in enumerate(bins):
            out.append(random.sample(b, k=(sample or len(b))))
        return out

    def reorder_in_bins(self, bins_ref, bins):
        return [[i for i in r if i in b] for (r,b) in zip(bins_ref, bins)]

    def cv_fold(self, data, nb_folds):
        return [[d for (j,d) in enumerate(data) if j%nb_folds == i] for i in range(nb_folds)]

    def cv_pick_single(self, data, rep):
        return [data[rep]]

    def cv_pick_others(self, data, rep):
        return data[:rep] + data[rep+1:]

    def cv_unfold(self, data):
        return [i for fold in data for i in fold]

    def setup_gi(self, step, algo):
        if step == 'analyse':
            algo.config['warmup'] = 9
            algo.stop['steps'] = 0
            algo.stop['wall'] = 0
        elif step == 'training':
            algo.config['warmup'] = 3
            algo.stop['steps'] = None
            algo.stop['wall'] = 2000*self.APPROX_TIME/self.FOLDS
        elif step == 'validation':
            algo.config['warmup'] = 1
            algo.stop['steps'] = 0
            algo.stop['wall'] = None
        elif step in ['test', 'assess-gi-training', 'assess-gi-valid', 'assess-gp-training', 'assess-gp-valid', 'assess-gp-test']:
            algo.config['warmup'] = 1
            algo.stop['steps'] = 0
            algo.stop['wall'] = None
        else:
            algo.config['warmup'] = 0
            algo.stop['steps'] = 10
            algo.stop['wall'] = 3*60

    def setup(self, step, algo, seed, replication, name=None):
        # fix name
        if name is None:
            name = algo.name
        self.name = '_'.join([
            self.niceify(self.SCENARIO_NAME),
            self.niceify(name),
            self.niceify(seed),
            step,
        ])

        # program
        assert(self.program is not None)
        self.program.possible_edits = [StmtReplacement, StmtInsertion, StmtDeletion]

        # algo
        algo.program = self.program
        self.my_setup(algo) # avoid super()

        # "perbin"
        bins_full = self.auto_bin(self.program.instances)
        for key in algo.config:
            if key.endswith('_perbin'):
                algo.config[key[:-7]] = algo.config[key]*len(bins_full)

        # GI
        self.setup_gi(step, algo)

        # instances
        if step in ['analyse', 'assess-gi-all', 'assess-gp-all']:
            # ALL instances
            bins = bins_full
        elif step in ['training', 'assess-gi-training', 'assess-gp-training']:
            # k-2 folds from k-1 folds
            bins = [b[:] for b in bins_full]
            for _ in range(0, replication//self.FOLDS+1):
                bins = self.sample_bins(bins)
            k_test = replication%self.FOLDS
            for _ in range(0, replication+1):
                k_valid = random.randint(0, self.FOLDS-2)
            bins = [self.cv_fold(b, self.FOLDS) for b in bins]
            bins = [self.cv_pick_others(b, k_test) for b in bins]
            bins = [self.cv_pick_others(b, k_valid) for b in bins]
            bins = [self.cv_unfold(b) for b in bins]
            bins = self.reorder_in_bins(bins_full, bins)
        elif step in ['validation', 'assess-gi-valid', 'assess-gp-valid']:
            # 1 fold from k-1 folds
            bins = [b[:] for b in bins_full]
            for _ in range(0, replication//self.FOLDS+1):
                bins = self.sample_bins(bins)
            k_test = replication%self.FOLDS
            for _ in range(0, replication+1):
                k_valid = random.randint(0, self.FOLDS-2)
            bins = [self.cv_fold(b, self.FOLDS) for b in bins]
            bins = [self.cv_pick_others(b, k_test) for b in bins]
            bins = [self.cv_pick_single(b, k_valid) for b in bins]
            bins = [self.cv_unfold(b) for b in bins]
            bins = self.reorder_in_bins(bins_full, bins)
        elif step in ['test', 'assess-gp-test']:
            # 1 fold
            bins = [b[:] for b in bins_full]
            for _ in range(0, replication//self.FOLDS+1):
                bins = self.sample_bins(bins)
            k_test = replication%self.FOLDS
            bins = [self.cv_fold(b, self.FOLDS) for b in bins]
            bins = [self.cv_pick_single(b, k_test) for b in bins]
            bins = [self.cv_unfold(b) for b in bins]
            bins = self.reorder_in_bins(bins_full, bins)
        elif step in ['check']:
            # 1 instance/bin
            bins = self.sample_bins(bins_full, 1)
        else:
            assert False, 'unknown algorithm: {}'.format(name)
        algo.instance_bins = bins

    def my_init(self, algo):
        pass

    def my_setup(self, algo):
        pass

    def ensure_sane_proxy(self):
        if 'TMPDIR' in os.environ:
            self.PROXY_PATH = os.environ['TMPDIR']
        self.PROXY_PATH = os.path.abspath(self.PROXY_PATH)
        if self.PROXY_PATH == os.path.abspath('.'):
            self.PROXY_PATH = ''
            print('PyGGI will run from the current directory ({})'.format(os.path.abspath('.')))
        else:
            self.PROXY_PATH = os.path.join(self.PROXY_PATH, 'pyggi')
            print('PyGGI will run from {}'.format(self.PROXY_PATH))
            dummy = os.path.join(self.PROXY_PATH, '.pyggi_proxy')
            if os.path.exists(self.PROXY_PATH):
                if os.path.exists(dummy):
                    shutil.rmtree(self.PROXY_PATH)
                else:
                    raise RuntimeError('PROXY_PATH should not exist (yet)')
                os.makedirs(self.PROXY_PATH, exist_ok=True)
                open(dummy, 'w').close

    def proxify(self, path, copy=True, must_exist=True):
        if self.PROXY_PATH == '':
            return os.path.abspath(path)
        proxy = os.path.join(self.PROXY_PATH, path)
        proxy = re.sub('\.\./', 'parent/', proxy)
        proxy = re.sub('\./', '', proxy)
        if not copy:
            return proxy
        try:
            print('[{}] Copy "{}" to "{}"'.format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), path, proxy))
            if os.path.isfile(path):
                os.makedirs(os.path.dirname(proxy), exist_ok=True)
                shutil.copyfile(path, proxy)
            else:
                shutil.copytree(path, proxy)
        except FileNotFoundError:
            if must_exist:
                raise
        return proxy

    @classmethod
    def niceify(cls, name):
        return re.sub('[^a-z0-9-]', '', str(name).lower())
