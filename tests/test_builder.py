#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
"""
tests for YANG builder
"""
import pytest

from pyang_builder import StatementWrapper

__author__ = "Anderson Bravalheri"
__copyright__ = "Copyright (C) 2016 Anderson Bravalheri"
__license__ = "mozilla"


def test_call(Y):
    """
    calling build should build statements
    calling build directly with children should build nested statements
    """
    prefix = Y('prefix', 'test')
    assert prefix.dump().strip() == 'prefix test;'

    extension = Y('ext:c-define', 'INTERFACES')
    assert extension.dump().strip() == 'ext:c-define "INTERFACES";'

    module = Y('module', 'test', [
        Y('namespace', 'urn:yang:test'),
        Y('prefix', 'test'),
    ])

    assert module.dump().strip() == (
        'module test {\n'
        '  namespace "urn:yang:test";\n'
        '  prefix test;\n'
        '}'
    )

    assert module.validate()


def test_getattr(Y):
    """
    calling undefined method build should build statements
    double underscores should be transformed into prefix
    underscore should be transformed into dashes
    explicit prefix as named parameter should work
    """
    prefix = Y.prefix('test')
    assert prefix.dump().strip() == 'prefix test;'

    extension = Y.ext__c_define('INTERFACES')
    assert extension.dump().strip() == 'ext:c-define "INTERFACES";'

    extension = Y.c_define('INTERFACES', prefix='ext')
    assert extension.dump().strip() == 'ext:c-define "INTERFACES";'


def test_comment(Y):
    """
    single line comments should start with double-slashes
    """
    comment = Y.comment('comment test')
    assert comment.dump().strip() == '// comment test'

    comment = Y.comment('comment\ntest')
    assert comment.dump().strip() == (
        '/*\n'
        ' * comment\n'
        ' * test\n'
        ' */'
    )


def test_blankline(Y):
    """
    blank lines should be empty
    """
    blankline = Y.blankline()
    assert blankline.dump().strip() == ''


def test_from_tuple(Y):
    """
    should build entire (nested) (sub)trees
    should return argument if it is an StatementWrapper
    should always return StatementWrapper
    should raise TypeError if argument is not tuple,
        StatementWrapper or Statement
    """
    module = Y.from_tuple(
        ('module', 'test', [
            ('namespace', 'urn:yang:test'),
            ('prefix', 'test'),
            ('leaf', 'data', [('type', 'anyxml')])
        ])
    )

    assert module.dump().strip() == (
        'module test {\n'
        '  namespace "urn:yang:test";\n'
        '  prefix test;\n'
        '  leaf data {\n'
        '    type anyxml;\n'
        '  }\n'
        '}'
    )

    assert id(Y.from_tuple(module)) == id(module)
    assert isinstance(module, StatementWrapper)
    assert isinstance(Y.from_tuple(module.unwrap()), StatementWrapper)

    with pytest.raises(TypeError):
        Y.from_tuple('foobar')


def test_mix_from_tuple_and_regular(Y):
    """
    should build entire (nested) (sub)trees
    should return argument if it is an StatementWrapper
    should always return StatementWrapper
    should raise TypeError if argument is not tuple,
        StatementWrapper or Statement
    """
    module = Y.module('test', [
        ('namespace', 'urn:yang:test'),
        ('prefix', 'test'),
        Y.leaf('data', [('type', 'anyxml')]),
    ])

    assert isinstance(module, StatementWrapper)

    assert module.dump().strip() == (
        'module test {\n'
        '  namespace "urn:yang:test";\n'
        '  prefix test;\n'
        '  leaf data {\n'
        '    type anyxml;\n'
        '  }\n'
        '}'
    )


def test_statement_without_arg(Y):
    """
    Y should allow bypassing ``arg``  as positional argument,
        in other words, pass ``children`` after ``keyword``
    """
    module = Y('module', 'test', [
        Y.namespace('urn:yang:test'),
        Y.prefix('test'),
        Y.rpc('perform', Y.input(
            Y.leaf('name', Y.type('string'))
        )),
        Y.rpc('eval', Y(
            'input',
            Y.leaf('name', Y.type('string'))
        )),
    ])

    assert module.dump().strip() == (
        'module test {\n'
        '  namespace "urn:yang:test";\n'
        '  prefix test;\n'
        '  rpc perform {\n'
        '    input {\n'
        '      leaf name {\n'
        '        type string;\n'
        '      }\n'
        '    }\n'
        '  }\n'
        '  rpc eval {\n'
        '    input {\n'
        '      leaf name {\n'
        '        type string;\n'
        '      }\n'
        '    }\n'
        '  }\n'
        '}'
    )

    assert module.validate()
