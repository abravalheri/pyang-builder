# -*- coding: utf-8 -*-
"""Components responsible for providing a ``FlentInterface``-like DSL."""

from pyang import statements as st
from pyangext.utils import check, create_context, dump, select

__author__ = "Anderson Bravalheri"
__copyright__ = "Copyright (C) 2016 Anderson Bravalheri"
__license__ = "mozilla"


class StatementWrapper(object):
    """Provides a elegant way of constructing YANG models.

    This class wraps functionality of
    :class:`Builder <..builder.Builder>` and :mod:`pyangext.utils`
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

        See :class:`Builder <..builder.Builder>`.
        """
        kwargs.setdefault('parent', self._statement)
        other_wrapper = self._builder.__call__(*args, **kwargs)
        self._statement.substmts.append(other_wrapper._statement)

        return other_wrapper

    def __getattr__(self, name):
        """Call ``__getattr__`` from builder, adding result as substatement.

        See :class:`Builder <..builder.Builder>`.
        """
        method = getattr(self._builder, name)
        parent = self._statement

        def _call(*args, **kwargs):
            kwargs.setdefault('parent', self._statement)
            other_wrapper = method(*args, **kwargs)
            parent.substmts.append(other_wrapper._statement)

            return other_wrapper

        return _call

    @property
    def arg(self):
        """Argument of the statement"""
        return self._statement.arg

    @property
    def keyword(self):
        """Keyword of the statement"""
        return self._statement.keyword

    @property
    def children(self):
        return ListWrapper([
            self.__class__(child, self._builder)
            for child in self._statement.substmts
        ])

    def dump(self, *args, **kwargs):
        """Returns the string representation of the YANG module.

        See :func:`pyangext.utils.dump`.
        """
        return dump(self._statement, *args, **kwargs)

    def find(self, *args, **kwargs):
        """find all children of the current node who match certain criteria.

        Arguments:
            keyword (str): if specified, a child should have this keyword
            arg (str): if specified, a child should have this argument

        ``keyword`` and ``arg`` can be also used as keyword arguments.

        Returns:
            list: nodes that matches the conditions
        """
        children = select(self._statement.substmts, *args, **kwargs)
        return ListWrapper(
            self.__class__(child, self._builder)
            for child in children
        )

    def unwrap(self):
        """Retrieve the inner ``pyang.statements.Statement`` object"""
        return self._statement

    def append(self, *children, **kwargs):
        """
        Add children statements

        Arguments:
            *children (pyang.statements.Statements): substatements to be added

        Keyword Arguments:
            copy (bool): If true, the node will be copied and not modified
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

        ctx_ = ctx or create_context()

        # do not mix validation errors with other errors
        old_errors = ctx_.errors
        ctx_.errors = []

        st.validate_module(ctx_, node)

        # look for errors and warnings
        check(ctx_)

        # restore old errors
        ctx_.errors = old_errors

        return node.i_is_validated

    def __repr__(self):
        """Unique representation for debugging purposes."""
        node = self._statement
        return '<{}.{}({} "{}") at {}>'.format(
            self.__module__, self.__class__.__name__,
            node.keyword, node.arg, hex(id(self)))


# --- Meta-Programing ---
#
# generates a parent class that wraps all the list methods that returns
# lists.
_list_methods = [
    '__add__', '__iadd__', '__reversed__',
    '__mul__', '__imul__', '__rmul__',
]

if hasattr(list, '__getslice__'):
    _list_methods.append('__getslice__')


# This new methods should return custom lists
def _wraper(method):
    """Wraps a list method to make it return a custom list"""

    def _wrapped(self, *args, **kwargs):
        result = method(self, *args, **kwargs)
        return self.__class__(result)

    _wrapped.__doc__ = method.__doc__
    _wrapped.__name__ = method.__name__

    return _wrapped

_CustomList = type('_CustomList', (list,), {
    method: _wraper(getattr(list, method))
    for method in _list_methods
})
# ---


class ListWrapper(_CustomList):
    """Provides a elegant way of searching YANG models.

    This class provides the same functionality of
    :method:`find() <pyang_builder.wrappers.StatementWrapper.find>`,
    but search for children of more than one node.
    """

    def __getitem__(self, index):
        """Wrap list.__getitem__ ensuring slices are wrapped objects"""
        result = super(ListWrapper, self).__getitem__(index)
        if isinstance(index, slice):
            return self.__class__(result)

        return result

    def invoke(self, method, *args, **kwargs):
        """Iter over the items invoking a method and collecting the results.

        The default behavior is create a new list and append each result of
        method call to the list. This can be changed passing ``extend=True``.

        Arguments:
            method (str): name of the method to be invoked.
            *args: list of arguments to be used to invoke ``method``.
            **kwargs: dict with keyword arguments to be used
                   to invoke ``method``.

        Keyword Arguments:
            extend (bool): if ``True`` the results of the method call
                will be assumed lists, and will be merged in the output list
                using the ``extend`` method.
        """
        results = self.__class__()
        if kwargs.get('extend'):
            accumulte = results.extend
            del kwargs['extend']
        else:
            accumulte = results.append

        for node in self:
            attr = getattr(node, method)
            accumulte(attr(*args, **kwargs))

        return results

    def pick(self, attr):
        """Iter over the items collecting an attribute.

        Arguments:
            attr (str): name of the attribute to be collected.
        """
        return self.__class__(getattr(item, attr) for item in self)

    def find(self, *args, **kwargs):
        """Find all children of node in the list who match certain criteria.

        Basically the ``find`` method is runned against each item in the
        list, the results are collected in a new list, which is wrapped and
        returned. This allows multiple ``find``s o be chained, e.g.::

            node = parse('''
                container {
                    leaf a { type "string"; }
                    leaf b { type "int"; }
                }
            ''')

            node.find('leaf').find('type')
            # => [<Statement (type string)>, <Statement (type int)>]


        See :meth:`StatementWrapper.find`.
        """
        kwargs['extend'] = True
        return self.invoke('find', *args, **kwargs)

    def __repr__(self):
        return '<{}.{} at {}: {}>'.format(
            self.__module__, self.__class__.__name__,
            hex(id(self)), super(ListWrapper, self).__repr__())
