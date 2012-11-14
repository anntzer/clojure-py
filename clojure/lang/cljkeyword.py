from clojure.lang.atomicreference import AtomicReference
from clojure.lang.iprintable import IPrintable
from clojure.lang.ifn import IFn
from clojure.lang.named import Named
from clojure.lang.persistenthashmap import EMPTY as EMPTY_MAP
from clojure.lang.symbol import Symbol


class Keyword(IFn, Named, IPrintable):
    interned = AtomicReference(EMPTY_MAP)

    def __new__(cls, *args):
        """Keyword constructor.
        
        Argument(s) will be passed to Symbol() first.  If the keyword was
        already interned, it will be returned.
        """
        sym = Symbol(*args).withMeta(None)
        if sym in Keyword.interned.get():
            return Keyword.interned.get()[sym]
        obj = super(Keyword, cls).__new__(cls)
        obj.sym = sym
        obj.hash = hash(sym) + 0x9e3779b9
        Keyword.interned.mutate(
            lambda old: old if sym in old else old.assoc(sym, obj))
        return obj

    def __hash__(self):
        return self.hash

    def __call__(self, obj, notFound=None):
        if obj is None:
            return None
        if self not in obj:
            return notFound
        return obj[self]

    def __repr__(self):
        return ":{0}".format(self.sym)

    def getNamespace(self):
        return self.sym.getNamespace()

    def getName(self):
        return self.sym.getName()

    def writeAsString(self, writer):
        writer.write(repr(self))

    def writeAsReplString(self, writer):
        writer.write(repr(self))


def find(*args):
    if len(args) == 1 and isinstance(args[0], Symbol):
        return Keyword.interned.val()[args[0]]()
    if len(args) == 2:
        return find(Symbol(*args))


LINE_KEY = Keyword("line")
TAG_KEY = Keyword("tag")
T = Keyword("T")
