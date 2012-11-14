from clojure.lang.apersistentmap import APersistentMap
from clojure.lang.persistentvector import PersistentVector
from clojure.lang.ipersistentvector import IPersistentVector
from clojure.lang.ieditablecollection import IEditableCollection
from clojure.lang.iobj import IObj
from clojure.lang.mapentry import MapEntry


class PersistentHashMap(dict, APersistentMap, IEditableCollection, IObj):
    def __init__(self, mapping, meta=None):
        dict.__init__(self, mapping)
        self._meta = meta
        #print "init", self

    def __setitem__(self, key, val):
        raise TypeError

    def meta(self):
        return self._meta

    def withMeta(self, meta):
        return PersistentHashMap(self, meta=meta)

    def assoc(self, key, val):
        copy = self.copy()
        copy[key] = val
        return PersistentHashMap(copy)

    def without(self, key):
        copy = self.copy()
        copy.pop(key, None)
        return PersistentHashMap(copy)

    def valAt(self, key, not_found=None):
        return self.get(key, not_found)

    __call__ = __getitem__ = valAt

    def entryAt(self, key):
        return MapEntry(key, self.get(key, None))

    def seq(self):
        return PersistentVector([it for it in self.iteritems()]).seq()

    __contains__ = containsKey = dict.has_key

    toDict = lambda self: dict(self)

    def cons(self, o):
        if isinstance(o, MapEntry):
            return self.assoc(o.getKey(), o.getValue())
        if isinstance(o, IPersistentVector):
            if len(o) != 2:
                raise InvalidArgumentException("Vector arg to map conj must "
                                               "be a pair")
            return self.assoc(o[0], o[1])
        ret = self
        s = o.seq()
        while s is not None:
            e = s.first()
            ret = ret.assoc(*e)
            s = s.next()
        return ret

def fromDict(d):
    return PersistentHashMap(d)


EMPTY = PersistentHashMap({})
