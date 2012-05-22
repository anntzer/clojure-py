from abc import ABCMeta, abstractmethod


class IFn(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __call__(self, *args):
        """Call a callable.
        """

