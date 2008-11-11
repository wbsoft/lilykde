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

DBUS_PREFIX = "org.frescobaldi.main-"
DBUS_PATH = "/Frescobaldi"
DBUS_IFACE = "org.frescobaldi.mainApp.Frescobaldi"

import dbus

def runningApp():
    """
    Returns a proxy object for an instance of Frescobaldi running on the DBus
    session bus, if it is there, or False if none.
    """
    bus = dbus.SessionBus()
    for name in bus.list_names():
        if name.startswith(DBUS_PREFIX):
            obj = bus.get_object(name, DBUS_PATH)
            iface = dbus.Interface(obj, dbus_interface = DBUS_IFACE)
            print "Found running instance:", name # DEBUG
            return iface
    return False

def newApp():
    """
    Returns a newly started Frescobaldi instance
    """
    from .mainapp import MainApp
    return MainApp()
