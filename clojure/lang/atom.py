"""
Tuesday, March 20 2012
"""

from .aref import ARef
from .cljexceptions import ArityException
from .atomicreference import AtomicReference


class Atom(ARef):
    """A thread-safe mutable object."""
    def __init__(self, state, meta=None):
        """Instantiate an Atom to the given state.
        
        state -- any object
        meta -- meta data to attach"""
        super(Atom, self).__init__(meta)
        self._state = AtomicReference(state)
    def deref(self):
        """Return this Atom's current state."""
        return self._state.get()
    def swap(self, *args):
        """Change this Atom's current state.

        args must be one of:
        
        * IFn
        * IFn, object
        * IFn, object, object
        * IFn, object, object, ISeq

        An ArityException will be raised otherwise.

        Return the result of calling IFn with the current state of this Atom
        as its first argument and the remaining arguments to this method."""
        func = None
        if len(args) == 1:
            ifn = args[0]
            func = lambda v: ifn(v)
        elif len(args) == 2:
            ifn, arg = args
            func = lambda v: ifn(v, arg) 
        elif len(args) == 3:
            ifn, arg1, arg2 = args
            func = lambda v: ifn(v, arg1, arg2)
        elif len(args) == 4:
            ifn, arg2, arg3, arg4 = args
            func = lambda v: apply(ifn, v, arg2, arg3, list(arg4))
        else:
            raise ArityException("Atom.swap() expected 1 to 4 arguments,"
                                 " got: ({})".format(len(args)))
        while True:
            val = self.deref()
            newv = func(val)
            self.validate(newv)
            if self._state.compareAndSet(val, newv):
                self.notifyWatches(val, newv)
                return newv
    def compareAndSet(self, oldv, newv):
        """Set the state of this Atom to newv.

        oldv -- Any object. The expected current state of this Atom.
        newv -- any object

        If the current state of this Atom is oldv set it to newv. A
        validator, if one exists is called prior to setting. Any watches are
        notified after successfully setting.

        Return True if successful, False otherwise."""
        self.validate(newv)
        ret = self._state.compareAndSet(oldv, newv)
        if ret is not None:
            self.notifyWatches(oldv, newv)
        return ret
    def reset(self, newval):
        """Reset this Atom's state to newval.

        newval -- any object

        A validator, if one exists is called prior to resetting.
        Any watches are notified after resetting.
        
        Return newval"""
        oldval = self._state.get()
        self.validate(newval)
        self._state.set(newval)
        self.notifyWatches(oldval, newval)
        return newval
