class AbstractMethodCall(Exception):
    def __init__(self, cls=None):
        if cls is not None:
            self.args = "in {0}".format(cls.__class__.__name__),


class ArityException(TypeError):
    pass


class CljException(Exception):
    pass


class IllegalStateException(CljException):
    pass


class InvalidArgumentException(CljException):
    pass


class IllegalAccessError(CljException):
    pass


class IndexOutOfBoundsException(CljException):
    pass


class UnsupportedOperationException(Exception):
    pass


class IllegalArgumentException(Exception):
    pass


class TransactionRetryException(Exception):
    pass


class ReaderException(Exception):
    def __init__(self, arg, rdr=None):
        if rdr:
            arg = "At line {0}: {1}".format(rdr.lineCol()[0], arg)
        self.args = arg,


class CompilerException(Exception):
    def __init__(self, reason, form):
        from lispreader import LINE_KEY
        if form:
            meta = form.meta()
            if meta:
                reason = "At line {0}: {1}".format(meta[LINE_KEY], reason)
        self.args = reason,


class NoNamespaceException(ImportError):
    def __init__(self, lib, ns):
        self.args = ("Importing {0} did not create namespace {1}.".
                     format(lib, ns),)
