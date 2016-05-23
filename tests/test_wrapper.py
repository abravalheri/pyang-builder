#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
"""
tests for Statement Wrapper
"""
import pytest

from pyang.statements import Statement

from pyangext.utils import create_context

from pyang_builder import StatementWrapper

__author__ = "Anderson Bravalheri"
__copyright__ = "Copyright (C) 2016 Anderson Bravalheri"
__license__ = "mozilla"


@pytest.fixture
def container(Y):
    """Sample container"""
    return Y.container('outer', [
        ('leaf', 'id', [('type', 'int32')]),
        ('leaf', 'name', [('type', 'string')]),
    ])


def test_dump(Y):
    """
    dump should correctly print wrapper
    wrapper should dump itself
    """
    module = Y.module('test', [
        Y.prefix('test'),
        Y.namespace('urn:yang:test')
    ])

    assert module.dump().strip() == (
        'module test {\n'
        '  namespace "urn:yang:test";\n'
        '  prefix test;\n'
        '}'
    )


def test_attribute(Y):
    """
    wrapper should allow direct attribute
    """
    module = Y.module('test')
    module.prefix('test')
    module.namespace('urn:yang:test')

    assert module.dump().strip() == (
        'module test {\n'
        '  namespace "urn:yang:test";\n'
        '  prefix test;\n'
        '}'
    )

    assert module.validate()


def test_call(Y):
    """
    wrapper should allow direct call
    """
    module = Y('module', 'test')
    module('prefix', 'test')
    module('namespace', 'urn:yang:test')

    assert module.dump().strip() == (
        'module test {\n'
        '  namespace "urn:yang:test";\n'
        '  prefix test;\n'
        '}'
    )

    assert module.validate()


def test_mix_builder(Y):
    """
    builder should mix with pyang standard
    """
    module = Y(
        'module', 'test',
        Statement(None, None, None, 'namespace', 'urn:yang:test')
    )
    module('prefix', 'test')
    module.append(Y.from_tuple(
        ('leaf', 'data', [('type', 'string')])
    ))

    assert module.dump().strip() == (
        'module test {\n'
        '  namespace "urn:yang:test";\n'
        '  prefix test;\n'
        '  leaf data {\n'
        '    type string;\n'
        '  }\n'
        '}'
    )

    assert module.validate()


def test_unwrap(Y):
    """
    unwrap should return pyang.statements.Statement
    """
    module = Y('module', 'test')
    assert isinstance(module.unwrap(), Statement)


def test_validate(Y):
    """
    validate should not allow non top-level statements
    module with namespace, prefix and revision should be valid
    validated modules should have i_children with all ``uses`` expanded
    validated modules should not have typedefs or extensions in i_children
    """
    leaf = Y.leaf('name', Y.type('string'))

    with pytest.raises(ValueError):
        leaf.validate()

    ctx = create_context()
    ref = Y.module('test1', [
        ('namespace', 'urn:yang:test'),
        ('prefix', 'test'),
        ('revision', '1988-07-03'),
        ('grouping', 'grouping-root', [
            ('leaf', 'leaf1', [
                ('type', 'string')
            ]),
            ('grouping', 'grouping1', [
                ('leaf', 'grouping1-leaf', [
                    ('type', 'string')
                ]),
            ]),
            ('typedef', 'type1', [('type', 'int')]),
            ('grouping', 'grouping2', [
                ('leaf-list', 'grouping2-leaf-list', [
                    ('type', 'type1')
                ]),
            ]),
            ('uses', 'grouping2'),
            ('extension', 'extension1')
        ]),
    ])

    ctx.add_module('test1', ref.dump())

    module = Y.module('test', [
        ('namespace', 'urn:yang:test'),
        ('prefix', 'test'),
        ('import', 'test1', [('prefix', 'test1')]),
        ('revision', '1988-07-03'),
        ('uses', 'test1:grouping-root')
    ])

    assert module.validate(ctx)
    raw_module = module.unwrap()
    assert len(raw_module.i_children) == 2
    assert raw_module.i_children[0].arg == 'leaf1'
    assert raw_module.i_children[1].arg == 'grouping2-leaf-list'
    assert not [
        child for child in raw_module.i_children
        if child.keyword == 'typedef']
    assert not [
        child for child in raw_module.i_children
        if child.keyword == 'extension']


def test_validate_with_warnings(Y):
    """
    should be valid even if AST is not exactly proper
    """
    module = Y.module('test', [
        Y.namespace('urn:yang:test'),
        Y.prefix('test'),
        Y('import', 'ietf-yang-types', Y.prefix('ietf')),  # warning: unused
        Y.revision('2008-01-02', Y.description('first update')),
        Y.revision('2009-01-02', Y.description('second update')),
        # warning: not reverse order
        Y.typedef('myint', Y.type('int32')),  # warning: unused
        Y.grouping('unused', [  # warning: unused
            Y.list('user', [
                Y.key('id'), Y.leaf('name', Y.type('string')),
                Y.leaf('id', [Y.type('int32'), Y.default(0)]),
            ])  # warning: key+default
        ]),
        Y.leaf('group', [
            Y.type('string'),
            Y.mandatory(False),  # warning
            Y.config(True),  # warning
        ]),
    ])

    with pytest.warns(SyntaxWarning):
        assert module.validate()


def test_find(container):
    """
    should find direct substatements by keyword + arg
    should find direct substatements by keyword
    should find direct substatements by arg
    should return StatementWrapper
    should not ignore prefix if no ``ignore_prefix`` were passed
    should ignore prefix in keyword if ``ignore_prefix`` were passed
    should ignore prefix in arg if ``ignore_prefix`` were passed
    """
    assert container.find('leaf', 'name')

    assert len(container.find('leaf')) == 2

    name = container.find(arg='name')
    assert name

    assert isinstance(name[0], StatementWrapper)

    container('ext:myext', 'ext:value')
    assert not container.find('myext')
    assert not container.find(arg='value')
    assert container.find('myext', ignore_prefix=True)
    assert container.find(arg='value', ignore_prefix=True)


def test_append(Y, container):
    """
    Append should accept N (mixed) arguments
    Append without copy should reuse node
    Append with copy should build a new node
    """
    other_ext = Statement(None, None, None, 'other:ext', 'other:ipsun')
    container.append(
        Y.description('loren ipsum'),
        Y('ext:loren', 'ipsun'),
        other_ext
    )

    assert container.find('description')
    assert container.find('ext:loren')
    assert len(container.find(arg='ipsun', ignore_prefix=True)) == 2

    result = container.find('other:ext')[0].unwrap()
    assert id(result) == id(other_ext)

    container.append(
        Y.description('loren ipsum'),
        Y('ext:loren', 'ipsun'),
        other_ext,
        copy=True
    )

    result = container.find('other:ext')[-1].unwrap()
    assert id(result) != id(other_ext)
