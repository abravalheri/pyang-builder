# -*- coding: utf-8 -*-
"""
The ``pyang_builder`` module exposes an API for ``programatical`` generation
of YANG modules.

Using the :mod:`Builder <pyang_builder.builder.Builder>`, it is possible to
dinamically generate a
`Syntax Tree <https://en.wikipedia.org/wiki/Abstract_syntax_tree>`_ that can
be dumped into a document following the
`YANG modeling language syntax <https://tools.ietf.org/html/rfc6020>`_.

Almost all methods of :mod:`Builder <pyang_builder.builder.Builder>`
returns instances of the
:mod:`StatementWrapper <pyang_builder.wrappers.StatementWrapper>` class.
This is a design decision in order to provide a beautiful DSL-like API.
"""
import pkg_resources

try:
    __version__ = pkg_resources.get_distribution(__name__).version
except:  # pylint: disable=bare-except
    __version__ = 'unknown'

from .builder import Builder
from .wrappers import StatementWrapper

__all__ = ['Builder', 'StatementWrapper']
