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


import dbus
from PyQt4.QtCore import QString
from PyKDE4.kdecore import KUrl

# interface for our object types (MainApp and Document)
DBUS_IFACE_PREFIX = 'org.frescobaldi.kateshell.'

def runningApp(servicePrefix, pid=None):
    """
    Returns a proxy object for an instance of our app running on the DBus
    session bus, if it is there, or False if none.
    
    Using the proxy object, we can command the remote app almost
    like a local one.
    """
    bus = dbus.SessionBus(private=True)
    names = [n for n in bus.list_names() if n.startswith(servicePrefix)]
    if names:
        if pid and "%s%s" % (servicePrefix, pid) in names:
            name = "%s%s" % (servicePrefix, pid)
        else:
            name = names[0]
        print "Found running instance:", name
        return Proxy(bus.get_object(name, '/MainApp'))
    return False
    
def newApp(servicePrefix):
    from kateshell.app import MainApp
    return MainApp(servicePrefix)


class Proxy(object):
    """
    A wrapper around a dbus proxy object.
    
    Methods calls are automagically directed to the correct interface,
    using some code in the __init__ method.

    When a remote object call would return a dbus.ObjectPath, we return
    the same wrapper for the referenced dbus proxy object.
    This way we can handle remote DBus objects in a Pythonic way:
    
        app = Proxy(bus.get_object(...))
        doc = app.createDoc()
        doc.callMethod()
    """
    def __init__(self, obj):
        self.obj = obj
        for i in 'MainApp', 'Document':
            if obj.object_path.startswith("/"+i):
                self.iface = dbus.Interface(obj, dbus_interface=DBUS_IFACE_PREFIX + i)
                return
        self.iface = None
        
    def __getattr__(self, attr):
        if self.iface:
            meth = getattr(self.iface, attr)
            if callable(meth):
                def proxy_func(*args):
                    # convert args from QString or KUrl to unicode
                    args = list(args)
                    for i in range(len(args)):
                        if isinstance(args[i], QString):
                            args[i] = unicode(args[i])
                        elif isinstance(args[i], KUrl):
                            args[i] = unicode(args[i].url())
                    # call the method
                    res = meth(*args)
                    # Return same proxy if the returned object is a reference
                    if isinstance(res, dbus.ObjectPath):
                        bus = dbus.SessionBus(private=True)
                        res = Proxy(bus.get_object(self.obj.bus_name, res))
                    return res
                return proxy_func
        return getattr(self.obj, attr)
    
    def run(self):
        """ cancel the startup notification """
        import PyKDE4.kdeui
        PyKDE4.kdeui.KStartupInfo.appStarted()

