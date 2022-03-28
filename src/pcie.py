#!/usr/bin/env python3

# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

import concurrent.futures
import re
import os
import errno

import src.meta as meta


class SysfsError:
    def __init__(self):
        self.save = {}
        self.allow = {
            'autosuspend_delay_ms': errno.EIO
        }


def check_pcie_sysfs(watchdog: meta.Watchdog) -> None:
    for entry in os.listdir('/sys/devices'):
        if re.match(r'pci\d+:\d+', entry):
            return

    raise OSError('No PCIe root port found.')


def consume_pcie_root(path: str, sysfs_error: SysfsError) -> int:
    count = 0
    for root, dirs, files in os.walk(top=path):
        # We are not going to read all devices' directories due to file-read many errors.
        dirs[:] = [entry for entry in dirs if not re.match(r'[0-9a-z]+:[0-9a-z]+:[0-9a-z]+\.[0-9a-z]+', entry)]

        for file in files:
            file_path = os.path.join(root, file)
            if os.access(file_path, os.R_OK):
                # we might get decoding errors without 'b'.
                f = open(file_path, 'rb')
                try:
                    count += 1
                    f.read()
                except OSError as e:
                    if file in sysfs_error.allow and sysfs_error.allow[file] == e.errno:
                        pass
                    else:
                        print(f'- Error: {file_path} - {e}')
                        sysfs_error.save[file_path] = e.errno
                        raise e
                finally:
                    f.close()

    return count


def read_pcie_sysfs(watchdog: meta.Watchdog) -> None:
    executor = concurrent.futures.ThreadPoolExecutor()
    sysfs = '/sys/devices/'
    todo = []
    future_map = {}
    sysfs_error = SysfsError()
    for entry in os.listdir(sysfs):
        if not re.match(r'pci\d+:\d+', entry):
            continue

        root_path = os.path.join(sysfs, entry)
        print(f'- Read files in {root_path}.')
        future = executor.submit(consume_pcie_root, root_path, sysfs_error)
        future_map[future] = root_path
        todo.append(future)

    # Check to see if we get any exceptions.
    for future in concurrent.futures.as_completed(fs=todo):
        print(f'- Finish reading {future_map[future]} for {future.result()} files.')

    for file in sysfs_error.save:
        print(f'- {file}: {os.strerror(sysfs_error.save[file])}')

    if sysfs_error.save:
        raise OSError(f'Caught the above exceptions.')
