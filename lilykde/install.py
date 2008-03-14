"""
This script is run if the user uses LilyKDE for the first time
or upgraded LilyKDE to a new version.

The old version number (if any) is still in [install]/version;
it will be updated after this script has been run.

"""

from lilykde.util import kconfig

from lilykde import config
conf = config.group("install")


def install_katefiletyperc():
    rc = kconfig("katefiletyperc", False, False).group("LilyKDE")
    rc["Mimetypes"] = "text/x-lilypond"
    rc["Priority"] = 10
    rc["Section"] = "LilyPond"
    rc["Wildcards"] = "*.ly; *.ily; *.lyi"
    rc["Variables"] = ("kate: "
        "encoding utf8; "
        "tab-width 4; "
        "indent-width 2; "
        "space-indent on; "
        "replace-tabs on; "
        "replace-tabs-save on; "
        "dynamic-word-wrap off; "
        "show-tabs off; "
        "indent-mode varindent; "
        r"var-indent-indent-after (\{[^}]*$|<<(?![^>]*>>)); "
        r"var-indent-unindent ^\s*(#?\}|>>); "
        r"var-indent-triggerchars }>; "
    )




if "version" not in conf:
    install_katefiletyperc()

