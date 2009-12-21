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

from __future__ import unicode_literals

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
    from its list of connected slots.
    
    Emit the signal (to call all connected slots) by simply invoking it.
    The order in which the slots are called is undetermined.
    
    If you create the signal instance with fireonce=True, it will clear
    all connections after being invoked.
    """
    def __init__(self, fireonce=False):
        self.functions = set()
        self.objects = weakref.WeakKeyDictionary()
        self.fireonce = fireonce

    def __call__(self, *args, **kwargs):
        """ call all connected slots """
        # make copies because the sets might change...
        for func in set(self.functions):
            # if possible determine the number of arguments the function 
            # expects, and discard the superfluous arguments.
            try:
                func.func_code.co_argcount
            except AttributeError:
                func(*args, **kwargs)
            else:
                func(*args[:func.func_code.co_argcount], **kwargs)
        for obj, methods in self.objects.items():
            for func in set(methods):
                try:
                    func.func_code.co_argcount
                except AttributeError:
                    func(obj, *args, **kwargs)
                else:
                    func(obj, *args[:func.func_code.co_argcount-1], **kwargs)
        if self.fireonce:
            self.clear()
            
    def connect(self, func):
        if inspect.ismethod(func):
            self.objects.setdefault(func.im_self, set()).add(func.im_func)
        else:
            self.functions.add(func)

    def disconnect(self, func):
        if inspect.ismethod(func):
            s = self.objects.get(func.im_self)
            if s is not None:
                s.discard(func.im_func)
        else:
            self.functions.discard(func)

    def clear(self):
        self.functions.clear()
        self.objects.clear()

    def disconnectObject(self, obj):
        """ Remove all connections that are methods of given object obj """
        try:
            del self.objects[obj]
        except KeyError:
            pass

