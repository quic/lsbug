#!/usr/bin/env python3

# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

import argparse

import src.meta as meta
import src.data as data
import src.utils as utils


def main() -> None:
    parser = argparse.ArgumentParser(prog='lsbug')
    parser.add_argument('-l', '--list', action='store_true', help='List all test cases and their descriptions.')
    parser.add_argument('-d', '--debug', action='store_true', help='Turn on the debugging output.')
    parser.add_argument('-x', '--exclude', action='append',
                        help='Exclude test cases by a number or range. It can be specified multiple times.')
    parser.add_argument('-t', '--timeout', help='number of seconds before killing the test run.')
    parser.add_argument('test_cases', action='append',
                        help=('Trigger test cases by numbers. They can be specified multiple times and used as a range,'
                              ' e.g., 0-3'))

    args = parser.parse_args()

    watchdog = meta.Watchdog()
    test_run = meta.TestRun()
    if args.timeout:
        watchdog.register(test_run)

    test_list = utils.merge_ranges(args.exclude, args.test_cases)
    for test_num in test_list:
        # We will need Python 3.8+ here.
        if not (test_case := data.num2case(test_num)):
            continue

        watchdog = meta.Watchdog()
        watchdog.register(test_case)
        test_case.setup()
        test_case.run()
        test_case.cleanup()
        watchdog.unregister(test_case)

    if args.timeout:
        watchdog.unregister(test_run)


if __name__ == '__main__':
    main()
