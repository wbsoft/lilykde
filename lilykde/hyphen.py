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
This module contains the user interface for breaking Lyrics text
using the hyphenator module.
"""

import re
import os
from glob import glob

from kdeui import KInputDialog

import kate

from lilykde.util import py2qstringlist, kconfig
from lilykde.kateutil import runOnSelection

from lilykde import config, language

# Translate the messages
from lilykde.i18n import _


defaultpaths = (
    '/opt/OpenOffice.org/share/dict/ooo',
    'lib/openoffice/share/dict/ooo',
    'share/apps/koffice/hyphdicts',
    'lib/scribus/dicts',
    'share/myspell',
    'share/hunspell',
)

hyphdicts = {}

def findDicts():
    conf = config("hyphenation")
    paths = conf["paths"].splitlines() or defaultpaths
    # build a list of existing paths.
    # is the path is not absolute, try with all known prefixes.
    res = []

    if 'KDEDIRS' in os.environ:
        prefixes = os.environ['KDEDIRS'].split(':')
    else:
        prefixes = ['/usr', '/usr/local']
        if 'KDEDIR' in os.environ:
            prefixes.append(os.environ['KDEDIR'])

    for path in paths:
        if os.path.isabs(path):
            res.append(path)
        else:
            for pref in prefixes:
                res.append(os.path.join(pref, path))
    paths = (p for p in res if os.path.isdir(p))

    # present the user with human readable language names
    all_languages = kconfig("all_languages", True, False, "locale")

    # default to the users current locale if not used before
    defaultlang = None

    # now find the hyph_xx_XX.dic files
    global hyphdicts
    # empty it again, because we might be called again when the user changes
    # the settings.
    hyphdicts = {}
    for p in paths:
        for g in glob(os.path.join(p, 'hyph_*.dic')):
            if os.path.isfile(g):
                lang = re.sub(r'hyph_(.*).dic', r'\1', os.path.basename(g))
                # find a human readable name belonging to the language code
                for i in lang, lang.split('_')[0]:
                    name = all_languages.group(i).get("Name")
                    if name:
                        name = '%s  (%s)' % (name, lang)
                        hyphdicts[name] = g
                        # set current locale as default
                        if lang == language:
                            defaultlang = name
                        break
                else:
                    hyphdicts[lang] = g

    # if not used before, write the current locale (if existing) as default
    if defaultlang and conf["lastused"] not in hyphdicts:
        conf["lastused"] = defaultlang

findDicts()

def askLanguage():
    """
    Ask the user which language to use.
    Returns None if the user cancels the dialog.
    """
    conf = config("hyphenation")
    lang = conf["lastused"] or ""
    langs = list(sorted(hyphdicts.keys()))
    index = lang in langs and langs.index(lang) or 0
    lang, ok = KInputDialog.getItem(
        _("Language selection"),
        _("Please select a language:"),
        py2qstringlist(langs), index, False,
        kate.mainWidget().topLevelWidget()
    )
    if ok:
        lang = unicode(lang)
        conf["lastused"] = lang
        return lang

@runOnSelection
def hyphenateText(text):
    """
    Add hyphenation to the selected text
    """
    lang = askLanguage()
    if not lang: return None
    from hyphenator import Hyphenator
    h = Hyphenator(hyphdicts[lang])
    def hyphrepl(matchObj):
        return h.inserted(matchObj.group(), ' -- ')
    return re.compile(r'[^\W0-9_]+', re.U).sub(hyphrepl, text)

@runOnSelection
def deHyphenateText(text):
    """
    Remove lyrics hyphenation from selected text
    """
    return text.replace(' -- ', '')



# kate: indent-width 4;
