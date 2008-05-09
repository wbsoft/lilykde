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

    def iterDepthFirst(self):
        yield self

    def iterDepthLast(self, depth = -1, ring = 0):
        """
        Iterate over the children in rings, depth last.
        Set depth to restrict the search to a certain depth, -1 is unrestricted.
        Do not set ring in your invocation, it's used internally.
        """
        if ring == 0:
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

    def allChildren(self, cls, recursive = False):
        """
        iterate over all children of the current node if they are of
        the exact class cls.
        """
        for obj in recursive and self or self.children:
            if obj.__class__ is cls:
                yield obj

    def allChildrenLike(self, cls, recursive = False):
        """
        iterate over all children of the current node if they are of
        the class cls or a subclass.
        """
        for obj in recursive and self or self.children:
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

    def pretty(self, width=2, start=0):
        """ return a pretty indented representation of this node """
        return indent(unicode(self), width, start)


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
        result = '\n'.join('%% %s' % i for i in self.text.splitlines())
        # don't add a newline if the parent joins children using newlines.
        if not self.parent or not self.parent.multiline:
            result += '\n'
        return result


class MultiLineComment(Comment):
    """ A LilyPond comment block. The block must not contain a %} . """
    def _outputComment(self):
        return '%%{\n%s\n%%}' % self.text.strip()


class SmallComment(Comment):
    """ A very small comment in %{ %}. The text should not contain \n . """
    def _outputComment(self):
        return '%%{ %s %%}' % self.text.strip()


class QuotedString(Text):
    """ A string that is output inside double quotes. """
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

    def insert(self, where, obj):
        """
        Insert at index, or just before another node.
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

    def __len__(self):
        return len(self.children)

    def __getitem__(self, k):
        """ also supports slices """
        return self.children[k]

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
        if isinstance(k, slice):
            for i in self.children[k]:
                self.remove(i)
        else:
            self.remove(self.children[k])

    def __contains__(self, obj):
        return obj in self.children

    def __str__(self):
        if self.multiline and self.children:
            f, j = self.mfmt, self.mjoin
        else:
            f, j = self.fmt, self.join
        return f % j.join(unicode(i) for i in self.children)

    def iterDepthFirst(self):
        """ Iterate over all the children, and their children, etc. """
        yield self
        for i in self.children:
            for j in i.iterDepthFirst():
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
            for i in self.children:
                yield i
            for i in self.children:
                for j in i.iterDepthLast(depth, ring + 1):
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


class _RemoveIfOneChild(object):
    """ (mixin) removes formatting if exactly one child """
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


class Assignment(Container):
    """ A varname = value construct with it's value as its first child """
    nullStr = '""'

    def __init__(self, pdoc, varName, valueObj = None):
        Container.__init__(self, pdoc)
        self.varName = varName
        if valueObj:
            self.append(valueObj)

    # Convenience methods:
    def setValue(self, obj):
        self.clear()
        self.append(obj)

    def value(self):
        if self.children:
            return self.children[0]

    def __str__(self):
        return '%s = %s' % (self.varName, unicode(self.value() or self.nullStr))


def ifbasestring(cls = Container):
    """
    Ensure that the method is only called for basestring objects.
    Otherwise the same method from (by default) Container is called.
    """
    def dec(func):
        cont = getattr(cls, func.func_name)
        def newfunc(obj, varName, *args):
            f = isinstance(varName, basestring) and func or cont
            return f(obj, varName, *args)
        return newfunc
    return dec


class _HandleVars(object):
    """
    A powerful mixin class that makes handling unique variable assignments
    inside a Container more easy.
    Mixin before Container, so you can get to the items by using their
    string names.
    """
    childClass = Assignment

    def all(self):
        """
        Iterate over name, value pairs. To create a dict:
        dict(h.all())
        """
        for i in self.allChildrenLike(self.childClass):
            yield i.varName, i.value()

    @ifbasestring()
    def __getitem__(self, varName):
        for i in self.allChildrenLike(self.childClass):
            if i.varName == varName:
                return i

    @ifbasestring()
    def __setitem__(self, varName, valueObj):
        if not isinstance(valueObj, Node):
            valueObj = self.importNode(valueObj)
        h = self[varName]
        if h:
            h.setValue(valueObj)
        else:
            self.childClass(self, varName, valueObj)

    @ifbasestring()
    def __contains__(self, varName):
        return bool(self[varName])

    @ifbasestring()
    def __delitem__(self, varName):
        h = self[varName]
        if h:
            self.remove(h)

    def importNode(self, obj):
        """
        Try to interprete the object and transform it into a Node object
        of the right species.
        """
        return QuotedString(self.doc, obj)


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


class Paper(_HandleVars, Section):
    secName = 'paper'
    pass


class HeaderEntry(Assignment):
    """ A header with it's value as its first child """
    pass


class Header(_HandleVars, Section):
    secName = 'header'
    childClass = HeaderEntry
    pass


class Layout(_HandleVars, Section):
    secName = 'layout'
    pass


class Midi(_HandleVars, Section):
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
b.insert(s, v)
t = Score(b)
h = Header(t)

h['title'] = "Preludium in G"
h['composer'] = "Wilbert Berendsen (*1971)"
h['title'] = "Preludium in A"
h.insert(Comment(h, "Not sure if this is the right name"), h['composer'])
print dict(h.all())
print h['title'].__class__
Text(t, 'c1')

