#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Dummy conftest.py for pyang-builder.

    If you don't know what this is for, just leave it empty.
    Read more about conftest.py under:
    https://pytest.org/latest/plugins.html
"""
from __future__ import absolute_import, division, print_function

import pytest

from pyang_builder import Builder


@pytest.fixture
def Y():
    """YANG Builder"""
    return Builder()
