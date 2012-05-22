from abc import ABCMeta, abstractmethod

class IEditableCollection(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def asTransient(self):
        """Render a persistent object transient.
        """
