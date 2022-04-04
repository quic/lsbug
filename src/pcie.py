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
        self._allow: dict[str, int] = {
            'autosuspend_delay_ms': errno.EIO
        }

    @property
    def allow(self) -> dict[str, int]:
        return self._allow


def check_pcie_sysfs(watchdog: meta.Watchdog) -> None:
    for entry in os.listdir('/sys/devices'):
        if re.match(r'pci\d+:\d+', entry):
            return

    raise OSError('No PCIe root port found.')


def consume_pcie_root(path: str, sysfs_error: SysfsError, save_errors: dict[str, int]) -> None:
    count = 0
    for root, dirs, files in os.walk(top=path):
        # We are not going to read all devices' directories due to file-read many errors.
        dirs[:] = [entry for entry in dirs if not re.match(r'[0-9a-z]+:[0-9a-z]+:[0-9a-z]+\.[0-9a-z]+', entry)]

        for entry in files:
            file = os.path.join(root, entry)
            if os.access(file, os.R_OK):
                # we might get decoding errors without 'b'.
                f = open(file, 'rb')
                try:
                    count += 1
                    f.read()
                except OSError as e:
                    if entry in sysfs_error.allow and sysfs_error.allow[entry] == e.errno:
                        pass
                    else:
                        print(f'- Error: {file} - {e}', file=sys.stderr)
                        save_errors[entry] = e.errno
                finally:
                    f.close()

    sys.exit(count)


def read_pcie_sysfs(watchdog: meta.Watchdog) -> None:
    sysfs = '/sys/devices/'
    proc_map = {}
    sysfs_error = SysfsError()
    save_errors = multiprocessing.Manager().dict()
    for entry in os.listdir(sysfs):
        if not re.match(r'pci\d+:\d+', entry):
            continue

        root_path = os.path.join(sysfs, entry)
        print(f'- Read files in {root_path}.')
        proc = multiprocessing.Process(target=consume_pcie_root, daemon=True,
                                       kwargs={'path': root_path, 'sysfs_error': sysfs_error,
                                               'save_errors': save_errors})
        proc.start()
        proc_map[proc] = root_path

    # Ideally, we can convert those to non-blocking.
    for proc in proc_map:
        proc.join()
        print(f'- Finish reading {proc_map[proc]} for {proc.exitcode} files.')

    for file in save_errors:
        print(f'- {file}: {os.strerror(save_errors[file])}')

    if save_errors:
        raise OSError(f'Caught the above exceptions.')
