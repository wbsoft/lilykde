# This file is part of LilyDOM, http://lilykde.googlecode.com/
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

r"""
LilyPond DOM

(c) 2008 Wilbert Berendsen
License: GPL.

A simple Document Object Model for LilyPond documents.

The purpose is to easily build a LilyPond document with good syntax,
not to fully understand all features LilyPond supports. (This DOM does
not enforce a legal LilyPond file.)

All elements of a LilyPond document inherit Node.

"""

class Node(object):
    
    def __init__(self, parent=None):
        self._parent = None
        self._children = []
        if parent:
            parent.append(self)

    def parent(self):
        """
        The parent, or None if the node has no parent.
        """
        return self._parent

    def setParent(self, parent):
        """
        Takes away node from current parent and appends to other.
        """
        if parent is not self._parent:
            parent.append(self)
    
    def removeFromParent(self):
        """
        Removes self from parent.
        """
        if self._parent:
            self._parent.remove(self)

    def append(self, node):
        """
        Appends an object to the current node. It will be reparented, that
        means it will be removed from it's former parent (if it had one).
        """
        assert isinstance(node, Node)
        node.removeFromParent()
        self._children.append(node)
        node._parent = self
        
    def index(self, node):
        """
        Return the index of the given object in our list of children.
        """
        return self._children.index(node)

    def insert(self, where, node):
        """
        Insert at index, or just before another node.
        """
        assert isinstance(node, Node)
        if isinstance(where, Node):
            where = self.index(where)
        node.removeFromParent()
        self._children.insert(where, node)
        node._parent = self
        
    def remove(self, node):
        """
        Removes the given child object.
        See also: removeFromParent()
        """
        self._children.remove(node)
        node._parent = None

    def replace(self, what, node):
        """
        Replace child at index or specified node with a replacement node.
        """
        assert isinstance(node, Node)
        if isinstance(what, Node):
            old = what
            what = self.index(what)
        else:
            old = self._children[what]
        node.removeFromParent()
        node._parent = self
        self._children[what] = obj
        old._parent = None

