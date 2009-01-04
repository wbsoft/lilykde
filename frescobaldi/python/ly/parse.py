# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
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
General functions that parse LilyPond document text.
"""

import os, re

def findIncludeFiles(lyfile, basedir=None, files=None):
    """
    A generator that finds files included by the document in lyfile.
    You should leave basedir and files to None, as it will be used
    to remember the base directory in recursive calls.
    """
    if files is None:
        files = set()
        basedir = os.path.dirname(lyfile)
    if os.access(lyfile, os.R_OK):
        files.add(lyfile)
        directory = os.path.dirname(lyfile)
        for f in re.findall(r'\\include\s*"([^"]+)"', file(lyfile).read()):
            # old include (relative to master file)
            findIncludeFiles(os.path.join(basedir, f), basedir, files)
            # new, recursive, relative include
            if directory != basedir:
                findIncludeFiles(os.path.join(directory, f), basedir, files)
    return files
