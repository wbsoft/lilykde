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

import re

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

    def children(self):
        """
        Our children, may be an empty list.
        """
        return self._children

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
        if isinstance(where, Node):
            old = where
            where = self.index(where)
        else:
            old = self._children[where]
        node.removeFromParent()
        node._parent = self
        self._children[where] = node
        old._parent = None

    def __nonzero__(self):
        """ We are always true """
        return True
    
    def __len__(self):
        """ Return the number of children """
        return len(self._children)

    def __getitem__(self, k):
        """ also supports slices """
        return self._children[k]

    def __setitem__(self, k, obj):
        """ also supports slices """
        if isinstance(k, slice):
            if k.step:
                # extended slice, number of items must be same
                if len(obj) == len(self[k]):
                    for new, old in zip(obj, self[k]):
                        self.replace(old, new)
                else:
                    raise ValueError, \
                        "extended slice and replacement must have same length"
            else:
                del self[k]
                start = k.start or 0
                # save the obj iterator results because obj could change ...
                for d, new in enumerate(tuple(obj)):
                    self.insert(start + d, new)
        else:
            self.replace(k, obj)

    def __delitem__(self, k):
        """ also supports slices """
        if isinstance(k, slice):
            for i in self[k]:
                self.remove(i)
        else:
            self.remove(self[k])

    def __contains__(self, node):
        return node in self._children

    def clear(self):
        """ Remove all children """
        del self[:]

    def ancestors(self):
        """ climb the tree up over the parents """
        node = self
        while node._parent:
            node = node._parent
            yield node

    def previousSibling(self):
        """
        Return the object just before this one in the parent's list of children.
        None if this is the first child, or if we have no parent.
        """
        if self._parent:
            i = self._parent.index(self)
            if i > 0:
                return self._parent[i-1]

    def nextSibling(self):
        """
        Return the object just after this one in the parent's list of children.
        None if this is the last child, or if we have no parent.
        """
        if self._parent:
            i = self._parent.index(self)
            if i < len(self._parent) - 1:
                return self._parent[i+1]

    def previousSiblings(self):
        """
        Iterate (backwards) over the preceding items in our parent's
        list of children.
        """
        node = self.previousSibling()
        while node:
            yield node
            node = self.previousSibling()

    def nextSiblings(self):
        """
        Iterate over the following items in our parent's list of children.
        """
        node = self.nextSibling()
        while node:
            yield node
            node = self.nextSibling()

    def isChildOf(self, otherNode):
        """ find parent in ancestors? """
        for node in self.ancestors():
            if node is otherNode:
                return True
        return False

    def toplevel(self):
        """ returns the toplevel parent Node of this node """
        node = self
        while node._parent:
            node = node._parent
        return node

    def iterDepthFirst(self, depth = -1):
        """
        Iterate over all the children, and their children, etc.
        Set depth to restrict the search to a certain depth, -1 is unrestricted.
        """
        yield self
        if depth != 0:
            for i in self:
                for j in i.iterDepthFirst(depth - 1):
                    yield j

    def iterDepthLast(self, depth = -1, ring = 0):
        """
        Iterate over the children in rings, depth last.
        Set depth to restrict the search to a certain depth, -1 is unrestricted.
        Do not set ring in your invocation, it's used internally.
        """
        if ring == 0:
            yield self
        if ring != depth:
            for i in self:
                yield i
            for i in self:
                for j in i.iterDepthLast(depth, ring + 1):
                    yield j

    # LilyPond related stuff, could move to subclass
    def isAtom(self):
        """
        Returns True if this element is single LilyPond atom, word, note, etc.
        When it is the only element inside { }, the brackets can be removed.
        """
        return False
   
    def nlBefore(self):
        """
        Return the number of newlines this object wants before it.
        """
        return 0
        
    def nlAfter(self):
        """
        Return the number of newlines this object wants after it.
        """
        return 0

    def ly(self, receiver):
        """
        Returns printable output for this object.
        """
        return ''

    def concat(self, other, repl=" "):
        """
        Returns a string with newlines to concat this node to another one.
        If zero newlines are requested, repl is returned, defaulting to a space.
        """
        return '\n' * max(self.nlAfter(), other.nlBefore()) or repl
        

class Text(Node):
    """ A leaf node with arbitrary text """
    
    def __init__(self, text="", parent=None):
        super(Text, self).__init__(parent)
        self.text = text
    
    def ly(self, receiver):
        return self.text


class Comment(Text):
    def nlAfter(self):
        return 1

    def ly(self, receiver):
        return re.compile('^', re.M).sub('% ')


class Newline(Node):
    """ A newline. """
    def nlAfter(self):
        return 1


class BlankLine(Newline):
    """ A blank line. """
    def nlBefore(self):
        return 1


class Container(Node):
    """ A node that concatenates its children on output """
    def nlBefore(self):
        if self.children():
            return self[0].nlBefore()
        else:
            return 0
    
    def nlAfter(self):
        if self.children():
            return self[-1].nlAfter()
        else:
            return 0
            
    def ly(self, receiver):
        if len(self) == 0:
            return ''
        else:
            n = self[0]
            res = [n.ly(receiver)]
            for m in self[1:]:
                res.append(n.concat(m))
                res.append(m.ly(receiver))
                n = m
            return "".join(res)
        

class Enclosed(Container):
    """ An expression between brackets: { ... } or << >> """
    may_remove_brackets = False
    pre = ""
    post = ""
    
    def nlBefore(self):
        return 0
    
    def nlAfter(self):
        return 0
    
    def ly(self, receiver):
        if len(self) == 0:
            return " ".join((self.pre, self.post))
        sup = super(Enclosed, self)
        before, text, after = sup.nlBefore(), sup.ly(receiver), sup.nlAfter()
        if before or after or '\n' in text:
            return "".join((self.pre, "\n" * max(before, 1), text,
                                      "\n" * max(after, 1), self.post))
        elif self.may_remove_brackets and len(self) == 1 and self[0].isAtom():
            return text
        else:
            return " ".join((self.pre, text, self.post))


class Seq(Enclosed):
    """ An expression between { } """
    pre = "{"
    post = "}"
    

class Sim(Enclosed):
    """ An expression between << >> """
    pre = "<<"
    post = ">>"


class Seqr(Seq):
    may_remove_brackets = True
    

class Simr(Sim):
    may_remove_brackets = True
    
    
