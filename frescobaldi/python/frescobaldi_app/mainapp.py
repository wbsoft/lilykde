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

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyKDE4.kdeui import KApplication

from . import DBUS_PREFIX, DBUS_MAIN_PATH, DBUS_MAIN_IFACE
from .mainwindow import MainWindow


# Make the Qt mainloop the default one
dbus.mainloop.qt.DBusQtMainLoop(set_as_default=True)

DBUS_SERVICE = "%s%d" % (DBUS_PREFIX, os.getpid())

class DBusItem(dbus.service.Object):
    """
    An exported DBus item for our application.
    To be subclassed!
    """
    def __init__(self, path=None):
        if path is None:
            path = '/%s' % self.__class__.__name__
        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(DBUS_SERVICE, bus)
        dbus.service.Object.__init__(self, bus_name, path)
    

class MainApp(DBusItem):
    """
    Our main application instance. Also exposes some methods to DBus.
    Instantiated only once.
    """
    def __init__(self):
         # KApplication needs to be instantiated before any D-Bus stuff
        self.kapp = KApplication()
        DBusItem.__init__(self, DBUS_MAIN_PATH)

        # Put ourselves in environment so ktexteditservice can find us
        os.environ["TEXTEDIT_DBUS_PATH"] = DBUS_SERVICE + DBUS_MAIN_PATH
        print "TEXTEDIT_DBUS_PATH=" + DBUS_SERVICE + DBUS_MAIN_PATH # DEBUG

        self.mainwin = MainWindow()
        self.kapp.setTopWidget(self.mainwin)
        
    
    @dbus.service.method(DBUS_MAIN_IFACE, in_signature='s', out_signature='b')
    def openUrl(self, url):
        print url
        return False # TODO

    @dbus.service.method(DBUS_MAIN_IFACE, in_signature='', out_signature='', sender_keyword="sender")
    def run(self, sender=None):
        """
        Is called by a remote app after new documents are opened.
        Currently need not to do anything.
        
        If we are the caller ourselves, run the KDE app.
        """
        if sender is None:
            self.kapp.exec_()

    @dbus.service.method(DBUS_MAIN_IFACE, in_signature='s', out_signature='b')
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
        print "openTextEditUrl called:", url # DEBUG
        return False # TODO

    @dbus.service.method(DBUS_MAIN_IFACE, in_signature='', out_signature='')
    def quit(self):
        self.kapp.quit()
