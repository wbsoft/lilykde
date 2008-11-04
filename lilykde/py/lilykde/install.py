# This file is part of LilyKDE, http://lilykde.googlecode.com/
#
# Copyright (c) 2008  Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# See http://www.gnu.org/licenses/ for more information.

"""
This script is run if the user uses LilyKDE for the first time
or upgraded LilyKDE to a new version.

The old version number (if any) is still in [install]/version;
it will be updated after this script has been run.

"""

from lilykde.util import kconfig

from lilykde import config

def install_katefiletyperc():
    """
    Installs a LilyKDE group into katefiletyperc with settings
    for LilyPond files.
    """
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



def install():
    """
    Main install functions, called always if this file is imported
    """
    conf = config()
    if "version" not in conf:
        install_katefiletyperc()


install()


# kate: indent-width 4;
