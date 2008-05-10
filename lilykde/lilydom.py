"""
LilyPond DOM

a simple Document Object Model for LilyPond documents.

The purpose is to easily build a LilyPond document with good syntax,
not to fully understand all features LilyPond supports. (This DOM does
not enforce a legal LilyPond file.)

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

The Document has a root Container object in .body, that's instantiated
by default.

Every Node keeps a reference to its parent in .parent, and its doc in .doc.

Example:

>>> from lilydom import *
>>> d=Document()
>>> d.body
<Body>
>>> Text(d.body, '\\version "2.11.46"')
<Text> \version "2.11.46"
>>> print d
\version "2.11.46"

>>> h=Header(d.body)
>>> h['composer'] = "Johann Sebastian Bach" #Header autogenerates some subnodes!
>>> h
<Header> \header { composer = "Johann Sebastian B...
>>> tree(h)
<Header> \header { composer = "Johann Sebastian B...
  <HeaderEntry> composer = "Johann Sebastian Bach"
    <QuotedString> "Johann Sebastian Bach"
>>> print h.pretty()
\header {
  composer = "Johann Sebastian Bach"
}
>>> print d
\version "2.11.46"
\header {
  composer = "Johann Sebastian Bach"
}


"""

import re


# pitches
# nl
class pitchwriter(object):
    def __init__(self, names, accs, special = None):
        self.names = names
        self.accs = accs
        self.special = special or ()

    def __call__(self, note, alter = 0):
        pitch = self.names[note]
        if alter:
            acc = self.accs[int(alter * 4 + 4)]
            # FIXME: warn if no alter defined
            pitch += acc
        for s, r in self.special:
            pitch = pitch.replace(s, r)
        return pitch


pitchInfo = {
    'nederlands': (
        ('c','d','e','f','g','a','b'),
        ('eses', 'eseh', 'es', 'eh', '', 'ih','is','isih','isis'),
        (('ees', 'es'), ('aes', 'as'))
    ),
}

pitchNames = dict(
    (lang, pitchwriter(*data)) for lang, data in pitchInfo.iteritems())


def indentGen(sourceLines, indentStr = '  ', d = 0):
    """
    A generator that walks on the source lines, and returns
    properly indented LilyPond code.
    """
    for t in sourceLines:
        if d and re.match(r'}|>|%}', t):
            d -= 1
        yield indentStr * d + t
        if re.search(r'(\{|<|%{)$', t):
            d += 1


def xmlescape(t):
    """ Escapes a string so that it can be used in an xml attribute """
    for s, r in (
        ('&', '&amp;'),
        ('<', '&gt;'),
        ('>', '&lt;'),
        ('"', '&quot;'),
        ('\n', '&#10;'),
    ):
        t = t.replace(s, r)
    return t


# small helper functions to get strings out of generators
def xml(obj):
    """ returns the XML representation of the object as a string """
    return ''.join(obj.xml())

def indent(obj):
    """ returns the indented LilyPond representation as a string """
    return ''.join(obj.indent())


class Document(object):
    """ A single LilyPond document """

    indentStr = '  '
    commentLevel = 8
    typographicalQuotes = True
    language = "nederlands"
    xmlIndentStr = '  '

    def __init__(self):
        self.body = Body(self)

    def __str__(self):
        return indent(self.body)


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

    def iterDepthFirst(self, depth = -1):
        """
        Iterate over all the children, and their children, etc.
        Set depth to restrict the search to a certain depth, -1 is unrestricted.
        """
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

    def allDescendants(self, cls, depth = -1):
        """
        iterate over all children of the current node if they are of
        the exact class cls.
        """
        for obj in self.iterDepthLast(depth):
            if obj.__class__ is cls:
                yield obj

    def allDescendantsLike(self, cls, depth = -1):
        """
        iterate over all children of the current node if they are of
        the class cls or a subclass.
        """
        for obj in self.iterDepthLast(depth):
            if isinstance(obj, cls):
                yield obj

    def isDescendantOf(self, parentObj):
        """ find parent in ancestors? """
        for obj in self.ancestors():
            if obj is parentObj:
                return True
        return False

    def isDangling(self):
        """ Returns whether the current Node is part of its Document """
        return not self.isDescendantOf(self.doc.body)

    def toplevel(self):
        """ returns the toplevel parent Node of this node """
        obj = self
        while obj.parent:
            obj = obj.parent
        return obj

    def copy(self):
        """
        Return a deep copy of this object, as a dangling tree belonging
        to the same document.
        """
        n = object.__new__(self.__class__)
        n.doc = self.doc
        for i in vars(self):
            if i not in ('doc', 'children', 'parent'):
                a = getattr(self, i)
                setattr(n, i, a.__class__(a))
        return n

    def indent(self, start=0):
        """ return a pretty indented representation of this node """
        for line in indentGen(unicode(self).splitlines(), self.doc.indentStr):
            yield line + '\n'

    def __repr__(self):
        """ return a representation for debugging purposes """
        maxlen = 50
        r = unicode(self).replace('\n', ' ')
        if len(r) > maxlen + 2:
            r = r[:maxlen] + '...'
        return '<%s> %s' % (self.__class__.__name__, r)

    def xmlattrs(self):
        """
        Returns all relevant instance variables as a XML attribute string
        """
        return ''.join(' %s="%s"' % (k, xmlescape(unicode(v)))
            for k, v in vars(self).iteritems()
                if k not in ('doc', 'children', 'parent'))

    def xml(self, indent = 0):
        """
        Generates XML (line by line / element by element) of the current node.
        """
        ind = self.doc.xmlIndentStr * indent
        tag = self.__class__.__name__
        attrs = self.xmlattrs()
        yield '%s<%s%s/>\n' % (ind, tag, attrs)


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


