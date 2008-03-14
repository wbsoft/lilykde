# config module

from qt import QString, QStringList
from kdecore import KConfig, KConfigGroup
from lilykde.util import py2qstringlist, qstringlist2py

_main = KConfig("lilykderc", False, False)

# all settings are saved in some group, master is not used.

class group(KConfigGroup):
    """
    Handles a KConfigGroup like a Python dictionary
    """
    def __init__(self, groupname):
        KConfigGroup.__init__(self, _main, groupname)

    def get(self, key, default=''):
        return unicode(KConfigGroup.readEntry(self, key, default))

    def __getitem__(self, key):
        return unicode(KConfigGroup.readEntry(self, key))

    def __setitem__(self, key, value):
        KConfigGroup.writeEntry(self, key, value)

    def __contains__(self, key):
        return KConfigGroup.hasKey(self, key)

# kate: indent-width 4;
