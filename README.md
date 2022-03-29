# A collection of Linux kernel tests for arm64 servers

## Introduction
We will need Python 3.8+ to run this as an unprivileged user, so it can help
find any security holes as well. The intention is to run this on bare-metal
servers, so it can exercise as many platform features as possible.

## Usage
To run the unit tests for the tests:
```
$ pytest -v check.py
```

To run the actual arm64 tests:
```
$ <path>/lsbug.py
```

## License
The code is licensed under GPL-2.0+.
