from clojure.lang.cljexceptions import AbstractMethodCall
from . import protocol


@protocol.asProtocol()
class Seqable(object):
    def seq(self):
        raise AbstractMethodCall(self)
