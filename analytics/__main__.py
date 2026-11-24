"""Lets the package run as a program: python -m analytics --help"""

import sys

from .cli import main

sys.exit(main())
