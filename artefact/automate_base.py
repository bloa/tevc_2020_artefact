import argparse
import datetime
import multiprocessing
import os
import re
import subprocess
import sys
import threading
import time

import pyggi # for pyggi.PYGGI_DIR

def my_os_system(cmd):
    env = os.environ.copy()
    if cmd[1] is not None:
        for key in cmd[1]:
            env[key] = cmd[1][key]
    p = subprocess.Popen(cmd[0], env=env, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while p.poll() is None:
        output = p.stdout.readline()
        if output and output != '':
            print(output.strip().decode())
    _, _ = p.communicate()

def wrap_cmd(context, name, time, cmd):
    if context in ['']:
        return (cmd, None)
    elif context in ['tmp']:
        return (cmd, {'TMPDIR': '/tmp/pyggi_{}'.format(name)})
    elif context in ['SGE']:
        base = "qsub -N {} -cwd -l h_rt={} -e cluster_logs -o cluster_logs -b y /usr/bin/bash -cl '{}'"
        return (base.format(name, to_time(time*1.2+15*60), cmd), None)
    else:
        raise ValueError('unknown context')

def threaded_exec_func(shared_cmds, shared_cmds_lock, shared_cores, shared_cores_lock, delay, corepcmd):
    cores = []
    while True:
        try:
            shared_cmds_lock.acquire()
            if len(shared_cmds) > 0:
                cmd = shared_cmds.pop(0)
            else:
                break
        finally:
            shared_cmds_lock.release()
        print(cmd)
        while len(cores) < corepcmd:
            try:
                shared_cores_lock.acquire()
                if len(shared_cores) >= corepcmd:
                    while len(cores) < corepcmd:
                        cores.append(shared_cores.pop(0))
                    break
            finally:
                shared_cores_lock.release()
            time.sleep(1)
        assert len(cores) == corepcmd
        fullcmd = ('taskset --cpu-list {} {}'.format(','.join(map(str, cores)), cmd[0]), cmd[1])
        my_os_system(fullcmd)
        try:
            shared_cores_lock.acquire()
            while len(cores) > 0:
                shared_cores.append(cores.pop(0))
        finally:
            shared_cores_lock.release()
        assert len(cores) == 0
        time.sleep(delay)

def fifo_exec(cmds, n=1, delay=1, corepcmd=1):
    if corepcmd > n:
        raise ValueError('not enough cores')
    cores = list(range(n))
    cmds_lock = threading.Lock()
    cores_lock = threading.Lock()
    pool = []
    for _ in range(n):
        thread = threading.Thread(target=threaded_exec_func, args=(cmds, cmds_lock, cores, cores_lock, delay, corepcmd))
        pool.append(thread)
        thread.start()
        time.sleep(delay)
    for thread in pool:
        thread.join()

def pool_exec(cmds, n=1, delay=1):
    pool = multiprocessing.Pool(n)
    try:
        for cmd in cmds:
            print(cmd)
            pool.apply_async(my_os_system, [cmd])
            time.sleep(delay)
        pool.close()
    except KeyboardInterrupt:
        pool.terminate()
    finally:
        pool.join()

def to_time(n):
    return '{}:{}:{}'.format(int(n//3600), int((n//60)%60), int(n%60))

def find_log(log):
    path = os.path.join(pyggi.PYGGI_DIR, 'logs', log)
    if os.path.isfile(path):
        return path
    return None

def is_log(log):
    return find_log(log) is not None

def clean_patch(log):
    with open(find_log(log), 'r') as out:
        lines = re.findall(r'CLEAN_PATCH: ?(.*)', out.read())
        return lines[0] if len(lines) == 1 else None

def final_patch(log):
    with open(find_log(log), 'r') as out:
        lines = re.findall(r'BEST_PATCH: ?(.*)', out.read())
        return lines[0] if len(lines) == 1 else None

def initial_fitness(log):
    with open(find_log(log), 'r') as out:
        lines = re.findall(r'INIT_FITNESS: ?(.*)', out.read())
        return int(lines[0]) if len(lines) == 1 else None

def final_fitness(log):
    with open(find_log(log), 'r') as out:
        lines = re.findall(r'BEST_FITNESS: ?(.*)', out.read())
        return int(lines[0]) if len(lines) == 1 else None

def debug_fitness(log):
    with open(find_log(log), 'r') as out:
        lines = re.findall('BEST\s*SUCCESS\s*(.*)', out.read())
        return int(lines[0]) if len(lines) > 0 else None

def initial_runtime(log):
    with open(find_log(log), 'r') as out:
        lines = re.findall(r'runtime.: ([^,]*),.*\n.*INITIAL', out.read())
        return float(lines[-1]) if len(lines) == 1 else None

def best_runtime(log):
    with open(find_log(log), 'r') as out:
        lines = re.findall(r'runtime.: ([^,]*),.*\n.*(?:BEST\s+SUCCESS|SUCCESS\s+\*)', out.read())
        return float(lines[-1]) if len(lines) == 1 else None

def debug_runtime(log):
    with open(find_log(log), 'r') as out:
        lines = re.findall(r'runtime.: ([^,]*),.*\n.*(?:BEST\s+SUCCESS\s+\*)', out.read())
        return float(lines[0]) if len(lines) > 0 else None

def final_diff(log):
    regexp = re.compile(r'BEST_PATCH:.*?\[DEBUG\]\s(.*)', re.DOTALL)
    with open(find_log(log), 'r') as out:
        lines = re.findall(regexp, out.read())
        return lines[0] if len(lines) == 1 else None

def stats_steps(log):
    regexp = re.compile(r'\[DEBUG\]\s\{.*\'steps\': (\d+)')
    with open(find_log(log), 'r') as out:
        lines = re.findall(regexp, out.read())
        return int(lines[0]) if len(lines) == 1 else 0

def stats_useful_steps(log):
    regexp = re.compile(r'\[DEBUG]\s<RunResult \'status\': \'SUCCESS\'.*\'percentage\': (\d+\.?\d*)')
    with open(find_log(log), 'r') as out:
        lines = re.findall(regexp, out.read())
        return len({s for s in lines if float(s) < 100})

def log_time(log):
    regexp = re.compile(r'^(20..-..-.. ..:..:..,...)', re.M)
    timef = '%Y-%m-%d %H:%M:%S,%f'
    with open(find_log(log), 'r') as out:
        lines = re.findall(regexp, out.read())
        if len(lines) > 0:
            ts1 = datetime.datetime.strptime(lines[0], timef)
            ts2 = datetime.datetime.strptime(lines[-1], timef)
            return (ts2-ts1).total_seconds()
        return None

def time_run(step, scenario, patch=None):
    if step == 'analyse':
        return scenario.APPROX_TIME*10
    elif step == 'check':
        return scenario.APPROX_TIME/scenario.FOLDS*10
    elif step == 'training':
        return (3+1+2000)*(scenario.FOLDS-2)*scenario.APPROX_TIME/scenario.FOLDS
    elif step == 'validation':
        return (1+1+2*(patch.count("|")+1))*scenario.APPROX_TIME/scenario.FOLDS
    elif step in ['test', 'assess-gi-valid', 'assess-gp-valid', 'assess-gp-test']:
        return (1+1+1)*scenario.APPROX_TIME/scenario.FOLDS
    elif step in ['assess-gi-training', 'assess-gi-training']:
        return (1+1+1)*(scenario.FOLDS-2)*scenario.APPROX_TIME/scenario.FOLDS
    elif step in ['assess-gi-all', 'assess-gp-all']:
        return (1+1+1)*scenario.APPROX_TIME


def dwim(args, scenarios, algos, cores, entry='./main.py', corepcmd=1):
    cmds = {}
    total_time = {}
    for scenario in scenarios:
        cmds[scenario.CORES] = []
        total_time[scenario.CORES] = 0
    for scenario in scenarios:
        sname = scenario.niceify(scenario.SCENARIO_NAME)
        cmd = 'python3 {} --scenario {} --step {}'.format(entry, sname, args.step)
        name = '{}_{}'.format(sname, args.step)

        logname = '{}_{}_{}_{}.log'
        if args.step in ['analyse', 'check']:
            t = time_run(args.step, scenario)
            for rep in range(max(cores//scenario.CORES, 1)):
                total_time[scenario.CORES] += t
                c = '{} --seed {} --inst-seed {}'.format(cmd, args.seed, args.seed)
                c = wrap_cmd(args.context, '{}_{}'.format(name, rep), t, c)
                cmds[scenario.CORES].append(c)
        elif args.step == 'training':
            t = time_run(args.step, scenario)
            for rep in range(scenario.FOLDS):
                for algo in algos:
                    c = '{} --seed {} --inst-seed {}'.format(cmd, args.seed+rep, args.seed+rep//scenario.FOLDS)
                    c = '{} --algo {} --replication {}'.format(c, algo, rep%scenario.FOLDS)
                    c = wrap_cmd(args.context, '{}_{}_{}'.format(name, algo, rep), t, c)
                    if args.force or not is_log(logname.format(sname, algo, args.seed+rep, args.step)):
                        total_time[scenario.CORES] += t
                        cmds[scenario.CORES].append(c)
        elif args.step in ['validation', 'assess-gp-training', 'assess-gp-validation', 'assess-gp-test', 'assess-gp-all']:
            for rep in range(scenario.FOLDS):
                for algo in algos:
                    c = '{} --seed {} --inst-seed {}'.format(cmd, args.seed+rep, args.seed+rep//scenario.FOLDS)
                    c = '{} --algo {} --replication {}'.format(c, algo, rep)
                    if args.force or not is_log(logname.format(sname, algo, args.seed+rep, args.step)):
                        log = logname.format(sname, algo, args.seed+rep, 'training')
                        if is_log(log):
                            patch = final_patch(log)
                            if patch is None:
                                print('final patch fail in log:', log)
                            elif patch == '':
                                print('empty patch in log:', log)
                            else:
                                t = time_run(args.step, scenario, patch)
                                c = '{} --patch "{}"'.format(c, patch)
                                c = wrap_cmd(args.context, '{}_{}_{}'.format(name, algo, rep), t, c)
                                total_time[scenario.CORES] += t
                                cmds[scenario.CORES].append(c)
        elif args.step in ['test', 'assess-gi-training', 'assess-gi-validation', 'assess-gi-all']:
            for rep in range(scenario.FOLDS):
                for algo in algos:
                    c = '{} --seed {} --inst-seed {}'.format(cmd, args.seed+rep, args.seed+rep//scenario.FOLDS)
                    c = '{} --algo {} --replication {}'.format(c, algo, rep)
                    if args.force or not is_log(logname.format(sname, algo, args.seed+rep, args.step)):
                        log = logname.format(sname, algo, args.seed+rep, 'validation')
                        if is_log(log):
                            patch = final_patch(log)
                            if patch is None:
                                print('final patch fail in log:', log)
                            elif patch == '':
                                print('empty patch in log:', log)
                            else:
                                t = time_run(args.step, scenario, patch)
                                c = '{} --patch "{}"'.format(c, patch)
                                c = wrap_cmd(args.context, '{}_{}_{}'.format(name, algo, rep), t, c)
                                total_time[scenario.CORES] += t
                                cmds[scenario.CORES].append(c)
        else:
            raise NotImplementedError

    for core in sorted(cmds.keys()):
        if len(cmds[core]) > 0:
            for cmd in cmds[core]:
                print(cmd)
    for core in sorted(cmds.keys()):
        if len(cmds[core]) > 0:
            ad = max(cores//core, 1)
            print('{} ({}*{}/{})'.format(to_time(total_time[core]/ad), to_time(total_time[core]/len(cmds[core])), len(cmds[core]), ad), file=sys.stderr)
            if args.run:
                # pool_exec(cmds[core], ad, args.delay)
                fifo_exec(cmds[core], max(cores, core), args.delay, core)

algos = []
scenarios = []
seed = 123
