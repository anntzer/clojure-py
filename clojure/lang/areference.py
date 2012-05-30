from clojure.lang.ireference import IReference
from clojure.lang.iprintable import IPrintable

class AReference(IReference, IPrintable):
    def __init__(self, meta = None):
        self._meta = meta

    def meta(self):
        return self._meta

    def alterMeta(self, fn, x, y):
        self._meta = fn(self._meta, x, y)

    def resetMeta(self, meta):
        self._meta = meta

    def writeAsString(self, writer):
        writer.write(repr(self))

    def writeAsReplString(self, writer):
        writer.write(repr(self))
