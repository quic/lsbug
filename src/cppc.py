# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import time
import signal
import sys
import math

import src.meta as meta
import src.utils as utils


class Cppc:
    def __init__(self, cpu: int = 0) -> None:
        self.hard_path = f'/sys/devices/system/cpu/cpu{cpu}/acpi_cppc/'
        self.soft_path = f'/sys/devices/system/cpu/cpu{cpu}/cpufreq/'
        self.cpu = cpu

    def obtain_scale(self) -> float:
        freq = open(f'{self.hard_path}lowest_freq').read().rstrip()
        perf = open(f'{self.hard_path}lowest_perf').read().rstrip()

        return int(freq) / int(perf)


def dump_cppc(cppc: Cppc) -> None:
    for item in sorted(os.listdir(cppc.hard_path)):
        print(f'- {item}:', open(cppc.hard_path + item).read().rstrip())

    for item in sorted(os.listdir(cppc.soft_path)):
        # "cpuinfo_cur_freq" is not readable by unprivileged users for some reasons.
        if item not in ('cpuinfo_cur_freq', 'scaling_setspeed'):
            print(f'- {item}:', open(cppc.soft_path + item).read().rstrip())


def setup_cppc(watchdog: meta.Watchdog) -> None:
    cppc = Cppc()
    driver = open(f'{cppc.soft_path}scaling_driver').read().rstrip()
    if driver != 'cppc_cpufreq':
        print(f'- Error: cpufreq driver is {driver}', file=sys.stderr)
        raise OSError('The cpufreq driver is not "cppc_cpufreq".')

    governor = open(f'{cppc.soft_path}scaling_governor').read().rstrip()
    if governor != 'schedutil':
        print(f'- Error: cpufreq governor is {governor}', file=sys.stderr)
        raise OSError('The cpufreq governor is not "schedutil"')

    dump_cppc(cppc)


def check_cppc(cppc: Cppc, top: bool = True) -> int:
    if top:
        file = 'max'
        string = 'peak'
    else:
        file = 'min'
        string = 'idle'

    cur_freq = open(f'{cppc.soft_path}scaling_cur_freq').read().rstrip()
    check_freq = open(f'{cppc.soft_path}cpuinfo_{file}_freq').read().rstrip()
    if cur_freq != check_freq:
        print(f'- Error: the CPU is running at {cur_freq} kHz.', file=sys.stderr)
        raise OSError(f'The CPU is not {string} at {check_freq} kHz.')

    return int(cur_freq)


def obtain_counters(file: str) -> tuple[int, int]:
    line = open(file).read().rstrip()
    reference, delivered = line.split()

    return int(reference.lstrip('ref:')), int(delivered.lstrip('del:'))


def check_counters(cppc: Cppc, freq: int) -> None:
    old_ref, old_del = obtain_counters(f'{cppc.hard_path}feedback_ctrs')
    time.sleep(5)
    new_ref, new_del = obtain_counters(f'{cppc.hard_path}feedback_ctrs')

    reference_perf = int(open(f'{cppc.hard_path}reference_perf').read().rstrip())
    scale = cppc.obtain_scale()
    new_freq = 1000 * scale * reference_perf * (new_del - old_del) / (new_ref - old_ref)

    if not math.isclose(new_freq, freq, rel_tol=0.1):
        print(f'- Error: average delivered performance is way off.', file=sys.stderr)
        print(f'  new_ref: {new_ref}, new_del: {new_ref}')
        print(f'  old_ref: {old_ref}, old_del: {old_ref}')
        print(f'  reference_perf: {reference_perf}, scale: {scale}, new_freq: {new_freq}')
        raise OSError(f'The CPU is not running at {freq} kHz.')


def run_cppc(watchdog: meta.Watchdog) -> None:
    cppc = Cppc(utils.tail_cpu())
    print(f'- Only obtain information from CPU{cppc.cpu}.')
    min_freq = check_cppc(cppc=cppc, top=False)

    pid = os.fork()
    if pid == 0:
        os.sched_setaffinity(os.getpid(), [cppc.cpu])
        while True:
            pass

    watchdog.add_pid(pid)
    # it will take a while to scale up.
    time.sleep(1)
    max_freq = check_cppc(cppc=cppc)

    assert max_freq > min_freq
    check_counters(cppc=cppc, freq=max_freq)

    os.kill(pid, signal.SIGTERM)
    # It will take a bit more time to scale down.
    time.sleep(5)
    check_cppc(cppc=cppc, top=False)
    check_counters(cppc=cppc, freq=min_freq)
