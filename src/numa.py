# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

# "check.py" will get us into a circular import.
from __future__ import annotations

import ctypes
import ctypes.util
import os
import typing
import mmap
import resource

import src.meta as meta
import src.utils as utils


class Numa:
    def __init__(self, nr_node: int) -> None:
        self._nr_node: int = nr_node
        self._sysfs: str = f'/sys/devices/system/node/node{nr_node}'
        # All system call numbers are from "include/uapi/asm-generic/unistd.h".
        self._nr_mbind: int = 235
        self._nr_get_mempolicy: int = 236
        self._nr_set_mempolicy: int = 237
        self._nr_migrate_pages: int = 238
        self._nr_move_pages: int = 239
        # from "include/uapi/linux/mempolicy.h"
        self._policy: utils.DoubleDict = utils.DoubleDict(['MPOL_DEFAULT', 'MPOL_PREFERRED', 'MPOL_BIND',
                                                           'MPOL_INTERLEAVE', 'MPOL_LOCAL', 'MPOL_PREFERRED_MANY'])
        self._syscall: typing.Callable[[ctypes.c_long, ...], typing.Any] = ctypes.CDLL(
            name=ctypes.util.find_library('c'), use_errno=True).syscall
        self._maxnode: int = 4096

    @property
    def nr_node(self) -> int:
        return self._nr_node

    @property
    def sysfs(self) -> str:
        return self._sysfs

    @property
    def nr_mbind(self) -> int:
        return self._nr_mbind

    @property
    def nr_get_mempolicy(self) -> int:
        return self._nr_get_mempolicy

    @property
    def nr_set_mempolicy(self) -> int:
        return self._nr_set_mempolicy

    @property
    def nr_migrate_pages(self) -> int:
        return self._nr_migrate_pages

    @property
    def nr_move_pages(self) -> int:
        return self._nr_move_pages

    @property
    def policy(self) -> utils.DoubleDict:
        return self._policy

    @property
    def syscall(self) -> typing.Callable[..., typing.Any]:
        return self._syscall

    @property
    def maxnode(self) -> int:
        return self._maxnode

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
    nr_node = utils.tail_node()
    print(f'- Found NUMA node {nr_node} to allocate.')
    numa = Numa(nr_node=nr_node)
    watchdog.storage['numa'] = numa

    mode = ctypes.c_int()
    nodemask = (ctypes.c_ulong * numa.maxnode)()
    numa.get_mempolicy(mode=ctypes.byref(mode), nodemask=nodemask, maxnode=numa.maxnode, addr=None, flags=0)
    watchdog.storage['mode'] = mode
    watchdog.storage['nodemask'] = nodemask
    print(f'- Current NUMA policy is {numa.policy[mode.value]}.')


def allocate_numa_node(watchdog: meta.Watchdog) -> None:
    numa = watchdog.storage['numa']
    nodemask = (ctypes.c_ulong * numa.maxnode)()
    nodemask[0] = ctypes.c_ulong(1 << numa.nr_node)
    numa.set_mempolicy(mode=numa.policy['MPOL_BIND'], nodemask=nodemask, maxnode=numa.maxnode)

    numastat = os.path.join(numa.sysfs, 'numastat')
    old_numa_hit = utils.parse_pair_file(file=numastat)['numa_hit']

    num_pages = 1024
    print(f'- Allocate {num_pages} on NUMA node {numa.nr_node}.')
    for _ in range(num_pages):
        with mmap.mmap(-1, resource.getpagesize()) as mm:
            mm.write(b'0')

    new_numa_hit = utils.parse_pair_file(file=numastat)['numa_hit']
    delta = int(new_numa_hit) - int(old_numa_hit)
    print(f'- The delta from "numa_hit" is {delta}.')
    # We probably won't get the exact delta due to debugging features like KASAN.
    if delta < num_pages:
        raise OSError(f'unexpected "numa_hit": old {old_numa_hit}; new {new_numa_hit}')


def restore_numa_policy(watchdog: meta.Watchdog) -> None:
    mode = watchdog.storage['mode']
    nodemask = watchdog.storage['nodemask']
    numa = watchdog.storage['numa']

    print(f'- Restore NUMA policy to {numa.policy[mode.value]}.')
    numa.set_mempolicy(mode=mode, nodemask=nodemask, maxnode=numa.maxnode)
