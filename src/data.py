# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

import typing

import src.meta as meta
import src.cppc as cppc
import src.pcie as pcie
import src.numa as numa


# This class will be alive for the program's whole life, so we don't need to create an instance of it.
class Mapping:
    _tc_map = {
        1: meta.TestCase(setup=cppc.setup_cppc, run=cppc.run_cppc, timeout=30, name='Scale CPU up and down.'),
        2: meta.TestCase(setup=pcie.check_pcie_sysfs, run=pcie.read_pcie_sysfs, timeout=30,
                         name='Read all PCIe sysfs files.'),
        3: meta.TestCase(setup=numa.check_numa_node, run=numa.allocate_numa_node, cleanup=numa.restore_numa_policy,
                         timeout=30, name='Allocate memory in a NUMA node.')
    }

    @classmethod
    def show_all(cls):
        for index, tc in cls._tc_map.items():
            print(f'{index:<8}: {tc.name}')

    @classmethod
    def get_test_case(cls, num: int) -> typing.Optional[meta.TestCase]:
        if num in cls._tc_map:
            return cls._tc_map[num]

    @classmethod
    def get_total(cls) -> int:
        return len(cls._tc_map)
