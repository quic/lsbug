#!/usr/bin/env python3

# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import signal
import subprocess
import sys
import time

import meta


class Lsbug:
    path = f'{sys.path[0]}/../lsbug.py'


def test_lsbug_help() -> None:
    print('- Test lsbug help.')
    # We want to run the tests from any directory, so use the absolute path.
    output = subprocess.check_output([Lsbug.path, '-h']).decode('utf-8')
    expect = """\
usage: lsbug [-h] [-l] [-d] [-x EXCLUDE] [-t TIMEOUT] test_cases

positional arguments:
  test_cases            Trigger test cases by numbers. They can be specified
                        multiple times and used as a range, e.g., 0-3

optional arguments:
  -h, --help            show this help message and exit
  -l, --list            List all test cases and their descriptions.
  -d, --debug           Turn on the debugging output.
  -x EXCLUDE, --exclude EXCLUDE
                        Exclude test cases by a number or range. It can be
                        specified multiple times.
  -t TIMEOUT, --timeout TIMEOUT
                        number of seconds before killing the test run.
"""

    if output != expect:
        print('- output is:')
        print(output)
        print('- expect is:')
        print(expect)
        raise AssertionError


def test_lsbug_negative():
    print('- Test lsbug with a negative test case number.')
    output = subprocess.check_output([Lsbug.path, '-1']).decode('utf-8')
    print(output, end='')
    assert output == ''


def test_meta_watchdog():
    print('- Test the Watchdog class.')
    tc = meta.TestCase()
    tc.timeout = 10

    wd = meta.Watchdog()
    wd.register(tc)

    pid = os.fork()
    if pid == 0:
        time.sleep(15)
        sys.exit(os.EX_OK)

    wd.add_pid(pid)
    _, status = os.wait()
    wd.unregister(tc)

    assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGTERM

