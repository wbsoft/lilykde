"""
LilyPond DOM

a simple Document Object Model for LilyPond documents.

The purpose is to easily build a LilyPond document with good syntax,
not to fully understand all features LilyPond supports.

This DOM does not enforce a legal LilyPond file. It adds some convenience when
you create objects though. E.g. when you add music expressions and \layout and
\midi blocks to a \score , they will always be printed in the right order.

All elements of a LilyPond document inherit Node.

the main branches of Node are:
    - Text: contains a string, cannot have child Nodes.
    - Container: contains child Node objects and optional pre, join and post
            text. You can find the child nodes in children, but never keep
            pointers to that list, nor change the values from outside!

The main document is represented by a Document object.
The contents of the document are in doc.body , which is a Container node,
created by default.

You create nodes by instantiating them.
The first parameter is always a parent Node OR a Document.

In the latter case, the Node is not added to anything, and you should keep
a reference to it. You can add a node to another one with append() or insert().



"""

import re

def indentGen(sourceLines, width = 2, start = 0):
    i = start * width
    for t in sourceLines:
        if i and re.match(r'}|>|%}', t):
            i -= width
        yield ' '*i + t
        if re.search(r'(\{|<|%{)$', t):
            i += width

def indent(text, width=2, start = 0):
    """ Indent a LilyPond file """
    return '\n'.join(indentGen(text.splitlines(), width, start)) + '\n'


class Document(object):
    """ A single LilyPond document """

    commentLevel = 8
    typographicalQuotes = True

    def __init__(self):
        self.body = Body(self)

    def __str__(self):
        return self.body.pretty()


class Node(object):
    """ Abstract base class """

    parent = None

    def __init__(self, pdoc):
        """
        if pdoc is a Document, save a pointer.
        if pdoc is a Node, append self to parent, and
        keep a pointer of the parent's doc.
        """
        if isinstance(pdoc, Document):
            self.doc = pdoc
        else:
            pdoc.append(self)
            self.doc = pdoc.doc

    def __iter__(self):
        yield self

    def removeFromParent(self):
        """ Removes self from parent """
        if self.parent:
            self.parent.remove(self)

    def replaceWith(self, newObj):
        """ Replace self in parent with new object """
        if self.parent:
            self.parent.replace(self, newObj)

    def reparent(self, newParent):
        """
        Don't use this yourself, normally append, insert, replace will
        handle everything.
        """
        self.removeFromParent()
        self.parent = newParent

    def ancestors(self):
        """ climb the tree up over the parents """
        obj = self
        while obj.parent:
            obj = obj.parent
            yield obj

    def findParent(self, cls):
        """
        Search for the first parent object of the exact given class, and
        return it, otherwise returns None.
        """
        for obj in self.ancestors():
            if obj.__class__ is cls:
                return obj

    def findParentLike(self, cls):
        """
        Search for the first parent object that's an instance of the given
        class or a subclass, and return it, otherwise returns None.
        """
        for obj in self.ancestors():
            if isinstance(obj, cls):
                return obj

    def allChildren(self, cls):
        """
        iterate over all children of the current node if they are of
        the exact class cls.
        """
        for obj in self:
            if obj.__class__ is cls:
                yield obj

    def allChildrenLike(self, cls):
        """
        iterate over all children of the current node if they are of
        the class cls or a subclass.
        """
        for obj in self:
            if isinstance(obj, cls):
                yield obj

    def isChildOf(self, parentObj):
        """ find parent in ancestors? """
        for obj in self.ancestors():
            if obj is parentObj:
                return True
        return False

    def isDangling(self):
        """ Returns whether the current Node is part of its Document """
        return not self.isChildOf(self.doc.body)

    def toplevel(self):
        """ returns the toplevel parent Node of this node """
        obj = self
        while obj.parent:
            obj = obj.parent
        return obj

    def pretty(self, width=2):
        """ return a pretty indented representation of this node """
        return indent(unicode(self), width)


class Text(Node):
    """ Any piece of text """
    def __init__(self, pdoc, text):
        Node.__init__(self, pdoc)
        self.text = text

    def __str__(self):
        return self.text


class Comment(Text):
    """ A LilyPond comment line """
    def __init__(self, pdoc, text, level = 2):
        Text.__init__(self, pdoc, text)
        self.level = level

    def __str__(self):
        if self.level <= self.doc.commentLevel:
            return self._outputComment()
        else:
            return ''

    def _outputComment(self):
        return ''.join('%% %s\n' %i for i in self.text.splitlines())


