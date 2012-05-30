from .. import protocols


class ProtocolException(Exception):
    pass


def getFuncName(protocol, funcname):
    return str(protocol) + funcname


class ProtocolFn(object):
    """A function that dispatches on the class of the first argument passed to
    __call__.
    """

    def __init__(self, protocol, fname):
        self.protocol = protocol
        self.name = intern(fname)
        self.attrname = intern("__proto__" + self.name)
        self.dispatchTable = {}
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

    def getExtensionBy(self, cls):
        """Return the function that extends this protocol function to a class.

        If this protocol function is implemented by an abstract method, then
        use the actual implementation of the method.
        """
        for supercls in cls.__mro__:
            fn = (getattr(supercls, self.attrname, None) or
                  self.dispatchTable.get(supercls))
            if getattr(fn, "__isabstractmethod__", False):
                fn = getattr(cls, fn.__name__)
            if fn:
                return fn

    def __call__(self, *args):
        """Dispatch a function call on the class of the first argument.
        """
        fn = self.getExtensionBy(type(args[0])) or self.default
        if fn:
            return fn(*args) # exceptions raised by fn will propagate.
        raise ProtocolException("{0} not extended to handle: {1}"
                                .format(self, type(args[0])))

    def __repr__(self):
        return "<ProtocolFn {0}.{1}>".format(self.protocol.__name__, self.name)


class ProtocolMeta(type):
    """Metaclass of Protocols: non-instantiatable classes that override
    is{instance,subclass}.
    """

    def __call__(self):
        raise ProtocolException("Protocols are not instantiatable.")

    def __instancecheck__(self, obj):
        return any(c in self.implementors for c in type(obj).__mro__)

    def __subclasscheck__(self, cls):
        return any(c in self.implementors for c in cls.__mro__)

    def __repr__(self):
        return "<Protocol {0}>".format(self.__name__)


def makeProtocol(ns, name, fns):
    """Define a protocol in a given ns with given name and functions names.

    For each function name, resolve it in the given namespace, creating and
    adding a new ProtocolFn if needed, and register it to protofns.
    """

    class Protocol(object):
        """A collection of ProtocolFns.
        """

        __metaclass__ = ProtocolMeta
        protofns = {} # a dict of fn names to ProtocolFns.
        implementors = set()

        @classmethod
        def markImplementor(self, cls):
            """Add a class to the list of implementors.
            """
            self.implementors.add(cls)

        @classmethod
        def extendForClass(self, cls, mp=None):
            """Extend self to a class using a names to implementations map.

            If the implementation map is not given, the protocol is extended
            using identically named methods of the class.
            """
            if mp is None:
                for fn in self.protofns:
                    pfn = self.protofns[fn]
                    if hasattr(cls, fn):
                        pfn.extend(cls, getattr(cls, fn))
            else:
                for meth_name in mp:
                    name = (meth_name if isinstance(meth_name, basestring)
                            else meth_name.getName())
                    if name not in self.protofns:
                        raise ProtocolException(
                            "No method found for name {0}".format(name))
                    pfn = self.protofns[name]
                    pfn.extend(cls, mp[meth_name])
            self.markImplementor(cls)

    Protocol.__name__ = name

    for fn in fns:
        if hasattr(ns, fn):
            proto = getattr(ns, fn)
        else:
            proto = ProtocolFn(Protocol, fn)
            setattr(ns, fn, proto)
        proto.__name__ = fn
        Protocol.protofns[fn] = proto

    return Protocol


def protocolFromType(ns, cls):
    """Create a protocol from a class.  Register it to the class and namespace.

    The class used registers the protocol in the __exactprotocol__ field, and
    the class used (i.e., itself) in the __exactprotocolclass__ type.  The
    __protocols__ field holds a list of all protocols a class defines.

    Useful for turning abstract classes into protocols.
    """
    fns = [fn for fn in dir(cls) if not fn.startswith("_")]
    proto = makeProtocol(ns, cls.__name__, fns)
    cls.__exactprotocol__ = proto
    cls.__exactprotocolclass__ = cls
    if not hasattr(cls, "__protocols__"):
        cls.__protocols__ = []
    cls.__protocols__.append(proto)
    if not hasattr(ns, cls.__name__):
        setattr(ns, cls.__name__, proto)
    return proto


def asProtocol(ns=protocols):
    """protocolFromType as a class decorator.
    """
    def decorator(cls):
        protocolFromType(ns, cls)
        return cls
    return decorator


def extends(*args):
    """Decorator for a class implicitely extending a list of protocols."""
    def decorator(cls):
        for protocol in args:
            protocol.extendForClass(cls)
        return cls
    return decorator


def _extendProtocolForAllSubclasses(proto, cls):
    """Implicitly extend a protocol to a class and all its subclasses.
    """
    proto.extendForClass(cls)
    for x in cls.__subclasses__():
        _extendProtocolForAllSubclasses(proto, x)


# XXX remove
def extendForAllSubclasses(cls):
    """Implicitly extend all subclasses of a class to the protocols it extends.
    """
    for proto in getattr(cls, "__protocols__", []):
        _extendProtocolForAllSubclasses(proto, cls)


def extend(cls, *args):
    """Extend a list of protocols to a class.
    
    args should be of the form
        [protocol, mapping, protocol, mapping, ...]
    """
    if len(args) % 2:
        raise ProtocolException("Expected even number of forms to extend.")
    for proto, mapping in zip(args[::2], args[1::2]):
        proto.extendForClass(cls, mapping)

