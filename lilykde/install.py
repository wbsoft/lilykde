"""
This script is run if the user uses LilyKDE for the first time
or upgraded LilyKDE to a new version.

The old version number (if any) is still in [install]/version;
it will be updated after this script has been run.

"""

from lilykde.util import kconfig, kconfiggroup

from lilykde import config
conf = config.group("install")


def install_katefiletyperc():
    rc = kconfig("katefiletyperc", False, False)





if "version" not in conf:
    install_katefiletyperc()

