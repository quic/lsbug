# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

import os
import signal
import typing
import threading
import dataclasses


@dataclasses.dataclass(frozen=True)
class TestCase:
    name: str
    timeout: int
    run: typing.Callable[[Watchdog], None]
    setup: typing.Callable[[Watchdog], None] = lambda x: None
    cleanup: typing.Callable[[Watchdog], None] = lambda x: None


@dataclasses.dataclass(frozen=True)
class TestRun:
    timeout: int


class Watchdog:
    def __init__(self) -> None:
        # We will need to kill children first, so we will use a stack.
        self._pids: list[int] = [os.getpid()]
        self._timers: dict[typing.Union[TestRun, TestCase], threading.Timer] = {}
        # We can use it to pass values within a test case.
        self._storage: dict[typing.Any, typing.Any] = {}

    @property
    def storage(self) -> dict[typing.Any, typing.Any]:
        return self._storage

    def kill(self) -> None:
        while self._pids:
            os.kill(self._pids.pop(), signal.SIGTERM)

    def register(self, target: typing.Union[TestRun, TestCase]) -> None:
        if target.timeout == 0:
            return

        assert target not in self._timers

        timer = threading.Timer(interval=target.timeout, function=self.kill)
        # We want the timer to end if the main thread is terminated.
        timer.daemon = True
        timer.start()
        self._timers[target] = timer

    def unregister(self, target: typing.Union[TestRun, TestCase]) -> None:
        if target.timeout == 0:
            return

        assert target in self._timers

        # This won't report any errors.
        self._timers[target].cancel()
        del self._timers[target]

    def add_pid(self, pid: int) -> None:
        self._pids.append(pid)

    def del_pid(self, pid: int) -> None:
        self._pids.remove(pid)
