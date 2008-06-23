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
PDFTK frontend to attach LilyPond source files to a PDF file.

Needs Pdftk installed. See http://www.accesspdf.com/pdftk .
"""

import os, re

from qt import QTimer

from lilykde import config
from lilykde.util import findexe
from lilykde.log import log

# Translate the messages
from lilykde.i18n import _

def pdftk():
    """ Returns the Pdftk command. """
    return config("commands").get('pdftk', 'pdftk')

def installed():
    """ Returns True if Pdftk is installed, otherwise False """
    return findexe(pdftk()) and True

def find_included_files(filename, directory):
    """
    Looks for LilyPond include statements in the given path
    and returns (as generator) the names of included files
    if they can be resolved.

    Until LilyPond supports recursive relative include paths,
    all paths are assumed to be relative to the directory of the
    given LilyPond source file.
    """
    full = os.path.join(directory, filename)
    if os.access(full, os.R_OK):
        yield filename
        for f in re.findall(r'\\include\s*"([^"]+)"', file(full).read()):
            for p in find_included_files(f, directory):
                yield p

def attach_files(ly, wait = 0):
    """
    Checks the ly file for includes, and attaches all files
    to the ly's PDF file.
    """
    import shutil, subprocess, tempfile, time

    directory, filename = os.path.split(ly)
    files = list(set(find_included_files(filename, directory)))
    pdf = os.path.splitext(ly)[0] + '.pdf'

    handle, temp = tempfile.mkstemp('.pdf')
    os.close(handle)

    wait += time.time()
    cmd = [pdftk(), pdf, 'attach_files'] + files + ['output', temp]

    try:
        retcode = subprocess.call(cmd, cwd = directory)
    except OSError, e:
        log.fail(_("Could not start Pdftk: %s") % e)
    else:
        if retcode == 0:
            # copy temp to the pdf, but do it not too quick if wait
            # was specified, otherwise KPDF could still be reading, and
            # will then possibly read a truncated file.
            def finish():
                shutil.copy(temp, pdf)
                os.remove(temp)
                log.ok(_(
                    "Embedded file %s in PDF.",
                    "Embedded files %s in PDF.",
                    len(files)
                    ) % '[%s]' % ', '.join(files))
            wait = int((wait - time.time()) * 1000)
            if wait > 0:
                QTimer.singleShot(wait, finish)
            else:
                finish()
            return
        else:
            log.fail('%s %s' % (
                _("Embedding files in PDF failed."),
                _("Return code: %i") % retcode))
    os.remove(temp)


# kate: indent-width 4;