class Version(Node):
    """ a LilyPond version instruction """
    def __init__(self, pdoc, version):
        Node.__init__(self, pdoc)
        self.version = version

    def __str__(self):
        return r'\version "%s"' % self.version


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
        """
        Appends an object to the current node. It will be reparented, that
        means it will be removed from it's former parent (if it had one).
        """
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
        """
        Removes the given child object.
        See also: removeFromParent()
        """
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

    def copy(self):
        """
        Return a deep copy of this object, as a dangling tree belonging
        to the same document.
        """
        n = Node.copy(self)
        n.children = []
        for i in self.children:
            n.append(i.copy())
        return n

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

    def iterDepthFirst(self, depth = -1):
        """
        Iterate over all the children, and their children, etc.
        Set depth to restrict the search to a certain depth, -1 is unrestricted.
        """
        yield self
        if depth != 0:
            for i in self.children:
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
            for i in self.children:
                yield i
            for i in self.children:
                for j in i.iterDepthLast(depth, ring + 1):
                    yield j

    def xml(self, indent = 0):
        """
        Generates XML (line by line / element by element) of the current node.
        """
        ind = self.doc.xmlIndentStr * indent
        tag = self.__class__.__name__
        attrs = self.xmlattrs()
        if self.children:
            yield '%s<%s%s>\n' % (ind, tag, attrs)
            for i in self.children:
                for x in i.xml(indent + 1):
                    yield x
            yield '%s</%s>\n' % (ind, tag)
        else:
            yield '%s<%s%s/>\n' % (ind, tag, attrs)


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
    """ Simultaneous polyphonic expressions """
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
    E.g.:
    >>> h = Header(doc)
    >>> h['composer'] = "Johann Sebastian Bach"
    creates a subnode (by default Assignment) with the name 'composer', and
    that node again gets an autogenerated subnode of type QuotedString (If the
    argument wasn't already a Node).
    """
    childClass = Assignment

    def all(self):
        """
        Iterate over name, value pairs. To create a dict:
        dict(h.all())
        """
        for i in self.allDescendantsLike(self.childClass, 1):
            yield i.varName, i.value()

    @ifbasestring()
    def __getitem__(self, varName):
        for i in self.allDescendantsLike(self.childClass, 1):
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
        Try to interpret the object and transform it into a Node object
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



class Pitch(Node):
    """
    A pitch with octave, note, alter.
    octave is specified by an integer, zero for the octave containing middle C.
    note is a number from 0 to 6, with 0 corresponding to pitch C and 6
    corresponding to pitch B.
    alter is the number of whole tones for alteration (can be a Rational)
    """
    def __init__(self, pdoc, octave = 0, note = 0, alter = 0):
        Node.__init__(self, pdoc)
        self.octave = octave
        self.note = note
        self.alter = alter

    def __str__(self):
        """
        print the pitch in the preferred language.
        """
        p = pitchNames[self.doc.language](self.note, self.alter)
        if self.octave < -1:
            return p + ',' * (-self.octave - 1)
        elif self.octave > -1:
            return p + "'" * (self.octave + 1)
        return p


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
v = Version(d, "2.11.46")
b.insert(s, v)
t = Score(b)
h = Header(t)

h['title'] = "Preludium in G"
h['composer'] = "Wilbert Berendsen (*1971)"
h['title'] = "Preludium in A"
h.insert(Comment(h, "Not sure if this is the right name"), h['composer'])
Text(t, 'c1')

