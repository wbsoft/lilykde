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
import ly.rx

def findIncludeFiles(lyfile):
    """
    Finds files included by the document in lyfile.
    """
    files = set()
    basedir = os.path.dirname(lyfile)
    
    def find(lyfile):
        if os.access(lyfile, os.R_OK):
            files.add(lyfile)
            directory = os.path.dirname(lyfile)
            # read the file and delete the comments.
            text = ly.rx.all_comments.sub('', file(lyfile).read())
            for f in ly.rx.include_file.findall(text):
                # old include (relative to master file)
                find(os.path.join(basedir, f))
                # new, recursive, relative include
                if directory != basedir:
                    find(os.path.join(directory, f))
    find(lyfile)
    return files
