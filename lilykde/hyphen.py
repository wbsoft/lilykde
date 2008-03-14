"""
This module contains the user interface for breaking Lyrics text
using the hyphenator module.
"""

import re
import os, os.path
from glob import glob
from locale import getdefaultlocale

from kdeui import KInputDialog

import kate

from lilykde.i18n import _
from lilykde.util import py2qstringlist, qstringlist2py, runOnSelection, kconfig

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

hyphdicts = {}

def findDicts():
    paths = config["paths"].splitlines() or defaultpaths
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
    paths = (p for p in res if os.path.isdir(p))

    # present the user with human readable language names
    all_languages = kconfig("all_languages", True, False, "locale")

    # default to the users current locale if not used before
    try:
        currentlang = getdefaultlocale()[0]
    except ValueError:
        currentlang = ""
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
                        if lang == currentlang: defaultlang = name
                        break
                else:
                    hyphdicts[lang] = g

    # if not used before, write the current locale (if existing) as default
    if defaultlang and config["lastused"] not in hyphdicts:
        config["lastused"] = defaultlang

findDicts()

def askLanguage():
    """
    Ask the user which language to use.
    Returns None if the user cancels the dialog.
    """
    lang = config["lastused"] or ""
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
        config["lastused"] = lang
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
