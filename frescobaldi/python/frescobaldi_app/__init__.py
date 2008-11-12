# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008  Wilbert Berendsen
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# See http://www.gnu.org/licenses/ for more information.

"""
Bootstrap application logic for the Frescobaldi editor.
"""

import dbus

DBUS_PREFIX = "org.frescobaldi.main-"
DBUS_IFACE_PREFIX = "org.frescobaldi."
DBUS_MAIN_PATH = "/MainApp"

def newApp():
    """ Returns a newly started Frescobaldi instance. """
    from .mainapp import MainApp
    return MainApp()

def runningApp():
    """
    Returns a proxy object for an instance of Frescobaldi running on the DBus
    session bus, if it is there, or False if none.
    
    Using the proxy object, we can command the remote app almost
    like a local one.
    """
    bus = dbus.SessionBus(private=True)
    for name in bus.list_names():
        if name.startswith(DBUS_PREFIX):
            print "Found running instance:", name # DEBUG
            return Proxy(bus.get_object(name, DBUS_MAIN_PATH))
    return False

def _get_interface(path):
    """ Return the default interface to use for the given object path. """
    for i in 'MainApp', 'Document':
        if path.startswith("/"+i):
            return DBUS_IFACE_PREFIX + i
    return False


class Proxy(object):
    """
    A wrapper around a dbus proxy object.
    
    Methods calls are automagically directed to the correct interface,
    using the object_path to interface name translation in the _get_interface
    function.

    When a remote object call would return a dbus.ObjectPath, we return
    the same wrapper for the referenced dbus proxy object.
    This way we can handle remote DBus objects in a Pythonic way:
    
        app = Proxy(bus.get_object(...))
        doc = app.createDoc()
        doc.callMethod()
    """
    def __init__(self, obj):
        self.obj = obj
        i = _get_interface(obj.object_path)
        if i: self.iface = dbus.Interface(obj, dbus_interface=i)
        else: self.iface = None
        
    def __getattr__(self, attr):
        if self.iface:
            a = getattr(self.iface, attr)
            if callable(a):
                def proxy_func(*args, **kwargs):
                    res = a(*args, **kwargs)
                    if isinstance(res, dbus.ObjectPath):
                        bus = dbus.SessionBus(private=True)
                        res = Proxy(bus.get_object(self.obj.bus_name, res))
                    return res
                return proxy_func
        return getattr(self.obj, attr)

