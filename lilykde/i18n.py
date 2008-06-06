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

import gettext
from os.path import join, dirname
from string import Template
from lilykde import appdir, language

# TODO: in system-wide installation use standard locale dirs and lilykde
# textdomain

def getTranslations():
    # Find sibling dir mo/ in parent of current script dir
    modir = join(appdir, "mo")
    if language:
        for mofile in language, language.split("_")[0]:
            try:
                fp = open(join(modir, mofile + ".mo"))
                return gettext.GNUTranslations(fp)
            except IOError:
                pass
    return gettext.NullTranslations()

#translations = gettext.translation('lilykde', fallback=True)
translations = getTranslations()

def _i18n(msgid1, msgid2=None, n=None):
    if n is None:
        return translations.ugettext(msgid1)
    else:
        return translations.ungettext(msgid1, msgid2, n)

class Translatable(unicode):
    """
    Subclass of unicode. The value is translated immediately. A method args()
    is added that substitutes dollarsign-prefixed keywords using the
    string.Template class.
    """
    def __new__(cls, *args):
        return unicode.__new__(cls, _i18n(*args))

    def args(self, *args, **kwargs):
        return Template(self).substitute(*args, **kwargs)

_ = Translatable


# kate: indent-width 4;
