# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import re
import typing

from src import data


class DoubleDict:
    def __init__(self, key_list: list[str]) -> None:
        self._double_dict: dict[typing.Union[str, int], typing.Union[str, int]] = {}
        for index, key in enumerate(key_list):
            self._double_dict[index] = key
            self._double_dict[key] = index

    def __getitem__(self, item: typing.Union[str, int]) -> typing.Union[str, int]:
        return self._double_dict[item]


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
    nr_cpu = -1
    for entry in os.listdir(sysfs):
        if not re.match(r'cpu\d+', entry):
            continue

        # Whether CPU0 have the "online" file depends on the kernel config.
        online_file = os.path.join(sysfs, entry, 'online')
        if os.path.exists(online_file) and open(online_file).read().rstrip() == '1':
            nr_cpu = max(nr_cpu, int(entry.lstrip('cpu')))

    assert nr_cpu >= 0
    return nr_cpu


def parse_pair_file(file: str, sep: typing.Optional[str] = None) -> dict[str, str]:
    """Return key value pairs from a file according to a delimiter string, and ignore non-working lines."""
    pairs = {}
    with open(file) as f:
        for line in f:
            try:
                key, value = line.rstrip().split(sep=sep)
                pairs[key] = value
            except ValueError:
                pass

    return pairs


def tail_node() -> int:
    """Return the last online NUMA node number including some memory."""
    sysfs = '/sys/devices/system/node/'
    nr_node = -1
    for entry in os.listdir(sysfs):
        if not re.match(r'node\d+', entry):
            continue

        # Don't think we can have a CPU-less node, so just check the "local_node" number.
        numastat = os.path.join(sysfs, entry, 'numastat')
        pairs = parse_pair_file(file=numastat)

        if int(pairs['local_node']) > 0:
            nr_node = max(nr_node, int(entry.lstrip('node')))

    assert nr_node >= 0
    return nr_node
