from abc import ABCMeta, abstractmethod

from clojure.lang.ifn import IFn
from clojure.lang.itransientmap import ITransientMap
import clojure.lang.rt as RT
from clojure.lang.iprintable import IPrintable

class ATransientMap(IFn, ITransientMap, IPrintable):
    __metaclass__ = ABCMeta

    @abstractmethod
    def ensureEditable(self):
        """Ensure that a transient object is editable.
        """

    @abstractmethod
    def doAssoc(self, key, val):
        """Add to an object an extra mapping from a key to a value.
        """

    @abstractmethod
    def doWithout(self, key):
        """Remove from an object an mapping given its key.
        """

    @abstractmethod
    def doValAt(self, key, notFound=None):
        """Return the mapping an object gives to a key.
        """

    @abstractmethod
    def doCount(self):
        """Count an object.
        """

    @abstractmethod
    def doPersistent(self):
        """Render a transient object persistent.
        """

    def conj(self, val):
        self.ensureEditable()
        return RT.conjToAssoc(self, val)

    def __call__(self, *args):
        return apply(self.valAt, args)

    def without(self, key):
        self.ensureEditable()
        return self.doWithout()

    def valAt(self, key, notFound = None):
        self.ensureEditable()
        return self.doValAt(key, notFound)

    def assoc(self, key, value):
        self.ensureEditable()
        return self.doAssoc(key, value)

    def count(self):
        self.ensureEditable()
        return self.count()

    def persistent(self):
        self.ensureEditable()
        return self.persistent()

    def writeAsString(self, writer):
        writer.write(repr(self))

    def writeAsReplString(self, writer):
        writer.write(repr(self))
