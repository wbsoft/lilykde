import gettext
try:
    _ = gettext.translation('lilykde').ugettext
except IOError:
    def _(message): return message
