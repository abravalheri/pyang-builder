#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
"""
tests for List Wrapper
"""
from itertools import chain

import pytest

from pyang_builder.wrappers import ListWrapper, StatementWrapper

__author__ = "Anderson Bravalheri"
__copyright__ = "Copyright (C) 2016 Anderson Bravalheri"
__license__ = "mozilla"


def test_coerce_iterators():
    """
    constructor should coerce iterations into class
    """
    assert ListWrapper(chain([0, 1], [2, 3])) == ListWrapper([0, 1, 2, 3])


def test_methods_should_be_wrapped():
    """
    methods that return lists should wrap response
    """
    x = ListWrapper([0, 1, 2, 3])
    assert isinstance(x + [1], ListWrapper)
    x += [1]
    assert isinstance(x, ListWrapper)
    x *= 2
    assert isinstance(x, ListWrapper)
    assert isinstance(x[1:], ListWrapper)
    x.reverse()
    assert isinstance(x, ListWrapper)
    x.sort()
    assert isinstance(x, ListWrapper)
    x.extend([2, 4, 5])
    assert isinstance(x, ListWrapper)


@pytest.fixture
def container(Y):
    """Sample container"""
    return Y.container('outer', [
        ('leaf', 'id', [('type', 'int32')]),
        ('leaf', 'name', [('type', 'string')]),
    ])


def test_find_supports_chain(container):
    """
    find should return wrapper
    find should support chain
    find results should be StatementWrappers
    find results should be in order
    """
    leafs = container.find('leaf')
    assert isinstance(leafs, ListWrapper)
    types = leafs.find('type')
    assert len(types) == 2
    assert all(isinstance(node, StatementWrapper) for node in types+leafs)
    assert list(types.pick('arg')) == ['int32', 'string']
