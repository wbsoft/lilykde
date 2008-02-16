import os.path
from locale import getdefaultlocale

# TODO: in system-wide installation use standard locale dirs and lilykde
# textdomain

# Find sibling dir mo/ in parent of current script dir
modir = os.path.join(os.path.dirname(__file__), "..", "mo")

_ = lambda s: s

try:
    lang, encoding = getdefaultlocale()
    if lang:
        for mofile in lang, lang.split("_")[0]:
            try:
                fp = open(os.path.join(modir, mofile + ".mo"))
                import gettext
                _ = gettext.GNUTranslations(fp).ugettext
                break
            except IOError:
                continue
except ValueError:
    pass
