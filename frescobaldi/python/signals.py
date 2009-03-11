"""
A signals implementation.
Inspired by http://code.activestate.com/recipes/439356/ but very drastically
changed. (WB)
"""

import inspect, weakref

class Signal:
    """
    class Signal

    A simple implementation of the Signal/Slot pattern. To use, simply 
    create a Signal instance. The instance may be a member of a class, 
    a global, or a local; it makes no difference what scope it resides 
    within. Connect slots to the signal using the "connect()" method. 
    The slot may be a member of a class or a simple function. If the 
    slot is a member of a class, Signal will automatically detect when
    the method's class instance has been deleted and remove it from 
    its list of connected slots.
    """
    def __init__(self):
        self.slots = {}

    def __call__(self, *args, **kwargs):
        for slot in self.slots.values():
            slot(*args, **kwargs)
                
    def connect(self, slot):
        self.disconnect(slot)
        if inspect.ismethod(slot):
            self.slots[id(slot)] = WeakMethod(slot, self)
        else:
            self.slots[id(slot)] = slot

    def disconnect(self, slot):
        if id(slot) in self.slots:
            del self.slots[id(slot)]

    def disconnectAll(self):
        self.slots = {}


class WeakMethod:
    def __init__(self, f, signal):
        self.f = f.im_func
        self.r = weakref.ref(f.im_self, lambda dummy: signal.disconnect(f))
    
    def __call__(self, *args, **kwargs):
        obj = self.r()
        if obj is not None:
            self.f(obj, *args, **kwargs)

