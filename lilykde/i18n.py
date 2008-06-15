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

from string import Template
from kdecore import KGlobal, i18n

KGlobal.locale().insertCatalogue('lilykde')

I18N_NOOP = lambda s: s

class _(unicode):
    """
    Subclass of unicode. The value is translated immediately. A method args()
    is added that substitutes dollarsign-prefixed keywords using the
    string.Template class.
    """
    def __new__(cls, *args):
        return unicode.__new__(cls, i18n(*args))

    def args(self, *args, **kwargs):
        return Template(self).substitute(*args, **kwargs)


# kate: indent-width 4;
