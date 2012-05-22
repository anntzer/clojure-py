from abc import ABCMeta, abstractmethod


class Comparator(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def compare(self, a, b):
        """Return 1 if a > b, 0 if a == b, -1 if a < b.
        """
