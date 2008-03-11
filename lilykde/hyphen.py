"""
This module contains the user interface for breaking Lyrics text
using the hyphenator module.
"""

import re
import os, os.path
from glob import glob

import kate

from lilykde.i18n import _
from lilykde.util import py2qstringlist, qstringlist2py, sorry

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
                hyphdicts[name] = g
    return hyphdicts


def deHyphenateText():
    """remove hyphenation from selected text"""
    sel = kate.view().selection
    if not sel.exists:
        sorry(_("Please select some text first."))
        return
    d, v, text = kate.document(), kate.view(), sel.text
    d.editingSequence.begin()
    sel.removeSelectedText()
    v.insertText(text.replace(' -- ', ''))
    d.editingSequence.end()

