import re
import sys

from clojure.lang.ipersistentvector import IPersistentVector
from clojure.lang.cljexceptions import InvalidArgumentException
from clojure.lang.comparator import Comparator
from clojure.lang.threadutil import AtomicInteger
from clojure.lang.iseq import ISeq
# I don't like * either, but this should be fine
from pytypes import *


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


#def map(*args): #!!!
    #from clojure.lang.persistenthashmap import EMPTY
    #if len(args) == 0:
        #return EMPTY
    #if len(args) == 1:
        #if isinstance(args[0], dict):
            #m = EMPTY
            #for x in args[0]:
                #if x in m:
                    #raise InvalidArgumentException("Duplicate key")
                #m = m.assoc(x, args[0][x])
            #return m
        #if fulfillsIndexable(args[0]):
            #args = args[0]
    #m = EMPTY
    #for x in range(0, len(args), 2):
        #key = args[x]
        #value = args[x + 1]
        #m = m.assoc(key, value)
    #return m
def map(*args):
    from clojure.lang.persistenthashmap import PersistentHashMap
    if len(args) == 1:
        if isinstance(args[0], dict):
            return PersistentHashMap(args[0])
        else:
            args = args[0]
    return PersistentHashMap({k: v for k, v in zip(args[::2], args[1::2])})


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


def _extendIPrintableForManuals():

    # Any added writeAsReplString handlers need
    # to write the unreadable syntax:
    # #<foo>
    # if lispreader cannot recognize it.

    # None
    protocols.writeAsString.extend(
        pyNoneType,
        lambda obj, writer: writer.write("nil"))
    protocols.writeAsReplString.extend(
        pyNoneType,
        lambda obj, writer: writer.write("nil"))
    # True, False
    protocols.writeAsString.extend(
        pyBoolType,
        lambda obj, writer: writer.write(obj and "true" or "false"))
    protocols.writeAsReplString.extend(
        pyBoolType,
        lambda obj, writer: writer.write(obj and "true" or "false"))
    # int, long
    protocols.writeAsString.extendForTypes(
        [pyIntType, pyLongType],
        lambda obj, writer: writer.write(str(obj)))
    protocols.writeAsReplString.extendForTypes(
        [pyIntType, pyLongType],
        lambda obj, writer: writer.write(str(obj)))
    # float separate to allow for possible precision state
    protocols.writeAsString.extend(
        pyFloatType,
        lambda obj, writer: writer.write(str(obj)))
    protocols.writeAsReplString.extend(
        pyFloatType,
        lambda obj, writer: writer.write(str(obj)))
    # str
    protocols.writeAsString.extend(
        pyStrType,
        lambda obj, writer: writer.write(obj))
    protocols.writeAsReplString.extend(
        pyStrType,
        # XXX: Will not correctly escape Python strings because clojure-py
        #      will currently only read Clojure-compliant literal strings.
        lambda obj, writer: writer.write('"{0}"'.format(stringEscape(obj))))
    # unicode
    protocols.writeAsString.extend(
        pyUnicodeType,
        lambda obj, writer: writer.write(obj.encode("utf-8")))
    protocols.writeAsReplString.extend(
        pyUnicodeType,
        lambda obj, writer: writer.write(u'"{0}"'.format(stringEscape(obj))
                                         .encode("utf-8")))
    # regex
    protocols.writeAsString.extend(
        pyRegexType,
        lambda obj, writer:   # not sure about this one
            writer.write(u'#"{0}"'.format(stringEscape(obj.pattern))
                         .encode("utf-8")))
    protocols.writeAsReplString.extend(
        pyRegexType,
        lambda obj, writer:
            writer.write(u'#"{0}"'.format(stringEscape(obj.pattern))
                         .encode("utf-8")))
    # tuple, list, dict, and set
    # This is the same as default below, but maybe these will be handled
    # specially at some point.
    protocols.writeAsString.extendForTypes(
        [pyTupleType, pyListType, pyDictType, pySetType],
        lambda obj, writer: writer.write(repr(obj)))
    protocols.writeAsReplString.extendForTypes(
        [pyTupleType, pyListType, pyDictType, pySetType],
        # possibly print a preview of the collection:
        # #<__builtin__.dict obj at 0xdeadbeef {'one': 1, 'two': 2 ... >
        lambda obj, writer:
            writer.write('#<{0}.{1} object at 0x{2:x}>'
                         .format(type(obj).__module__, type(obj).__name__,
                                 id(obj))))
    # type
    # #<fully.qualified.name> or fully.qualified.name ?
    protocols.writeAsString.extend(
        pyTypeType,
        lambda obj, writer:
            writer.write('#<{0}.{1}>'.format(obj.__module__, obj.__name__)))
    protocols.writeAsReplString.extend(
        pyTypeType,
        lambda obj, writer:
            writer.write('#<{0}.{1}>'.format(obj.__module__, obj.__name__)))
    # function
    # #<function name at 0x21d20c8>
    protocols.writeAsString.extend(
        pyFuncType,
        lambda obj, writer: writer.write('#{0}'.format(obj)))
    protocols.writeAsReplString.extend(
        pyFuncType,
        lambda obj, writer: writer.write('#{0!r}'.format(obj)))
    # default
    # This *should* allow pr and family to handle anything not specified
    # above.
    protocols.writeAsString.setDefault(
        # repr or str here?
        lambda obj, writer: writer.write(str(obj)))
    protocols.writeAsReplString.setDefault(
        lambda obj, writer:
            writer.write('#<{0}.{1} object at 0x{2:x}>'
                         .format(type(obj).__module__, type(obj).__name__,
                                 id(obj))))

# this is only for the current Python-coded repl
def printTo(obj, writer=sys.stdout):
    protocols.writeAsReplString(obj, writer)
    writer.write("\n")
    writer.flush()

def _extendSeqableForManuals():
    from clojure.lang.indexableseq import create as createIndexableSeq
    
    protocols.seq.extendForTypes(
        [pyTupleType, pyListType, pyStrType, pyUnicodeType],
        lambda obj: createIndexableSeq(obj))
    protocols.seq.extend(type(None), lambda x: None)
    
    #protocols.seq.setDefault(lambda x: NotSeq())

def _bootstrap_protocols():
    global protocols, seq
    from clojure.lang.iseq import ISeq as iseq
    from clojure.lang.iprintable import IPrintable
    from clojure.lang.named import Named
    from clojure.lang.protocol import protocolFromType, extendForAllSubclasses
    from clojure.lang.seqable import Seqable as seqable

    protocolFromType("clojure.protocols", IPrintable)
    extendForAllSubclasses(IPrintable)

    protocolFromType("clojure.protocols", seqable)
    extendForAllSubclasses(seqable)
    
    protocolFromType("clojure.protocols", iseq)
    extendForAllSubclasses(iseq)
    protocols = sys.modules["clojure.protocols"]
    seq = protocols.seq
    _extendSeqableForManuals()
    _extendIPrintableForManuals()
    
    protocolFromType("clojure.protocols", Named)
    extendForAllSubclasses(Named)
    global name, namespace
    
    name = protocols.getName
    namespace = protocols.getNamespace
    _extendNamedForManuals()
    
def _extendNamedForManuals():
	protocols.getName.extendForTypes([pyStrType, pyUnicodeType], lambda x: x)
	protocols.getName.extend(pyTypeType, lambda x: x.__name__)
	
	protocols.getNamespace.extend(pyTypeType, lambda x: x.__module__)

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
