"""
This module contains the user interface for breaking Lyrics text
using the hyphenator module.
"""

import re
import os, os.path
from glob import glob

from kdeui import KInputDialog

import kate

from lilykde.i18n import _
from lilykde.util import py2qstringlist, qstringlist2py, runOnSelection

from lilykde import config
config = config.group("hyphenation")

defaultpaths = (
    '/opt/OpenOffice.org/share/dict/ooo',
    'lib/openoffice/share/dict/ooo',
    'share/apps/koffice/hyphdicts',
    'lib/scribus/dicts',
    'share/myspell',
    'share/hunspell',
)

def searchDicts():
    paths = config.readPathListEntry("paths") or defaultpaths
    # build a list of existing paths.
    # is the path is not absolute, try with all known prefixes.
    res = []
    prefixes = os.environ['KDEDIRS'].split(':')
    for path in paths:
        if os.path.isabs(path):
            res.append(path)
        else:
            for pref in prefixes:
                res.append(os.path.join(pref, path))
    paths = [p for p in res if os.path.isdir(p)]
    # now find the hyph_xx_XX.dic files
    hyphdicts = {}
    for p in paths:
        for g in glob(os.path.join(p, 'hyph_*.dic')):
            if os.path.isfile(g):
                name = re.sub(r'hyph_(.*).dic', r'\1', os.path.basename(g))
                hyphdicts[unicode(name)] = g
    return hyphdicts

hyphdicts = searchDicts()

def askLanguage():
    """
    Ask the user which language to use
    """
    lang = config.readEntry("lastused") or ""
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
        config.writeEntry("lastused", lang)
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
    return re.compile(r'\w+', re.U).sub(hyphrepl, text)

@runOnSelection
def deHyphenateText(text):
    """
    Remove lyrics hyphenation from selected text
    """
    return text.replace(' -- ', '')

