# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009, 2010 by Wilbert Berendsen
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

from __future__ import unicode_literals

""" Hyphenator functionality for Frescobaldi """

import locale, os, re
from glob import glob

import ly.rx
from hyphenator import Hyphenator

from PyQt4.QtGui import QLabel, QListWidget, QVBoxLayout
from PyKDE4.kdecore import KConfig, KGlobal, i18n
from PyKDE4.kdeui import KDialog, KMessageBox

try:
    language, encoding = locale.getdefaultlocale()
except ValueError:
    language, encoding = None, None

defaultPaths = (
    'share/dict/ooo',
    'lib/openoffice/share/dict/ooo',
    '/opt/OpenOffice.org/share/dict/ooo',
    'koffice/hyphdicts',
    'share/apps/koffice/hyphdicts',
    'lib/scribus/dicts',
    'share/scribus/dicts',
    'share/scribus-ng/dicts',
    'share/myspell',
    'share/myspell/dicts',
    'share/hunspell',
)

hyphdicts = {}

def config(group="hyphenation"):
    return KGlobal.config().group(group)

def findDicts():
    """ Find installed hyphen dictionary files """
    conf = config("hyphenation")
    def paths():
        """ build a list of paths based on config """
        # in which prefixes to look for relative paths
        prefixes = KGlobal.dirs().kfsstnd_prefixes().split(os.pathsep)
        prefixes = set(prefixes + ['/usr/', '/usr/local/'])
        # if the path is not absolute, add it to all prefixes.
        for path in conf.readEntry("paths", defaultPaths):
            if os.path.isabs(path):
                yield path
            else:
                for pref in prefixes:
                    yield os.path.join(pref, path)
                for d in KGlobal.dirs().findDirs("data", path):
                    yield d

    # now find the hyph_xx_XX.dic files
    dicfiles = (f
        for p in paths() if os.path.isdir(p)
            for f in glob(os.path.join(p, 'hyph_*.dic')) if os.access(f, os.R_OK))

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
            name = KGlobal.locale().languageCodeToName(i)
            if name:
                name = '{0} ({1})'.format(name, lang)
                hyphdicts[name] = dic
                # set current locale as default
                if lang == language:
                    defaultlang = name
                break
        else:
            hyphdicts[lang] = dic

    # if not used before, write the current locale (if existing) as default
    if defaultlang and conf.readEntry("lastused", "") not in hyphdicts:
        conf.writeEntry("lastused", defaultlang)
        conf.sync()

findDicts()


def hyphenate(text, mainwindow):
    """
    Ask the user which language to use.
    Returns None if the user cancels the dialog or no hyphenation pattern files
    could be found.
    """
    if not hyphdicts:
        KMessageBox.sorry(mainwindow, i18n(
            "Could not find any hyphenation dictionaries.\n\n"
            "Please install a package containing some and/or or configure the "
            "search path to find them in the Frescobaldi settings under "
            "\"Paths.\""))
        return
    
    conf = config("hyphenation")
    lang = conf.readEntry("lastused", "")
    langs = list(sorted(hyphdicts.keys()))
    index = lang in langs and langs.index(lang) or 0
    
    d = KDialog(mainwindow)
    d.setButtons(KDialog.ButtonCode(KDialog.Ok | KDialog.Cancel | KDialog.Help))
    d.setCaption(i18n("Hyphenate Lyrics Text"))
    d.setHelp("lyrics")
    layout = QVBoxLayout()
    d.mainWidget().setLayout(layout)
    layout.addWidget(QLabel(i18n("Please select a language:")))
    listbox = QListWidget()
    layout.addWidget(listbox)
    listbox.addItems(langs)
    listbox.setCurrentRow(index)
    listbox.setFocus()
    if d.exec_():
        lang = langs[listbox.currentRow()]
        conf.writeEntry("lastused", lang)
        conf.sync()
        # get hyphenator
        h = Hyphenator(hyphdicts[lang])
        return ly.rx.lyric_word.sub(lambda m: h.inserted(m.group(), ' -- '), text)
