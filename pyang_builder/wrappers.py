# -*- coding: utf-8 -*-
"""Components responsible for providing a ``FlentInterface``-like DSL."""
from pyang import statements as st
from pyangext.utils import create_context, dump, select

__author__ = "Anderson Bravalheri"
__copyright__ = "Copyright (C) 2016 Anderson Bravalheri"
__license__ = "mozilla"


class StatementWrapper(object):
    """Provides a elegant way of constructing YANG models.

    This class wraps functionality of
    :mod:`Builder <pyang_builder.builder.Builder>` and ``pyangext.utils``
    in an object oriented chainable way.
    """

    def __init__(self, statement, builder):
        """Create a builder wrapper around ``pyang.statements.Statement``.

        This wrapper can be used to generate substatements, or dump the
        syntax tree as a YANG string representation.

        Example:
        ::
            >>> from pyang_builder import Builder
            >>> Y = Builder('desired-module-name')
            >>> wrapper = Y.leaf_list('allow-user')
            >>> wrapper.type('string')
            >>> wrapper.dump()
            # => 'leaf-list allow-user {
            #       type string;
            #     }'
        """
        self._statement = statement
        self._builder = builder

    def __call__(self, *args, **kwargs):
        """Call ``__call__`` from builder, adding result as substatement.

        See :meth:`Builder.__call__`.
        """
        kwargs.setdefault('parent', self._statement)
        other_wrapper = self._builder.__call__(*args, **kwargs)
        self._statement.substmts.append(other_wrapper._statement)

        return other_wrapper

    def __getattr__(self, name):
        """Call ``__getattr__`` from builder, adding result as substatement.

        See :meth:`Builder.__getattr__`.
        """
        method = getattr(self._builder, name)
        parent = self._statement

        def _call(*args, **kwargs):
            kwargs.setdefault('parent', self._statement)
            other_wrapper = method(*args, **kwargs)
            parent.substmts.append(other_wrapper._statement)

            return other_wrapper

        return _call

    def dump(self, *args, **kwargs):
        """Returns the string representation of the YANG module.

        See :func:`dump`.
        """
        return dump(self._statement, *args, **kwargs)

    def find(self, *args, **kwargs):
        """Find by a substatement by keyword, or argument or both.

        See :func:`select`.
        """
        children = select(self._statement.substmts, *args, **kwargs)
        return [type(self)(child, self._builder) for child in children]

    def unwrap(self):
        """Retrieve the inner ``pyang.statements.Statement`` object"""
        return self._statement

    def append(self, *children, **kwargs):
        """
        Add children statements

        Arguments:
            *children (pyang.statements.Statements): substatements to be added

        Keyword Arguments:
            copy (boolean): If true, the node will be copied and not modified
                in place

        Returns:
            StatementWrapper: wrapper itself
        """
        statement = self._statement
        substatements = statement.substmts
        copy = kwargs.get('copy')

        for child in children:
            sub = (
                child._statement if isinstance(child, StatementWrapper)
                else child
            )
            if copy:
                sub = sub.copy(statement)
            else:
                sub.parent = statement
            substatements.append(sub)

        return self

    def validate(self, ctx=None):
        """Validates the syntax tree.

        Should be called just from ``module``, ``submodule`` statements.

        Arguments:
            ctx (pyang.Context): object generated from pyang parsing
        """
        node = self._statement
        if node.keyword not in ('module', 'submodule'):
            raise ValueError(
                'Cannot validate `%s`, only top-level statements '
                '(module, submodule)', node.keyword)

        st.validate_module(ctx or create_context(), node)

        return node.i_is_validated

    def __repr__(self):
        """Unique representation for debugging purposes."""
        node = self._statement
        return '<{}.{}({} "{}") at {}>'.format(
            self.__module__, type(self).__name__,
            node.keyword, node.arg, hex(id(self)))
