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

import os, re
from glob import glob

from kdeui import KInputDialog

from lilykde.util import py2qstringlist, kconfig
from lilykde.editor import runOnSelection

from lilykde import config, editor, language

# Translate the messages
from lilykde.i18n import _

_wordSub = re.compile(r'[^\W0-9_]+', re.U).sub

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

    def paths():
        """ build a list of paths based on config """
        # in which prefixes to look for relative paths
        if 'KDEDIRS' in os.environ:
            prefixes = os.environ['KDEDIRS'].split(':')
        else:
            prefixes = ['/usr', '/usr/local']
            if 'KDEDIR' in os.environ:
                prefixes.append(os.environ['KDEDIR'])
        # if the path is not absolute, add it to all prefixes.
        for path in conf["paths"].splitlines() or defaultpaths:
            if os.path.isabs(path):
                yield path
            else:
                for pref in prefixes:
                    yield os.path.join(pref, path)

    # now find the hyph_xx_XX.dic files
    dicfiles = (f
        for p in paths() if os.path.isdir(p)
            for f in glob(os.path.join(p, 'hyph_*.dic')) if os.path.isfile(f))

    # present the user with human readable language names
    all_languages = kconfig("all_languages", True, False, "locale")

    # default to the users current locale if not used before
    defaultlang = None

    global hyphdicts
    # empty it, because we might be called again when the user changes
    # the settings.
    hyphdicts = {}
    for dic in dicfiles:
        lang = os.path.basename(dic)[5:-4]
        # find a human readable name belonging to the language code
        for i in lang, lang.split('_')[0]:
            name = all_languages.group(i).get("Name")
            if name:
                name = '%s  (%s)' % (name, lang)
                hyphdicts[name] = dic
                # set current locale as default
                if lang == language:
                    defaultlang = name
                break
        else:
            hyphdicts[lang] = dic

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
        editor.topLevelWidget()
    )
    if ok:
        lang = unicode(lang)
        conf["lastused"] = lang
        return lang

@runOnSelection
def hyphenateText(text):
    """
    Add lyrics hyphenation to the selected text.
    """
    lang = askLanguage()
    if lang:
        from hyphenator import Hyphenator
        h = Hyphenator(hyphdicts[lang])
        return _wordSub(lambda m: h.inserted(m.group(), ' -- '), text)

@runOnSelection
def deHyphenateText(text):
    """
    Remove lyrics hyphenation from selected text.
    """
    return text.replace(' -- ', '')



# kate: indent-width 4;
