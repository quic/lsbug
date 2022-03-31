# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

import ctypes
import ctypes.util
import enum
import os
import typing

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
                      flags: int):
        self.syscall.argtypes = [ctypes.c_long, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_ulong),
                                 ctypes.c_ulong, ctypes.c_void_p, ctypes.c_int]
        self.syscall.restype = ctypes.c_long

        if self.syscall(self.nr_get_mempolicy, mode, nodemask, maxnode, addr, flags):
            raise OSError(f'error from get_mempolicy():', os.strerror(ctypes.get_errno()))


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
    pass


def restore_numa_policy(watchdog: meta.Watchdog) -> None:
    pass
