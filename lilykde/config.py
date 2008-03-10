# config module

from qt import QString, QStringList
from kdecore import KConfig, KConfigGroup

config = KConfig("lilykderc", False, False)

def qstringlist(l):
    """
    convert a list of strings to a QStringList
    """
    r.QStringList()
    for i in l:
        r.append(i)
    return r


class group(KConfigGroup):
    def __init__(self, groupname):
        super(group, self).__init__(config, groupname)

    def writePathEntry(key, path, *args):
        if type(path) not in (str, unicode, QString, QStringList):
            path = qstringlist(path)
        super(group, self).writePathEntry(key, path, *args)

