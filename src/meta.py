# Copyright (c) 2022, Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import signal
import typing
import threading
import abc


class TestCase:
    def __init__(self) -> None:
        self.name: str = ''
        self.timeout: int = 0

    @abc.abstractmethod
    def setup(self, watchdog=...) -> None:
        pass

    @abc.abstractmethod
    def run(self, watchdog=...) -> None:
        pass

    @abc.abstractmethod
    def cleanup(self, watchdog=...) -> None:
        pass


class TestRun:
    def __init__(self) -> None:
        self.name: str
        self.timeout: int = 0


class Watchdog:
    def __init__(self) -> None:
        # We will need to kill children first, so we will use a stack.
        self.pids: list[int] = [os.getpid()]
        self.timers: dict[typing.Union[TestRun, TestCase], threading.Timer] = {}

    def kill(self) -> None:
        while self.pids:
            os.kill(self.pids.pop(), signal.SIGTERM)

    def register(self, target: typing.Union[TestRun, TestCase]) -> None:
        assert(target not in self.timers)

        timer = threading.Timer(target.timeout, self.kill)
        # We want the timer to end if the main thread is terminated.
        timer.daemon = True
        timer.start()
        self.timers[target] = timer

    def unregister(self, target: typing.Union[TestRun, TestCase]) -> None:
        assert(target in self.timers)

        # This won't report any errors.
        self.timers[target].cancel()
        del self.timers[target]

    def add_pid(self, pid: int) -> None:
        self.pids.append(pid)

    def del_pid(self, pid: int) -> None:
        self.pids.remove(pid)
