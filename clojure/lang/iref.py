from abc import ABCMeta, abstractmethod
from clojure.lang.ideref import IDeref

class IRef(IDeref):
    __metaclass__ = ABCMeta

    @abstractmethod
    def setValidator(self, fn):
        """Sets the validator for an object.
        """

    @abstractmethod
    def getValidator(self):
        """Returns the validator of an object.
        """

    @abstractmethod
    def getWatches(self):
        """Returns the watchers of an object.
        """

    @abstractmethod
    def addWatch(self, key, fn):
        """Adds a watcher to an object with a given key.
        """

    @abstractmethod
    def removeWatch(self, key):
        """Removes the watcher from an object, given its key.
        """
