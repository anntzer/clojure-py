from clojure.lang.namespace import Namespace
import clojure.lang.rt as RT


class ProtocolException(Exception):
    pass


def getFuncName(protocol, funcname):
    return str(protocol) + funcname


class ProtocolFn(object):
    """A function that dispatches on the class of the first argument passed to
    __call__.
    """

    def __init__(self, fname):
        self.dispatchTable = {}
        self.name = intern(fname)
        self.attrname = intern("__proto__" + self.name)
        self.default = None

    def extend(self, cls, fn):
        """Extend a protocol function to a given class.
        
        For user-defined classes, add a __proto__<name> attribute to the class.
        For builtin classes, add an entry to the global dispatch table.
        """
        try:
            setattr(cls, self.attrname, fn)
        except:
            self.dispatchTable[cls] = fn

    def setDefault(self, fn):
        self.default = fn

    def isExtendedBy(self, cls):
        """Check whether a given class extends this protocol function.
        """
        return hasattr(cls, self.attrname) or cls in self.dispatchTable

    def __call__(self, *args):
        """Dispatch a function call on the class of the first argument.
        """
        x = type(args[0])
        try:
            fn = getattr(x, self.attrname)
        except AttributeError:
            fn = self.dispatchTable.get(x, self.default)
        if fn:
            return fn(*args) # exceptions raised by fn will propagate.
        raise ProtocolException("{0} not extended to handle: {1}"
                                .format(self.name, x))

    def __repr__(self):
        return "ProtocolFn<" + self.name + ">"


class Protocol(object):
    """A collection of ProtocolFns.
    """

    def __init__(self, ns, name, fns):
        """Define a protocol in a given ns with given name and functions names.
        """
        self.ns = ns
        self.name = name
        self.fns = fns
        self.protofns = registerFns(ns, fns) # a dict of fn names to ProtocolFns.
        self.__name__ = name
        self.implementors = set()

    def markImplementor(self, cls):
        """Add a class to the list of implementors.
        """
        self.implementors.add(cls)

    def extendForType(self, cls, mp):
        """Extend this protocol for the given type and the given map of methods.

        mp should be a map of methodnames: functions.
        """
        for x in mp:
            name =  RT.name(x.sym)
            if name not in self.protofns:
                raise ProtocolException("No Method found for name " + x)
            fn = self.protofns[name]
            fn.extend(cls, mp[x])
        self.markImplementor(cls)

    def isExtendedBy(self, cls):
        """Check whether a class extends a protocol.
        """
        return cls in self.implementors

    def __repr__(self):
        return "Protocol<" + self.name + ">"


def registerFns(ns, fns):
    """Return a dict of function names to ProtocolFns in a given namespace.

    For each function name, resolve it in the given namespace, creating and
    adding a new ProtocolFn if needed.
    """
    protofns = {}
    for fn in fns:
        if hasattr(ns, fn):
            proto = getattr(ns, fn)
        else:
            fname = ns.__name__ + fn
            proto = ProtocolFn(fname)
            setattr(ns, fn, proto)
        proto.__name__ = fn
        protofns[fn] = proto
    return protofns


def protocolFromType(ns, cls):
    """Create a protocol from a class.  Register it to the class and namespace.

    The class used registers the protocol in the __exactprotocol__ field, and
    the class used (i.e., itself) in the __exactprotocolclass__ type.  The
    __protocols__ field holds a list of all protocols a class extends.

    Useful for turning abstract classes into protocols.
    """
    fns = [fn for fn in dir(cls) if not fn.startswith("_")]
    proto = Protocol(ns, cls.__name__, fns)
    cls.__exactprotocol__ = proto
    cls.__exactprotocolclass__ = cls
    if not hasattr(cls, "__protocols__"):
        cls.__protocols__ = []
    cls.__protocols__.append(proto)
    if not hasattr(ns, cls.__name__):
        setattr(ns, cls.__name__, proto)
    return proto


def getExactProtocol(cls):
    """Return the protocol defined by a class, if there is one.
    """
    if hasattr(cls, "__exactprotocol__") \
       and hasattr(cls, "__exactprotocolclass__") \
       and cls.__exactprotocolclass__ is cls:
           return cls.__exactprotocol__


def extendProtocolForClass(proto, cls):
    """Implicitly extend a class to a protocol using identically named fields.
    """
    for fn in proto.protofns:
        pfn = proto.protofns[fn]
        if hasattr(cls, fn):
            try:
                pfn.extend(cls, getattr(cls, fn))
            except AttributeError as e:
                print "Can't extend, got {0}".format(pfn), type(pfn)
                raise
    proto.markImplementor(cls)


def _extendProtocolForAllSubclasses(proto, cls):
    """Implicitly extend a class and all its subclasses to a protocol.
    """
    extendProtocolForClass(proto, cls)
    for x in cls.__subclasses__():
        _extendProtocolForAllSubclasses(proto, x)


def extendForAllSubclasses(cls):
    """Implicitly extend all subclasses of a class to the protocols it extends.
    """
    for proto in getattr(cls, "__protocols__", []):
        _extendProtocolForAllSubclasses(proto, cls)


def extendForType(interface, cls):
    """Implicitly extend a class to the list of protocols of an interface.
    """
    for proto in getattr(interface, "__protocols__", []):
        extendProtocolForClass(proto, cls)


def extend(cls, *args):
    """Extend a class to a list of protocols.
    
    args should be of the form
        [abstract-class, mapping, abstract-class, mapping, ...]
    """
    if len(args) % 2:
        raise ProtocolException("Expected even number of forms to extend.")
    for cls_proto, mapping in zip(args[::2], args[1::2]):
        proto = getExactProtocol(cls_proto)
        if not proto:
            raise ProtocolException(
                "Expected protocol, got {0}".format(cls_proto))
        proto.extendForType(cls, mapping)

