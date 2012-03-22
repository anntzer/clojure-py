from clojure.lang.ipersistentvector import IPersistentVector
from clojure.lang.cljexceptions import InvalidArgumentException
from clojure.lang.comparator import Comparator
from clojure.lang.threadutil import AtomicInteger

from clojure.lang.iseq import ISeq

mapInter = map
_list = list


def setMeta(f, meta):
    setattr(f, "meta", lambda: meta)
    return f


def cons(x, s):
    from clojure.lang.cons import Cons
    from clojure.lang.persistentlist import EMPTY as EMPTY_LIST
    if isinstance(s, ISeq):
        return Cons(x, s)
    if s is None:
        return EMPTY_LIST.cons(x)
    return Cons(x, seq(s))


def seqToTuple(s):
    if s is None:
        return ()
    if isinstance(s, tuple):
        return s
    if isinstance(s, IPersistentVector):
        return tuple(s)
    return tuple(s)


class NotSeq(object):
    pass


#def seq(obj):
#    from clojure.lang.indexableseq import IndexableSeq
#    from clojure.lang.symbol import Symbol
#    from clojure.lang.aseq import ASeq

#    if isinstance(obj, Symbol):
#        pass
#    if obj is None:
#        return None
#    if isinstance(obj, ASeq):
#        return obj
#    if isinstance(obj, (tuple, _list, str)):
#        if len(obj) == 0:
#            return None
#        return IndexableSeq(obj, 0)

#    if hasattr(obj, "seq"):
#        return obj.seq()
#    return NotSeq()


    
def first(obj):
    return protocols.first(seq(obj))
        
def next(obj):
    return protocols.next(seq(obj))
    
def isSeqable(obj):
    return protocols.seq.isExtendedBy(type(obj))
    
    
    

def applyTo(fn, args):
    return apply(fn, tuple(map(lambda x: x.first(), args)))


def booleanCast(obj):
    if isinstance(obj, bool):
        return obj
    return obj is None


def keys(obj):
    from clojure.lang.apersistentmap import createKeySeq
    return createKeySeq(obj)


def vals(obj):
    from clojure.lang.apersistentmap import createValueSeq
    return createValueSeq(obj)


def fulfillsHashSet(obj):
    if not hasattr(obj, "__getitem__"):
        return False
    if not hasattr(obj, "__iter__"):
        return False
    if not hasattr(obj, "__contains__"):
        return False
    return True


def fulfillsIndexable(obj):
    if not hasattr(obj, "__getitem__"):
        return False
    if not hasattr(obj, "__len__"):
        return False
    return True


def list(*args):
    from clojure.lang.persistentlist import EMPTY
    c = EMPTY
    for x in range(len(args) - 1, -1, -1):
        c = c.cons(args[x])
    return c


def vector(*args):
    from clojure.lang.persistentvector import EMPTY
    c = EMPTY
    for x in args:
        c = c.cons(x)
    return c


def map(*args):
    from clojure.lang.persistenthashmap import EMPTY
    if len(args) == 0:
        return EMPTY
    if len(args) == 1:
        if isinstance(args[0], dict):
            m = EMPTY
            for x in args[0]:
                if x in m:
                    raise InvalidArgumentException("Duplicate key")
                m = m.assoc(x, args[0][x])
            return m
        if fulfillsIndexable(args[0]):
            args = args[0]
    m = EMPTY
    for x in range(0, len(args), 2):
        key = args[x]
        value = args[x + 1]
        m = m.assoc(key, value)
    return m

def set(*args):
    from clojure.lang.persistenthashset import EMPTY
    if len(args) == 0:
        return EMPTY
    if len(args) == 1:
        if isinstance(args[0], dict):
            m = EMPTY
            for x in args[0]:
                if x in m:
                    raise InvalidArgumentException("Duplicate key")
                m.impl = m.impl.assoc(x, args[0][x])
            return m
        if fulfillsIndexable(args[0]):
            args = args[0]
    m = EMPTY
    for x in range(0, len(args), 2):
        key = args[x]
        value = args[x + 1]
        m.impl = m.impl.assoc(key, value)
    return m



def getDefaultImports():
    from clojure.lang.persistentlist import PersistentList
    import sys
    import math
    d = {"String": str,
         "Integer": int,
         "Math": math,
         "clojure.lang.PersistentList": PersistentList,
         "clojure.lang.RT": sys.modules[__name__]}
    return d


id = AtomicInteger()


def nextID():
    return id.getAndIncrement()


def subvec(v, start, end):
    from clojure.lang.persistentvector import EMPTY as EMPTY_VECTOR
    from clojure.lang.apersistentvector import SubVec
    if end < start or start < 0 or end > len(v):
        raise Exception("Index out of range")
    if start == end:
        return EMPTY_VECTOR
    return SubVec(None, v, start, end)


def _extendIPrintableForManuals():
    protocols.writeAsString.extend(type(None), lambda obj, writer: writer.write("nil"))
    protocols.writeAsReplString.extend(type(None), lambda obj, writer: writer.write("nil"))
    
    protocols.writeAsString.extend(int, lambda obj, writer: writer.write(str(obj)))
    protocols.writeAsReplString.extend(int, lambda obj, writer: writer.write(str(obj)))


def _extendSeqableForManuals():
    from clojure.lang.indexableseq import create as createIndexableSeq
    from clojure.lang.persistentvector import PersistentVector
    from clojure.lang.stringseq import stringseq
    
    protocols.seq.extendForTypes([tuple, type([])],
                                 lambda obj: createIndexableSeq(obj))
    protocols.seq.extendForTypes([str, unicode], stringseq)
    protocols.seq.extend(type(None), lambda x: None)
    
    #protocols.seq.setDefault(lambda x: NotSeq())

def _bootstrap_protocols():
    global protocols, seq
    from clojure.lang.protocol import protocolFromType, extendForAllSubclasses
    from clojure.lang.iseq import ISeq as iseq
    from clojure.lang.seqable import Seqable as seqable
    from clojure.lang.iprintable import IPrintable

    protocolFromType("clojure.protocols", IPrintable)
    extendForAllSubclasses(IPrintable)

    protocolFromType("clojure.protocols", seqable)
    extendForAllSubclasses(seqable)
    
    
    protocolFromType("clojure.protocols", iseq)
    extendForAllSubclasses(iseq)
    import sys 
    protocols = sys.modules["clojure.protocols"]
    seq = protocols.seq
    _extendSeqableForManuals()
    _extendIPrintableForManuals()
    
    

def init():
    global DEFAULT_IMPORTS
    DEFAULT_IMPORTS = map(getDefaultImports())
    _bootstrap_protocols()


DEFAULT_IMPORTS = None


class DefaultComparator(Comparator):
    def compare(self, k1, k2):
        if k1 == k2:
            return 0
        elif k1 < k2:
            return -1
        else:
            return 1
