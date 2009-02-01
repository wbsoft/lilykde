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
Bootstrap application logic for the Frescobaldi editor.
"""

import os, kateshell

DBUS_PREFIX = "org.frescobaldi.main-"

def runningApp():
    pid = os.environ.get("FRESCOBALDI_PID", "")
    return kateshell.runningApp(DBUS_PREFIX, pid)

def newApp(installPrefix=None):
    from frescobaldi_app import mainapp
    return mainapp.MainApp(DBUS_PREFIX, installPrefix)
