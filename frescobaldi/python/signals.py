# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009  Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

"""
A simple signal/slot implementation.
"""

import inspect, weakref

class Signal:
    """
    A simple implementation of the Signal/Slot pattern.
    
    To use, simply create a Signal instance. The instance may be a member
    of a class, a global, or a local; it makes no difference what scope
    it resides within. Connect slots to the signal using the "connect()"
    method. The slot may be a member of a class or a simple function.
    
    If the slot is a member of a class, Signal will automatically detect
    when the method's class instance has been deleted and remove it
    from its list of connected slots. If the member is a function, you
    can optionally specify an owner object. If that owner disappears,
    the function if also deleted from the list of connected slots.
    
    Invoke the signal (which will call all connected slots) by simply
    calling it.
    """
    def __init__(self):
        self.functions = set()
        self.objects = weakref.WeakKeyDictionary()
        self.ownedfunctions = weakref.WeakKeyDictionary()

    def __call__(self, *args, **kwargs):
        for func in self.functions:
            func(*args, **kwargs)
        for obj, methods in self.objects.items():
            for func in methods:
                func(obj, *args, **kwargs)
        for functions in self.ownedfunctions.values():
            for func in functions:
                func(*args, **kwargs)
    
    def connect(self, func, owner = None):
        if inspect.ismethod(func):
            self.objects.setdefault(func.im_self, set()).add(func.im_func)
        elif owner is None:
            self.functions.add(func)
        else:
            self.ownedfunctions.setdefault(owner, set()).add(func)

    def disconnect(self, func, owner = None):
        if inspect.ismethod(func):
            s = self.objects.get(func.im_self)
            if s is not None: 
                s.discard(func.im_func)
        elif owner is None:
            self.functions.discard(func)
        else:
            s = self.ownedfunctions.get(owner)
            if s is not None:
                s.discard(func)

    def disconnectAll(self):
        self.functions.clear()
        self.objects.clear()
        self.ownedfunctions.clear()

