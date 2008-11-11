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

import os, re, sys
import dbus, dbus.service, dbus.mainloop.qt

from PyQt4.QtCore import QTimer
from PyQt4.QtGui import QPushButton
from PyKDE4.kdeui import KApplication

from . import DBUS_PREFIX, DBUS_PATH, DBUS_IFACE

# Make the Qt mainloop the default one
dbus.mainloop.qt.DBusQtMainLoop(set_as_default=True)

class DBusApp(dbus.service.Object):
    """
    The DBus interface for our app.
    """
    def __init__(self, app):
        self.app = app
        name = "%s%d" % (DBUS_PREFIX, os.getpid())
        bus = dbus.service.BusName(name, bus=dbus.SessionBus(private=True))
        dbus.service.Object.__init__(self, bus, DBUS_PATH)
        # Put in environment so ktexteditservice can find us
        os.environ["TEXTEDIT_DBUS_PATH"] = name + DBUS_PATH
    
    @dbus.service.method(DBUS_IFACE, in_signature='s', out_signature='b')
    def openUrl(self, url):
        print url
        return False # TODO

    @dbus.service.method(DBUS_IFACE, in_signature='', out_signature='b')
    def run(self):
        """
        Is called by a remote app after new documents are opened.
        Currently need not to do anything.
        """
        return True

    @dbus.service.method(DBUS_IFACE, in_signature='s', out_signature='b')
    def isOpen(self, url):
        """
        Returns true is the specified URL is opened by the current application
        """
        return False # TODO
        
    @dbus.service.method("org.lilypond.TextEdit", in_signature='s', out_signature='b')
    def openTextEditUrl(self, url):
        """
        To be called by ktexteditservice (part of lilypond-kde4).
        Opens the specified textedit:// URL.
        """
        print url
        return False # TODO


class MainApp(object):
    """ A running Frescobaldi instance. """
    def __init__(self):
        self.kapp = KApplication()
        self.dbus = DBusApp(self)

        # test stuff
        self.w = QPushButton("bla")
        self.kapp.setTopWidget(self.w)
        self.w.show()

    def run(self):
        return self.kapp.exec_()
