#!/usr/bin/env python3

# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

import typing

import src.meta as meta
import src.cppc as cppc


def num2case(num: int) -> typing.Optional[meta.TestCase]:
    test_case = meta.TestCase()
    tc_map = {
        1: (cppc.setup_cppc, cppc.run_cppc, test_case.cleanup, 30, 'scale CPU up and down')
    }

    if num in tc_map:
        test_case.setup, test_case.run, test_case.cleanup, test_case.timeout, test_case.name = tc_map[num]
    else:
        return None

    return test_case
