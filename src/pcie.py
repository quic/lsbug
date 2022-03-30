# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

import re
import os
import errno
import multiprocessing
import sys

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


def consume_pcie_root(path: str, sysfs_error: SysfsError) -> None:
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
                finally:
                    f.close()

    sys.exit(count)


def read_pcie_sysfs(watchdog: meta.Watchdog) -> None:
    sysfs = '/sys/devices/'
    proc_map = {}
    sysfs_error = SysfsError()
    for entry in os.listdir(sysfs):
        if not re.match(r'pci\d+:\d+', entry):
            continue

        root_path = os.path.join(sysfs, entry)
        print(f'- Read files in {root_path}.')
        proc = multiprocessing.Process(target=consume_pcie_root, daemon=True,
                                       kwargs={'path': root_path, 'sysfs_error': sysfs_error})
        proc.start()
        proc_map[proc] = root_path

    # Ideally, we can convert those to non-blocking.
    for proc in proc_map:
        proc.join()
        print(f'- Finish reading {proc_map[proc]} for {proc.exitcode} files.')

    for file in sysfs_error.save:
        print(f'- {file}: {os.strerror(sysfs_error.save[file])}')

    if sysfs_error.save:
        raise OSError(f'Caught the above exceptions.')
