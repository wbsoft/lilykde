# config module

from qt import QString, QStringList
from lilykde.util import py2qstringlist, qstringlist2py, kconfig, kconfiggroup

master = kconfig("lilykderc", False, False)
group = master.group

# kate: indent-width 4;