class MultiLineComment(Comment):
    """ A LilyPond comment block. The block must not contain a %} . """
    def _outputComment(self):
        return '%%{\n%s\n%%}' % self.text.strip()


class SmallComment(Comment):
    """ A very small comment in %{ %}. The text should not contain \n . """
    def _outputComment(self):
        return '%%{ %s %%}' % self.text.strip()


class QuotedString(Text):
    def __str__(self):
        text = self.text
        if self.doc.typographicalQuotes:
            text = re.sub(r'"(.*?)"', u'\u201C\\1\u201D', text)
            text = re.sub(r"'(.*?)'", u'\u2018\\1\u2019', text)
            text = text.replace("'", u'\u2018')
        # escape regular double quotes
        text = text.replace('"', '\\"')
        # quote the string
        return '"%s"' % text


class Container(Node):
    """ (abstract) Contains bundled expressions """
    fmt, join = '%s', ' '
    mfmt, mjoin = '%s\n', '\n'
    multiline = False

    def __init__(self, pdoc, multiline=None):
        Node.__init__(self, pdoc)
        self.children = []
        if multiline is not None:
            self.multiline = multiline

    def append(self, obj):
        self.children.append(obj)
        obj.reparent(self)

    def insert(self, obj, where = 0):
        """
        Insert at index, or just before another node.
        Default: insert at beginning.
        """
        if isinstance(where, Node):
           where = self.children.index(where)
        obj.reparent(self)
        self.children.insert(where, obj)

    def remove(self, obj):
        self.children.remove(obj)
        obj.parent = None

    def replace(self, what, repl):
        """
        Replace child at index or specified Node with a replacement object.
        """
        if isinstance(what, Node):
            old = what
            what = self.children.index(what)
        else:
            old = self.children[what]
        repl.reparent(self)
        self.children[what] = repl
        old.parent = None

    def clear(self):
        """ Remove all children """
        for n in self.children:
            n.parent = None
        self.children = []

    def childrenStr(self):
        return (unicode(i) for i in self.children)

    def __str__(self):
        if self.multiline and self.children:
            return self.mfmt % self.mjoin.join(self.childrenStr())
        else:
            return self.fmt % self.join.join(self.childrenStr())

    def __iter__(self):
        """ Iterate over all the children """
        yield self
        for i in self.children:
            for j in i:
                yield j


class Body(Container):
    """ Just a sequence of lines or other blocks of Lily code """
    multiline = True
    pass


class Sim(Container):
    """ Simultaneous expressions """
    fmt = '<< %s >>'
    mfmt = '<<\n%s\n>>'
    pass


class Seq(Container):
    """ Sequential expressions """
    fmt = '{ %s }'
    mfmt = '{\n%s\n}'
    pass


class _RemoveIfOneChild(Container):
    """ (abstract) removes formatting if exactly one child """
    def __str__(self):
        if len(self.children) == 1:
            return unicode(self.children[0])
        else:
            return Container.__str__(self)


class Simr(_RemoveIfOneChild, Sim): pass
class Seqr(_RemoveIfOneChild, Seq): pass


class SimPoly(Sim):
    """ Simultaneous polyphone expressions """
    join, mjoin = r' \\ ', '\n\\\\\n'
    pass


class Section(Container):
    """
    (abstract)
    A section like \header, \score, \paper, \with, etc.
    with the children inside braces { }
    """
    fmt = '{ %s }'
    mfmt = '{\n%s\n}'
    multiline = True
    secName = ''
    def __str__(self):
        return '\\%s %s' % (self.secName, Container.__str__(self))


class Book(Section):
    """ A \book should only contain \score or \paper blocks """
    secName = 'book'
    pass


class Score(Section):
    secName = 'score'
    pass


class Paper(Section):
    secName = 'paper'
    pass


class Header(Section):
    secName = 'header'
    pass


class Layout(Section):
    secName = 'layout'
    pass


class Midi(Section):
    secName = 'midi'
    pass


class Context(Section):
    secName = 'context'
    pass


class With(Section):
    secName = 'with'
    pass

## testing
d = Document()
b = d.body
s = Score(b)
Seq(s)
Seq(s)
p = SimPoly(s, multiline=True)
Seq(p), Seq(p), Seq(p)
l = Layout(s)
m = Midi(s)
v = Text(d, r'\version "2.11.46"')
b.insert(v, s)
t = Score(b)
Header(t)
Text(t, 'c1')
