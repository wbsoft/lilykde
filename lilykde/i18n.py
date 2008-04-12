import gettext
from os.path import join, dirname
from locale import getdefaultlocale
from string import Template
from lilykde import appdir

# TODO: in system-wide installation use standard locale dirs and lilykde
# textdomain

def getTranslations():
    # Find sibling dir mo/ in parent of current script dir
    modir = join(appdir, "mo")
    try:
        lang, encoding = getdefaultlocale()
        if lang:
            for mofile in lang, lang.split("_")[0]:
                try:
                    fp = open(join(modir, mofile + ".mo"))
                    return gettext.GNUTranslations(fp)
                except IOError:
                    pass
    except ValueError:
        pass
    return gettext.NullTranslations()

#translations = gettext.translation('lilykde', fallback=True)
translations = getTranslations()

def _i18n(msgid1, msgid2=None, n=None):
    if n is None:
        return translations.ugettext(msgid1)
    else:
        return translations.ungettext(msgid1, msgid2, n)

class Translatable(unicode):
    """
    Subclass of unicode. The value is translated immediately. A method args()
    is added that substitutes dollarsign-prefixed keywords using the
    string.Template class.
    """
    def __new__(cls, *args):
        return unicode.__new__(cls, _i18n(*args))

    def args(self, *args, **kwargs):
        return Template(self).substitute(*args, **kwargs)

_ = Translatable


# kate: indent-width 4;
