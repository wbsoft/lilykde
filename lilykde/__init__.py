"""
LilyKDE
"""

import os
from qt import QMimeSourceFactory

appdir = os.path.dirname(__path__[0])

QMimeSourceFactory.defaultFactory().addFilePath(
    os.path.join(appdir, "pics"))

def config(group=None):
    """
    Return the master KConfig object for "lilykderc", or
    a KConfigGroup (wrapper) object if a group name is given.
    """
    from lilykde.util import kconfig
    k = kconfig("lilykderc", False, False)
    return group and k.group(group) or k


# kate: indent-width 4;
