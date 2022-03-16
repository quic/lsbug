#!/usr/bin/env python3

# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import signal
import typing
import threading


class TestCase:
    def __init__(self) -> None:
        self.name: str
        self.timeout: int = 0
        self.run: typing.Callable[..., None] = lambda: None
        self.setup: typing.Callable[..., None] = lambda: None
        self.cleanup: typing.Callable[..., None] = lambda: None


class TestRun:
    def __init__(self) -> None:
        self.name: str
        self.timeout: int = 0
        self.run: typing.Callable[..., None] = lambda: None


class Watchdog:
    def __init__(self) -> None:
        self.pids: set[int] = set()
        self.timers: dict[typing.Union[TestRun, TestCase], threading.Timer] = {}

    def kill(self) -> None:
        while self.pids:
            os.kill(self.pids.pop(), signal.SIGTERM)

    def register(self, target: typing.Union[TestRun, TestCase]) -> None:
        assert(target not in self.timers)

        timer = threading.Timer(target.timeout, self.kill)
        timer.start()
        self.timers[target] = timer

    def unregister(self, target: typing.Union[TestRun, TestCase]) -> None:
        assert(target in self.timers)

        # This won't report any errors.
        self.timers[target].cancel()
        del self.timers[target]

    def add_pid(self, pid: int) -> None:
        self.pids.add(pid)

    def del_pid(self, pid: int) -> None:
        self.pids.remove(pid)
