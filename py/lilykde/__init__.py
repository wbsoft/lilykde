# This file is part of LilyKDE, http://lilykde.googlecode.com/
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
LilyKDE
"""

import os
from locale import getdefaultlocale
from qt import QMimeSourceFactory

__all__ = ['appdir', 'language', 'encoding', 'config']

appdir = os.path.dirname(__path__[0])

try:
    language, encoding = getdefaultlocale()
except ValueError:
    language, encoding = None, None

def config(group=None):
    """
    Return the master KConfig object for "lilykderc", or
    a KConfigGroup (wrapper) object if a group name is given.
    """
    from lilykde.util import kconfig
    k = kconfig("lilykderc", False, False)
    return group and k.group(group) or k


QMimeSourceFactory.defaultFactory().addFilePath(
    os.path.join(appdir, "pics"))



# kate: indent-width 4;
