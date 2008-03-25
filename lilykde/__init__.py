"""
LilyKDE
"""

from lilykde.util import kconfig

def config(group=None):
    """
    Return the master KConfig object for "lilykderc", or
    a KConfigGroup (wrapper) object if a group name is given.
    """
    k = kconfig("lilykderc", False, False)
    return group and k.group(group) or k


# kate: indent-width 4;
