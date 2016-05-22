# -*- coding: utf-8 -*-
"""Factory for programmatic generation of a YANG Abstract Syntax Tree."""
from pyang import statements as st
from pyang.error import Position
from pyangext.definitions import PREFIX_SEPARATOR

from .wrappers import StatementWrapper

__author__ = "Anderson Bravalheri"
__copyright__ = "Copyright (C) 2016 Anderson Bravalheri"
__license__ = "mozilla"


class Builder(object):
    """Statement generator factory for YANG modeling language.

    The ``Builder`` class provides an easy way of generating and printing
    YANG documents.
    Internally it represents the models in a
    `Syntax Tree (AST) <https://en.wikipedia.org/wiki/Abstract_syntax_tree>`_.
    In this sense each statement of the YANG model is considered to be a
    node in a Tree-like data structure. Each node of this structure has
    a ``keyword``, an ``arg`` (argument) and some ``children``.
    For example, the statement ``leaf name { type string }``, corresponds
    to a node with the keyword ``leaf``, the arg ``name`` and a children
    list with one more node object (this one has keyword ``type`` and
    argument ``string``).


    Usage
    -----

    The Builder class needs to be instantiated for usage. It is recomended
    to pass a string as first argument for debugging purposes, for example::

        Y = Builder('my-awesome-module')

    If an undefined method is called from builder, the name of the
    method is used as keyword for the node. Underscore are replaced
    by dashes and duble underscores denote separation of a prefix::

        >>> Y.leaf_list('allow-user', [
                Y.type('string'), Y.description('username')
            ]).dump()
        # => 'leaf-list allow-user {
        #       type string;
        #       description "username";
        #     }'
        >>> Y.ext__c_define(
                'INTERFACES', Y.if_feature('local-storage')).dump()
        # => 'ext:c-define "INTERFACES" {
        #       if-feature local-storage;
        #     }'

    When the builder itself is called, the first argument is used as
    keyword for the statement and the second is used as its argument.
    Optional child (or a children list) and parent nodes can be passed::

        >>> Y('ext:c-define', 'INTERFACES',
                     Y.if_feature('local-storage'), parent=module).dump()
        # => 'ext:c-define "INTERFACES" {
        #       if-feature local-storage;
        #     }'

    A child can be a node or a tuple (in case of children list,
    both can be mixed togheter). If a tuple is passed, the method
    :meth:`from_tuple() <pyang_builder.builder.Bulder.from_tuple>`
    is used to transform it into a node::

        >>> Y.leaf_list('allow-user', [
                ('type', 'string'),
                Y.description('username'),
            ]).dump()
        # => 'leaf-list allow-user {
        #       type string;
        #       description "username";
        #     }'

    The nodes produced by Builder are wrapped as
    :class:`StatementWrapper <pyang_builder.wrappers.StatementWrapper>`
    objects. This objects can be called similarly to builder, but the
    produced nodes are automatically appended as children::

        >>> tl = Y.leaf_list('text-lines')
        >>> tl.type('string')
        >>> tl.description('lines of a text')
        >>> tl.dump()
        # => 'leaf-list text-lines {
        #       type string;
        #       description "lines of a text";
        #     }'

    .. note:: Since methods cannot be named ``import`` in python,
        use the ``call`` style::

            Y('import', 'my-module-name', Y.prefix('my'))

    .. note:: Builder is stateful, it means it cannot be shared among
        threads or even used to build multiple trees simultaneously.

    """
    def __init__(self, name='builder-generated', top=None, keyword='module'):
        """Initialize builder.

        Arguments:
            name (str): optional name for a hypothetical output module.
                Note that this argument may be used for debbuging purposes,
                usually the syntax errors will threat this string as a
                filename. If no name is provided, the string
                ``builder-generated`` is used.
            top (pyang.statements.Statement): optional outer-most statement
                where the subtree will be placed. There is no need to pass
                this argument: the Builder itself will generate a top
                statement. Just use it if you plan to append the generated
                subtree to a pre-existing statement.
        """
        self._pos = (top and top.pos) or Position(name)

        # Creates a dummy outermost module statement to simplify
        # traversing tree logic
        self._top = top or st.Statement(None, None, self._pos, 'module', name)

        if not self._pos.top:
            self._pos.top = self._top

    def __call__(self, keyword, arg=None, children=None, parent=None):
        """Magic method to generate YANG statements.

        Arguments:
            keyword (str): string to be used as keyword for the statement
            arg (str): argument of the statement

        Keyword Arguments:
            children: optional statement or list to be inserted as substatement
            parent (pyang.statements.Statement): optional parent statement

        Returns:
            StatementWrapper: wrapper around ``pyang.statements.Statement``.
                call ``unwrap`` if direct access is necessary.
        """
        children = children or []

        if isinstance(arg, (list, tuple, st.Statement, StatementWrapper)):
            children = arg
            arg = None

        if not isinstance(children, list):
            children = [children]

        if arg in (False, True):
            arg = str(arg).lower()

        if keyword in ('module', 'submodule'):
            node = self._top
            node.keyword = keyword
            node.arg = arg
            node.i_module = node
        else:
            parent_node = (
                parent.unwrap()
                if isinstance(parent, StatementWrapper)
                else parent
            )

            node = st.Statement(
                self._top, parent_node, self._top.pos, keyword, arg)
            node.i_module = self._top

        unwraped_children = []
        for child in children:
            if isinstance(child, StatementWrapper):
                unwraped = child.unwrap()
            elif isinstance(child, tuple):
                unwraped = self.from_tuple(child).unwrap()
            else:
                unwraped = child
            unwraped.parent = node
            unwraped_children.append(unwraped)

        node.substmts = unwraped_children

        return StatementWrapper(node, self)

    def __getattr__(self, keyword):
        """Magic method to generate YANG statements."""
        keyword = keyword.replace('__', ':').replace('_', '-')
        build = self.__call__

        def _factory(arg=None, children=None, prefix=None, **kwargs):
            node_type = keyword
            if prefix is not None:
                node_type = PREFIX_SEPARATOR.join([prefix, keyword])

            return build(node_type, arg, children, **kwargs)

        return _factory

    def blankline(self):
        """Insert a empty line."""
        return self.__call__('_comment', ' ')

    def comment(self, text, parent=None):
        """Generate a comment node.

        Arguments:
            text (str): content of the comment
        """
        lines = text.strip().splitlines()
        if len(lines) == 1:
            text = '// ' + lines[0]
        else:
            text = (
                '/*\n' +
                '\n'.join(['* ' + line for line in lines]) +
                '\n*/'
            )

        return self.__call__('_comment', text, parent=parent)

    def from_tuple(self, texp, parent=None):
        """Generates a YANG statement form a tuple-expression

        Here the tuple-expression is considered a tuple (nested or not)
        in the form::

            (<keyword>, <arg>, <children>)

        Consider the following YANG statement::

            container error {
              leaf code { type int32; }
              leaf message { type string; }
            }

        The equivalent tuple-expression is::

            ('container', 'error', [
                ('leaf', 'code', [('type', 'int32')]),
                ('leaf', 'message', [('type', 'string')]),
            ])

        For comments use ``_comment`` as keyword.
        Note that children should be a list

        Arguments:
            texp (tuple): tuple-expression representation of statement
            parent (pyang.statements.Statement): optional parent statement

        Example:
            The statement `leaf counter { type int32; }` can be generated by::

                builder.from_tuple(('leaf', 'counter', [('type', 'int32')]))

        See :meth:`Builder.__call__`.
        """
        if isinstance(texp, st.Statement):
            return StatementWrapper(texp, self)

        if isinstance(texp, StatementWrapper):
            return texp

        if not isinstance(texp, tuple):
            raise TypeError(
                'argument should be tuple, %s given', type(texp))

        last = texp[-1]
        if isinstance(last, list):
            node = self(*texp[:-1], parent=parent)
            for child in last:
                node.append(self.from_tuple(child, parent=node))

            return node

        return self(*texp, parent=parent)
