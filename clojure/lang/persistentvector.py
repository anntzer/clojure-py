from clojure.lang import rt as RT
from clojure.lang.apersistentvector import APersistentVector


_not_supplied = object()


class PersistentVector(tuple, APersistentVector):
    def __new__(cls, iterable, meta=None):
        return tuple.__new__(PersistentVector, iterable)

    def __init__(self, iterable, meta=None):
        self._meta = meta

    __call__ = tuple.__getitem__

    def nth(self, idx, not_found=_not_supplied):
        try:
            return self[idx]
        except IndexError:
            if not_found is _not_supplied:
                raise
            return not_found

    def meta(self):
        return self._meta

    def withMeta(self, meta):
        return PersistentVector(self, meta)

    def assoc(self, idx, val):
        if 0 <= idx <= len(self):
            return PersistentVector(self[:idx] + (val,) + self[idx+1:], self._meta)
        else:
            raise IndexError

    assocN = assoc

    def cons(self, val):
        return PersistentVector(self + (val,), self._meta)

    def empty(self):
        return PersistentVector((), self._meta)

    def pop(self):
        return PersistentVector(self[:-1], self._meta)

    # overrides APersistenVector
    __iter__ = tuple.__iter__
    __getitem__ = tuple.__getitem__
    count = tuple.__len__

    def peek(self):
        return self[-1]

    # seq, count, __eq__, __hash__, __ne__ missing


def vec(seq):
    if isinstance(seq, APersistentVector):
        return seq
    else:
        seq = RT.seq(seq)
        l = []
        while seq:
            l.append(seq.first())
            seq = RT.next(seq)
        return PersistentVector(l)


def create(*args):
    return PersistentVector(args)


EMPTY = PersistentVector(())
