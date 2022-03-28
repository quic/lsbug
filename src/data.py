#!/usr/bin/env python3

# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

import typing

import src.meta as meta
import src.cppc as cppc
import src.pcie as pcie


class Mapping:
    _tc_map = {
        1: (cppc.setup_cppc, cppc.run_cppc, meta.TestCase().cleanup, 30, 'Scale CPU up and down.'),
        2: (pcie.check_pcie_sysfs, pcie.read_pcie_sysfs, meta.TestCase().cleanup, 30, 'Read all PCIe sysfs files.')
    }

    @classmethod
    def show_all(cls):
        for key, value in cls._tc_map.items():
            print(f'{key:<8}: {value[-1]}')

    @classmethod
    def get_test_case(cls, num: int) -> typing.Optional[meta.TestCase]:
        test_case = meta.TestCase()

        if num in cls._tc_map:
            test_case.setup, test_case.run, test_case.cleanup, test_case.timeout, test_case.name = cls._tc_map[num]
        else:
            return

        return test_case

    @classmethod
    def get_total(cls) -> int:
        return len(cls._tc_map)
