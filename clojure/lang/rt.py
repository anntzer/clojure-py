import re
import sys

from clojure.lang.ipersistentvector import IPersistentVector
from clojure.lang.cljexceptions import InvalidArgumentException
from clojure.lang.comparator import Comparator
from clojure.lang.threadutil import AtomicInteger
from clojure.lang.iseq import ISeq
# I don't like * either, but this should be fine
from .pytypes import *


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


# need id for print protocol
_id = AtomicInteger()


def nextID():
    return _id.getAndIncrement()


def subvec(v, start, end):
    from clojure.lang.persistentvector import EMPTY as EMPTY_VECTOR
    from clojure.lang.apersistentvector import SubVec
    if end < start or start < 0 or end > len(v):
        raise Exception("Index out of range")
    if start == end:
        return EMPTY_VECTOR
    return SubVec(None, v, start, end)


stringEscapeMap = {
    "\a" : "<???>",                  # XXX
    "\b" : "\\b",
    "\f" : "\\f",
    "\n" : "\\n",
    "\r" : "\\r",
    "\t" : "\\t",
    "\v" : "<???>",                  # XXX
    "\\" : "\\\\",
    '"' : '\\\"'
    }

def stringEscape(s):
    return "".join([stringEscapeMap.get(c, c) for c in s])


# this is only for the current Python-coded repl
def printTo(obj, writer=sys.stdout):
    protocols.writeAsReplString(obj, writer)
    writer.write("\n")
    writer.flush()


def _bootstrap_protocols():
    global protocols, seq
    from clojure.lang.indexableseq import create as createIndexableSeq
    from clojure.lang.iprintable import IPrintable
    from clojure.lang.iseq import ISeq
    from clojure.lang.named import Named
    from clojure.lang.namespace import Namespace
    from clojure.lang.protocol import protocolFromType, extendForAllSubclasses
    from clojure.lang.seqable import Seqable

    protocols = Namespace("clojure.protocols")

    for protocol in [ISeq, IPrintable, Named, Seqable]:
        protocolFromType(protocols, protocol)
        extendForAllSubclasses(protocol)

    seq = protocols.seq

    for typ in [pyTupleType, pyListType, pyStrType, pyUnicodeType]:
        protocols.seq.extend(typ, createIndexableSeq)
    protocols.seq.extend(type(None), lambda _: None)
    # protocols.seq.setDefault(NotSeq)

    # Any added writeAsReplString handlers need
    # to write the unreadable syntax:
    # #<foo>
    # if lispreader cannot recognize it.
    common_writes = {
        pyNoneType: lambda obj: "nil",
        pyBoolType: lambda obj: "true" if obj else "false",
        (pyIntType, pyLongType, pyFloatType): str,
        pyStrType: str,
        pyUnicodeType: lambda obj: obj.encode("utf-8"),
        # not sure about this one
        pyRegexType:
            lambda obj:
                '#"{0}"'.format(stringEscape(obj.pattern)).encode("utf-8"),
        # This is the same as default below, but maybe these will be handled
        # specially at some point.
        (pyTupleType, pyListType, pyDictType, pySetType): repr,
        # #<fully.qualified.name> or fully.qualified.name ?
        pyTypeType: "#<{0.__module__}.{0.__name__}>".format,
        # #<function name at 0x21d20c8>
        pyFuncType: "#{0}".format
    }
    repl_extras = {
        # XXX: Will not correctly escape Python strings because clojure-py
        #      will currently only read Clojure-compliant literal strings.
        pyStrType: lambda obj: '"{0}"'.format(stringEscape(obj)),
        pyUnicodeType:
            lambda obj: '"{0}"'.format(stringEscape(obj)).encode("utf-8"),
        # possibly print a preview of the collection:
        # #<__builtin__.dict obj at 0xdeadbeef {'one': 1, 'two': 2 ... >
        (pyTupleType, pyListType, pyDictType, pySetType):
            lambda obj: "#<{0.__module__}.{0.__name__} object at 0x{1:x}>"
                        .format(type(obj), id(obj)),
        pyFuncType: "#{0!r}".format
    }
    repl_writes = common_writes.copy()
    repl_writes.update(repl_extras)
    # early binding trick
    for types, fn in common_writes.items():
        if isinstance(types, type):
            types = (types,)
        for typ in types:
            protocols.writeAsString.extend(
                typ, (lambda fn: lambda obj, writer: writer.write(fn(obj)))(fn))
    for types, fn in repl_writes.items():
        if isinstance(types, type):
            types = (types,)
        for typ in types:
            protocols.writeAsReplString.extend(
                typ, (lambda fn: lambda obj, writer: writer.write(fn(obj)))(fn))
    # default
    # This *should* allow pr and family to handle anything not specified above.
    protocols.writeAsString.setDefault(
        # repr or str here?
        lambda obj, writer: writer.write(str(obj)))
    protocols.writeAsReplString.setDefault(
        lambda obj, writer:
            writer.write('#<{0}.{1} object at 0x{2:x}>'
                         .format(type(obj).__module__, type(obj).__name__,
                                 id(obj))))

    protocols.getName.extend(pyStrType, lambda obj: obj)
    protocols.getName.extend(pyUnicodeType, lambda obj: obj)
    protocols.getName.extend(pyTypeType, lambda obj: obj.__name__)
    protocols.getNamespace.extend(pyTypeType, lambda obj: obj.__module__)

    global name, namespace
    name = protocols.getName
    namespace = protocols.getNamespace


# init is being called each time a .clj is loaded
initialized = False
def init():
    global initialized
    if not initialized:
        _bootstrap_protocols()
        initialized = True


class DefaultComparator(Comparator):
    def compare(self, k1, k2):
        if k1 == k2:
            return 0
        elif k1 < k2:
            return -1
        else:
            return 1
