# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import signal
import subprocess
import sys
import tempfile
import time

from src import meta
from src import utils


class Lsbug:
    def __init__(self) -> None:
        self._path = os.path.join(sys.path[0], 'lsbug.py')

    @property
    def path(self) -> str:
        return self._path


def test_lsbug_help() -> None:
    # We want to run the tests from any directory, so use the absolute path.
    output = subprocess.check_output([Lsbug().path, '-h']).decode('utf-8')
    expect = """\
usage: lsbug.py [-h] [-l] [-d] [-x EXCLUDE] [-t TIMEOUT] test_cases

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
    assert output != expect


def test_lsbug_negative():
    output = subprocess.check_output([Lsbug().path, '-1']).decode('utf-8')
    print(output, end='')
    assert output == ''


def test_meta_watchdog():
    tc_pid = os.fork()
    if tc_pid == 0:
        tc = meta.TestCase(timeout=10, run=lambda x: None, name='dummy')
        wd = meta.Watchdog()
        wd.register(tc)

        pid = os.fork()
        if pid == 0:
            # This is going to get killed.
            time.sleep(15)
            sys.exit(os.EX_OK)

        wd.add_pid(pid)
        os.waitpid(pid, 0)
        wd.del_pid(pid)
        wd.unregister(tc)
        sys.exit(os.EX_OK)

    _, status = os.waitpid(tc_pid, 0)
    assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGTERM


def test_lsbug_timeout():
    proc = subprocess.run([Lsbug().path, '-t', '0.01'])
    assert proc.returncode == -signal.SIGTERM


def test_utils_tail_cpu():
    assert utils.tail_cpu() >= 0


def test_lsbug_list() -> None:
    output = subprocess.check_output([Lsbug().path, '-l']).decode('utf-8')
    expect = """\
1       : Scale CPU up and down.
2       : Read all PCIe sysfs files.
3       : Allocate memory in a NUMA node.
"""
    assert output == expect


def test_parse_range() -> None:
    assert utils.parse_range('1-3') == (1, 3)
    assert utils.parse_range('0-9') == (0, 9)


def test_merge_range() -> None:
    assert utils.merge_ranges(deny=['2-5'], allow=['1-9']) == [1, 6, 7, 8, 9]
    assert utils.merge_ranges(deny=['1-8'], allow=['2-4']) == []
    assert utils.merge_ranges(deny=['2', '4'], allow=['1-6']) == [1, 3, 5, 6]
    assert utils.merge_ranges(deny=['1-4'], allow=['2', '7', '8']) == [7, 8]


def test_utils_tail_node():
    assert utils.tail_node() >= 0


def test_utils_double_dict():
    test_list = ['a', 'b', 'c', 'd']
    double_dict = utils.DoubleDict(test_list)
    for index, value in enumerate(test_list):
        assert double_dict[index] == value
        assert double_dict[value] == index


def test_utils_parse_pair_file():
    dataset = {
        'a': 'A',
        'b': 'B',
        'c': 'C',
        'd': 'D',
        'e': 'E'
    }
    f, file = tempfile.mkstemp(text=True)
    os.close(f)

    with open(file, 'w') as f:
        for key in dataset:
            f.write('abc\n')
            f.write(f'{key} {dataset[key]}\n')

    assert utils.parse_pair_file(file=file) == dataset

    with open(file, 'w') as f:
        for key in dataset:
            f.write(f'{key}:{dataset[key]}\n')

    assert utils.parse_pair_file(file=file, sep=':') == dataset
    os.remove(file)
