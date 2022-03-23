#!/usr/bin/env python3

# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import re


def merge_ranges(exclude_list: list[str], test_list: list[str]) -> list[int]:
    # FIXME
    ret = [int(test_list[0])]

    return ret


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

    return cpu
