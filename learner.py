# -*- coding: utf-8 -*-

from functools import reduce as fold
from discopy import cat, config
from discopy.moncat import Ob, Ty, Box, Diagram, MonoidalFunctor


if config.JAX:
    import warnings
    for msg in config.IGNORE:
        warnings.filterwarnings("ignore", message=msg)
    import jax.numpy as np
else:
    import numpy as np


class Dim(Ty):
    """ Implements dimensions as tuples of non-negative integers.
    Dimensions form a monoid with product @ and unit Dim(0).

    >>> Dim(0) @ Dim(1) @ Dim(2)
    Dim(1, 2)
    """
    def __init__(self, *xs):
        """
        >>> len(Dim(2, 3, 4))
        3
        >>> len(Dim(1, 2, 3))
        3
        >>> Dim(-1)  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        ValueError: Expected non-negative integer, got -1 instead.
        """
        for x in xs:  # pylint: disable=invalid-name
            if not isinstance(x, int) or x < 0:
                raise ValueError("Expected non-negative integer, "
                                 "got {} instead.".format(repr(x)))
        self._dim = sum(xs)
        super().__init__(*[Ob(x) for x in xs if x > 0])

    @property
    def dim(self):
        """
        >>> assert Dim(2, 3).dim == 5
        """
        return self._dim

    def __matmul__(self, other):
        """
        >>> assert Dim(0) @ Dim(2, 3) == Dim(2, 3) @ Dim(0) == Dim(2, 3)
        """
        return Dim(*[x.name for x in super().__matmul__(other)])

    def __add__(self, other):
        """
        >>> assert sum([Dim(0), Dim(2, 3), Dim(4)], Dim(0)) == Dim(2, 3, 4)
        """
        return self @ other

    def __getitem__(self, key):
        """
        >>> assert Dim(2, 3)[:1] == Dim(3, 2)[1:] == Dim(2)
        >>> assert Dim(2, 3)[0] == Dim(3, 2)[1] == 2
        """
        if isinstance(key, slice):
            return Dim(*[x.name for x in super().__getitem__(key)])
        return super().__getitem__(key).name

    def __iter__(self):
        """
        >>> [n for n in Dim(2, 3, 4)]
        [2, 3, 4]
        """
        for i in range(len(self)):
            yield self[i]

    def __repr__(self):
        """
        >>> Dim(0, 1, 2)
        Dim(1, 2)
        """
        return "Dim({})".format(', '.join(map(repr, self)) or '1')

    def __str__(self):
        """
        >>> print(Dim(0, 1, 2))
        Dim(1, 2)
        """
        return repr(self)

    def __hash__(self):
        """
        >>> dim = Dim(2, 3)
        >>> {dim: 42}[dim]
        42
        """
        return hash(repr(self))


class Function(Box):
    """ Wraps functions on lists with domain and codomain information
    """
    def __init__(self, dom, cod, function):
        """
        >>> Function(Dim(2), Dim(2), lambda x: x)
        """
        dom, cod = Dim(*dom), Dim(*cod)
        self._function = function
        super().__init__(function, dom, cod)

    @property
    def function(self):
        return self._function

    def __call__(self, value):
        """
        >>> Function(Dim(2), Dim(2), lambda x: x)([1, 2])
        [1, 2]
        """
        if not isinstance(value, list):
            raise ValueError(
                "List expected, got {} instead.".format(repr(value)))
        if not len(value) == self.dom.dim:
            raise AxiomError("Input length {} does not agree with dimension {}"
                             .format(len(value), sum(x[i] for x in self.dom)))
        return self.function(value)

    def then(self, other):
        """
        >>> m = Function(Dim(2), Dim(2), lambda x: x[::-1])
        >>> assert (m >> m)([1, 0]) == [1, 0]
        """
        if not isinstance(other, Function):
            raise ValueError(
                "Function expected, got {} instead.".format(repr(other)))
        if self.cod != other.dom:
            raise AxiomError("{} does not compose with {}."
                             .format(repr(self), repr(other)))

        def function(x):
            return other(self(x))
        return Function(self.dom, other.cod, function)

    def tensor(self, other):
        """
        >>> f = Function(Dim(2), Dim(1), lambda x: [x[0] + x[1]])
        >>> g = Function(Dim(1), Dim(2), lambda x: x + x)
        >>> assert (f @ g)([0, 1, 2]) == [1, 2, 2]
        """
        if not isinstance(other, Function):
            raise ValueError(
                "Function expected, got {} instead.".format(repr(other)))
        dom, cod = self.dom @ other.dom, self.cod @ other.cod

        def function(x):
            return self(x[:self.dom.dim]) + other(x[self.dom.dim:])
        return Function(dom, cod, function)