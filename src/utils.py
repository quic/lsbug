# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import re

import src.data as data


class DoubleDict:
    def __init__(self, key_list: list[str]):
        self.double_dict = {}
        for index, key in enumerate(key_list):
            self.double_dict[index] = key
            self.double_dict[key] = index

    def __getitem__(self, item):
        return self.double_dict[item]


def parse_range(simple_range: str) -> tuple[int, int]:
    try:
        start, end = simple_range.split('-')
    except ValueError:
        raise RuntimeError(f'Unable to parse the range {simple_range}.')

    return int(start), int(end)


def merge_ranges(deny: list[str], allow: list[str]) -> list[int]:
    flat_list = []
    # We will run all tests if none is given.
    if not allow:
        flat_list = range(1, data.Mapping.get_total() + 1)

    flat_set = set(flat_list)
    for item in allow:
        if item.lstrip('-').isdigit():
            flat_set.add(int(item))
        else:
            start, end = parse_range(item)
            flat_set.update(range(start, end + 1))

    for item in deny:
        if item.lstrip('-').isdigit():
            flat_set.remove(int(item))
        else:
            start, end = parse_range(item)
            flat_set.difference_update(range(start, end + 1))

    return sorted(flat_set)


def tail_cpu() -> int:
    """Return the last online CPU number."""
    sysfs = '/sys/devices/system/cpu/'
    cpu = -1
    for entry in os.listdir(sysfs):
        if not re.match(r'cpu\d+', entry):
            continue

        # Whether CPU0 have the "online" file depends on the kernel config.
        online = f'{sysfs}{entry}/online'
        if os.path.exists(online) and open(online).read().rstrip() == '1':
            cpu = max(cpu, int(entry.lstrip('cpu')))

    assert cpu >= 0
    return cpu


def tail_node() -> int:
    """Return the last online NUMA node number including some memory."""
    sysfs = '/sys/devices/system/node/'
    node = -1
    for entry in os.listdir(sysfs):
        if not re.match(r'node\d+', entry):
            continue

        # Don't think we can have a CPU-less node, so just check the "local_node" number.
        path = os.path.join(sysfs, entry, 'numastat')
        with open(path) as f:
            for line in f:
                name, value = line.split()
                # Make sure we have some memory in this node.
                if name == 'local_node' and int(value) > 0:
                    node = max(node, int(entry.lstrip('node')))

    assert node >= 0
    return node
