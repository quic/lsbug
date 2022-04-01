# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

import ctypes
import ctypes.util
import os
import typing
import mmap
import resource

import src.meta as meta
import src.utils as utils


class Numa:
    def __init__(self):
        # All system call numbers are from "include/uapi/asm-generic/unistd.h".
        self.nr_mbind = 235
        self.nr_get_mempolicy = 236
        self.nr_set_mempolicy = 237
        self.nr_migrate_pages = 238
        self.nr_move_pages = 239
        self.sysfs = '/sys/devices/system/node/'
        # from "include/uapi/linux/mempolicy.h"
        self.policy = utils.DoubleDict(['MPOL_DEFAULT', 'MPOL_PREFERRED', 'MPOL_BIND', 'MPOL_INTERLEAVE', 'MPOL_LOCAL',
                                        'MPOL_PREFERRED_MANY'])
        self.syscall = ctypes.CDLL(name=ctypes.util.find_library('c'), use_errno=True).syscall
        self.maxnode = 4096

    def get_mempolicy(self, mode: 'ctypes.byref', nodemask: ctypes.Array, maxnode: int, addr: typing.Optional[int],
                      flags: int) -> None:
        self.syscall.argtypes = [ctypes.c_long, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_ulong),
                                 ctypes.c_ulong, ctypes.c_void_p, ctypes.c_int]
        self.syscall.restype = ctypes.c_long

        if self.syscall(self.nr_get_mempolicy, mode, nodemask, maxnode, addr, flags):
            raise OSError(f'error from get_mempolicy():', os.strerror(ctypes.get_errno()))

    def set_mempolicy(self, mode: int, nodemask: ctypes.Array, maxnode: int) -> None:
        self.syscall.argtypes = [ctypes.c_long, ctypes.c_int, ctypes.POINTER(ctypes.c_ulong), ctypes.c_ulong]
        self.syscall.restype = ctypes.c_long

        if self.syscall(self.nr_set_mempolicy, mode, nodemask, maxnode):
            raise OSError(f'error from set_mempolicy():', os.strerror(ctypes.get_errno()))


def check_numa_node(watchdog: meta.Watchdog) -> None:
    node = utils.tail_node()
    print(f'- Found NUMA node {node} to allocate.')
    watchdog.storage['node'] = node

    numa = Numa()
    mode = ctypes.c_int()
    nodemask = (ctypes.c_ulong * numa.maxnode)()
    numa.get_mempolicy(mode=ctypes.byref(mode), nodemask=nodemask, maxnode=numa.maxnode, addr=None, flags=0)
    watchdog.storage['mode'] = mode
    watchdog.storage['nodemask'] = nodemask
    print(f'- Current NUMA policy is {numa.policy[mode.value]}.')


def allocate_numa_node(watchdog: meta.Watchdog) -> None:
    numa = Numa()
    nodemask = (ctypes.c_ulong * numa.maxnode)()
    node = watchdog.storage['node']
    nodemask[0] = ctypes.c_ulong(1 << node)
    numa.set_mempolicy(numa.policy['MPOL_BIND'], nodemask, numa.maxnode)

    numastat = os.path.join(numa.sysfs, f'node{node}', 'numastat')
    old_numa_hit = utils.parse_pair_file(file=numastat)['numa_hit']

    num_pages = 1024
    print(f'- Allocate {num_pages} on NUMA node {node}.')
    for _ in range(num_pages):
        with mmap.mmap(-1, resource.getpagesize()) as mm:
            mm.write(b'0')

    new_numa_hit = utils.parse_pair_file(file=numastat)['numa_hit']
    delta = int(new_numa_hit) - int(old_numa_hit)
    print(f'- The delta from "numa_hit" is {delta}.')
    # We probably won't get the exact delta due to debugging features like KASAN.
    if delta < num_pages:
        raise OSError(f'- unexpected "numa_hit": old {old_numa_hit}; new {new_numa_hit}')


def restore_numa_policy(watchdog: meta.Watchdog) -> None:
    numa = Numa()
    mode = watchdog.storage['mode']
    nodemask = watchdog.storage['nodemask']

    print(f'- Restore NUMA policy to {numa.policy[mode.value]}.')
    numa.set_mempolicy(mode=mode, nodemask=nodemask, maxnode=numa.maxnode)
