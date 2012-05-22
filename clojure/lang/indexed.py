from abc import ABCMeta, abstractmethod
from clojure.lang.counted import Counted

class Indexed(Counted, object):
    __metaclass__ = ABCMeta

    def nth(self, i, notFound = None):
        pass

