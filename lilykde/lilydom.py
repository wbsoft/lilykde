r"""
LilyPond DOM

(c) 2008 Wilbert Berendsen
License: GPL.

A simple Document Object Model for LilyPond documents.

The purpose is to easily build a LilyPond document with good syntax,
not to fully understand all features LilyPond supports. (This DOM does
not enforce a legal LilyPond file.)

All elements of a LilyPond document inherit Node.

the main branches of Node are:
    - Text: contains a string, cannot have child Nodes.
    - Container: contains child Node objects and optional pre, join and post
        text. You can access the child nodes using the [] syntax. This also
        supports slices.

The main document is represented by a Document object.
The contents of the document are in doc.body , which is a Body node,
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
>>> d = Document()
>>> b = d.body
>>> Version(b, '2.11.46')
<Version> \version "2.11.46"
>>> s = Sim(Score(b), multiline=True)
>>> man = Sim(PianoStaff(s), multiline=True)
>>> ped = Seq(Staff(s))
>>> r = Seq(Staff(man, 'right'))
>>> l = Seq(Staff(man, 'left'))
>>> h = Header(d)
>>> b.insert(1, h)
>>> h['composer'] = "Johann Sebastian Bach" #Header autogenerates some subnodes!
>>> h['title'] = "Prelude and Fuge in C Major"
>>> print d
\version "2.11.46"

\header {
  composer = "Johann Sebastian Bach"
  title = "Prelude and Fuge in C Major"
}

\score {
  <<
    \new PianoStaff <<
      \new Staff = "right" {  }
      \new Staff = "left" {  }
    >>
    \new Staff {  }
  >>
}

You can always get to any element later and edit it:
>>> man.parent.instrName('Manuals','Man.')
>>> print d
\version "2.11.46"

\header {
  composer = "Johann Sebastian Bach"
  title = "Prelude and Fuge in C Major"
}

\score {
  <<
    \new PianoStaff \with {
      instrumentName = "Manuals"
      shortInstrumentName = "Man."
    } <<
      \new Staff = "right" {  }
      \new Staff = "left" {  }
    >>
    \new Staff {  }
  >>
}

There is also fairly simple XML support. LilyDOM can save and load
the XML structure of a Document (and also of any particular node):

>>> print d.toXml()
<?xml version="1.0" encoding="UTF-8"?>
<Document>
  <Body>
    <Version text="2.11.46"/>
    <Header>
      <HeaderEntry name="composer">
        <QuotedString text="Johann Sebastian Bach"/>
      </HeaderEntry>
      <HeaderEntry name="title">
        <QuotedString text="Prelude and Fuge in C Major"/>
      </HeaderEntry>
    </Header>
    <Score>
      <Sim multiline="True">
        <PianoStaff>
          <With>
            <Assignment name="instrumentName">
              <QuotedString text="Manuals"/>
            </Assignment>
            <Assignment name="shortInstrumentName">
              <QuotedString text="Man."/>
            </Assignment>
          </With>
          <Sim multiline="True">
            <Staff cid="right">
              <Seq/>
            </Staff>
            <Staff cid="left">
              <Seq/>
            </Staff>
          </Sim>
        </PianoStaff>
        <Staff>
          <Seq/>
        </Staff>
      </Sim>
    </Score>
  </Body>
</Document>

"""

import re
from rational import Rational

# pitches
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
    'english': (
        ('c','d','e','f','g','a','b'),
        ('ff', 'tqf', 'f', 'qf', '', 'qs', 's', 'tqs', 'ss'),
        (('flat', 'f'), ('sharp', 's'))
    ),
    'deutsch': (
        ('c','d','e','f','g','a','h'),
        ('eses', 'eseh', 'es', 'eh', '', 'ih','is','isih','isis'),
        (('ees', 'es'), ('aes', 'as'), ('hes', 'b'))
    ),
    'svenska': (
        ('c','d','e','f','g','a','h'),
        ('essess', '', 'ess', '', '', '','iss','','ississ'),
        (('ees', 'es'), ('aes', 'as'), ('hess', 'b'))
    ),
    'italiano': (
        ('do', 're', 'mi', 'fa', 'sol', 'la', 'si'),
        ('bb', 'bsb', 'b', 'sb', '', 'sd', 'd', 'dsd', 'dd')
    ),
    'espanol': (
        ('do', 're', 'mi', 'fa', 'sol', 'la', 'si'),
        ('bb', '', 'b', '', '', '', 's', '', 'ss')
    ),
    'portuges': (
        ('do', 're', 'mi', 'fa', 'sol', 'la', 'si'),
        ('bb', 'btqt', 'b', 'bqt', '', 'sqt', 's', 'stqt', 'ss')
    ),
    'vlaams': (
        ('do', 're', 'mi', 'fa', 'sol', 'la', 'si'),
        ('bb', '', 'b', '', '', '', 'k', '', 'kk')
    ),
}

pitchInfo['norsk'] = pitchInfo['deutsch']
pitchInfo['suomi'] = pitchInfo['deutsch']
pitchInfo['catalan'] = pitchInfo['italiano']


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


# XML utility functions

def xmlescape(t):
    """ Escapes a string so that it can be used in an xml attribute """
    for s, r in (
        ('&', '&amp;'),
        ('<', '&gt;'),
        ('>', '&lt;'),
        ('"', '&quot;'),
        ("'", '&apos;'),
        ('\n', '&#10;'),
        ('\t', '&#9;'),
    ):
        t = t.replace(s, r)
    return t

def xmlunescape(t):
    """ Unescape an XML attribute string """
    t = re.compile(r'\&#(x)?(.*?);').sub(
        lambda m: unichr(int(m.group(2), m.group(1) and 16 or 10)), t)
    for s, r in (
        ('&gt;', '<'),
        ('&lt;', '>'),
        ('&quot;', '"'),
        ('&apos;', "'"),
        ('&amp;', '&'),
    ):
        t = t.replace(s, r)
    return t

def xmlformatattrs(d):
    """
    Return dict (or nested sequence of key-value pairs)
    (of unicode objects) as a XML attribute string
    """
    return ''.join(' %s="%s"' % (k, xmlescape(v)) for k, v in d)

def xmlattrs(s):
    """
    Return a interator over key, value pairs of unescaped xml attributes
    from the string.

    This can be easily converted in a dict using dict(xmlattrs(string))
    """
    for m in re.compile(r'(\w+)\s*=\s*"(.*?)"').finditer(s):
        yield m.group(1), xmlunescape(m.group(2))

def xmltags(s):
    """"
    Returns an iterator that walks over all the XML elements in the
    string (discarding text between the elements).

    Each iteration consists of a four-tuple:
        tag: the tag name
        start: is this an opening tag? (bool)
        end: is this a closing tag? (bool)
        attrs: iterable over the attributes.

    Both start and end can be true (with an empty <element/>).
    """
    for m in re.compile(r'<(/)?(\w+)(.*?)(/)?>', re.DOTALL).finditer(s):
        tag = m.group(2)
        start = not m.group(1)
        end = bool(m.group(1) or m.group(4))
        attrs = xmlattrs(m.group(3))
        yield tag, start, end, attrs

def setattrs(obj, attrs):
    """
    Sets attributes of the object to values from the attrs iterable.
    The attrs in the attrs iterable are always of str/unicode type.

    Class attributes of the object's class are consulted to determine
    if the attr needs to be converted from str/unicode to something else.

    If a class attribute attrName + '_func' exists, it is called.
    Otherwise class attribute 'attr_func' is tried. If that also not
    exists, the attribute remains a str/unicode object.
    """
    cls = obj.__class__
    for attr, value in attrs:
        f = getattr(cls, attr + '_func', None) or \
            getattr(cls, 'attr_func', lambda s:s)
        setattr(obj, attr, f(value))

# small helper functions to get strings out of generators
def xml(obj):
    """ returns the XML representation of the object as a string """
    return ''.join(obj.xml())

def indent(obj):
    """ returns the indented LilyPond representation as a string """
    return ''.join(obj.indent())


def str2rat(s):
    """Converts a string like '1/2' to a Rational"""
    return Rational(*map(int,s.split('/')))


class Document(object):
    """ A single LilyPond document """

    indentStr = '  '
    commentLevel = 8
    typographicalQuotes = True
    language = "nederlands"
    xmlIndentStr = '  '

    def __init__(self):
        self.body = Body(self)

    def _getbody(self):
        return self._body
    def _setbody(self, body):
        assert isinstance(body, Node)
        self._body = body
    body = property(_getbody, _setbody)

    def __str__(self):
        """ Return the LilyPond document, formatted and indented. """
        return ''.join(self.body.indent())

    def copy(self):
        """ Return a deep copy of the document. """
        d = Document()
        d.body = self.body.copy()
        for i in vars(self):
            if not i.startswith('_'):
                a = getattr(self, i)
                setattr(d, i, a.__class__(a))
        return d

    def toXml(self, encoding='UTF-8'):
        """
        Returns the document as an UTF-8 (by default) encoded XML string.
        """
        attrs = xmlformatattrs((k, unicode(v))
            for k, v in vars(self).iteritems()
            if not k.startswith('_'))
        return ('<?xml version="1.0" encoding="%s"?>\n'
                '<Document%s>\n%s</Document>\n' % (
                    encoding, attrs, ''.join(self.body.xml(1))
                )).encode(encoding)

    def parseXml(self, s):
        """
        Parse a string of XML and return the Node object (with possible
        children).

        All classes can define how their instance attributes should be
        converted from string to the right type (int, bool, Rational, etc.)

        If a class attribute attrName + '_func' exists, it is called.
        Otherwise class attribute 'attr_func' is tried. If that also not
        exists, the attribute remains a str/unicode object.
        """
        e = None
        for tag, start, end, attrs in xmltags(s):
            if start:
                cls = eval(tag)
                assert issubclass(cls, Node)
                e = cls.__new__(cls, e or self)
                setattrs(e, attrs)
            if end and e:
                if e.parent:
                    e = e.parent
                else:
                    return e
        # this is only reached when not all tags are closed properly.
        return e and e.toplevel()

    @staticmethod
    def fromXml(s):
        """
        Parse the XML string (containing a full Document) and return
        a Document object.

        If the string starts with an XML declaration with an encoding
        pseudo attribute, the string is decoded first.
        """
        m = re.compile(
            r'<\?xml.*?encoding\s*=\s*"(.*?)".*?\?>', re.DOTALL).match(s)
        if m:
            s = s.decode(m.group(1))
        m = re.compile(
            r'<Document\s*(.*?)>(.*?)</Document>', re.DOTALL).search(s)
        if m:
            doc = Document()
            setattrs(doc, xmlattrs(m.group(1)))
            doc.body = doc.parseXml(m.group(2))
            return doc

    def toXmlFile(self, filename, encoding='UTF-8'):
        """
        Write the document out to an XML file with default encoding UTF-8.
        """
        f = open(filename, 'w')
        f.write(self.toXml(encoding))
        f.close()

    @staticmethod
    def fromXmlFile(filename):
        """
        Read an XML document from a file and return the document object.
        """
        return Document.fromXml(open(filename).read())


    # helper methods to quickly instantiate certain Node objects:
    def _smarkup(self, command, *args):
        r"""
        Evaluate all the args and create a simple markup command
        like \italic, etc. enclosing the arguments.
        """
        obj = MarkupEncl(self, command)
        for a in args:
            if isinstance(a, basestring):
                Text(obj, a)
            elif isinstance(a, Node):
                obj.append(a)
        return obj

    def smarkup(f):
        """
        Decorator that returns a simple markup-creating function, containing
        a call to _smarkup with a command argument based on the function name.
        """
        def _smarkup_func(self, *args):
            return self._smarkup(f.func_name.replace('_', '-'), *args)
        _smarkup_func.__doc__ = f.__doc__
        return _smarkup_func

    #arrow-head axis (integer) direction (direction) filled (boolean)
    #  Produce an arrow head in specified direction and axis.
    #  Use the filled head if filled is specified.

    #beam width (number) slope (number) thickness (number)
    #  Create a beam with the specified parameters.

    @smarkup
    def bigger():
        "Increase the font size relative to current setting."
        pass

    @smarkup
    def bold():
        "Switch to bold font-series."
        pass

    @smarkup
    def box():
        "Draw a box round arg."
        pass

    @smarkup
    def bracket():
        "Draw vertical brackets around arg"
        pass

    @smarkup
    def caps():
        "Emit arg as small caps."
        pass

    @smarkup
    def center_align():
        "Put args in a centered column."
        pass

    #char num
    #Produce a single character. For example, \char #65 produces the letter A.

    @smarkup
    def circle():
        "Draw a circle around arg."
        pass

    @smarkup
    def column():
        "Stack the markups in args vertically."
        pass

    #combine m1 (markup) m2 (markup)

    @smarkup
    def concat():
        "Concatenate args in a horizontal line, without spaces inbetween."
        pass


    #...



class Node(object):
    """ Abstract base class """

    def __new__(cls, pdoc, *args, **kwargs):
        """
        if pdoc is a Document, save a pointer.
        if pdoc is a Node, append self to parent, and
        keep a pointer of the parent's doc.
        """
        obj = object.__new__(cls)
        obj._parent = None
        if isinstance(pdoc, Document):
            obj._doc = pdoc
        else:
            assert isinstance(pdoc, Node)
            obj._doc = pdoc._doc
            pdoc.append(obj)
        return obj

    doc = property(lambda self: self._doc)

    def _getparent(self):
        return self._parent
    def _setparent(self, value):
        self._parent = value
    parent = property(_getparent, _setparent,
            doc = "The parent Node of this Node.")

    def __nonzero__(self):
        """ We are always true """
        return True

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
        Don't use this yourself.
        Normally append, insert and replace will handle everything.
        If the new parent belongs to another document, all our descendants
        will be moved over to the new document.
        """
        self.removeFromParent()
        self.parent = newParent
        if newParent._doc is not self._doc:
            for i in self.iterDepthFirst():
                i._doc = newParent._doc

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

    def previousSibling(self):
        """
        Return the object just before this one in the parent's list of children.
        None if this is the first child, or if we have no parent.
        """
        if self.parent:
            i = self.parent.index(self)
            if i > 0:
                return self.parent[i-1]

    def nextSibling(self):
        """
        Return the object just after this one in the parent's list of children.
        None if this is the last child, or if we have no parent.
        """
        if self.parent:
            i = self.parent.index(self)
            if i < len(self.parent) - 1:
                return self.parent[i+1]

    def previousSiblings(self):
        """
        Iterate (backwards) over the preceding items in our parent's
        list of children.
        """
        obj = self.previousSibling()
        while obj:
            yield obj
            obj = self.previousSibling()

    def nextSiblings(self):
        """
        Iterate over the following items in our parent's list of children.
        """
        obj = self.nextSibling()
        while obj:
            yield obj
            obj = self.nextSibling()

    def descendants(self, cls, depth = -1):
        """
        iterate over all descendants of the current node if they are of
        the exact class cls.
        """
        for obj in self.iterDepthLast(depth):
            if obj.__class__ is cls:
                yield obj

    def descendantsLike(self, cls, depth = -1):
        """
        iterate over all descendants of the current node if they are of
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
        n = self.__class__.__new__(self.__class__, self.doc)
        for i in vars(self):
            if not i.startswith('_'):
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
        Return all relevant instance variables as a iterable key-value sequence.
        You can subclass this method if you have attributes that cannot be
        rendered using unicode.
        """
        return ((k, unicode(v)) for k, v in vars(self).iteritems()
            if not k.startswith('_'))

    def xml(self, indent = 0):
        """
        Generates XML (line by line / element by element) of the current node.
        """
        ind = self.doc.xmlIndentStr * indent
        tag = self.__class__.__name__
        attrs = xmlformatattrs(self.xmlattrs())
        yield '%s<%s%s/>\n' % (ind, tag, attrs)


class Container(Node):
    """ (abstract) Contains bundled expressions """

    multiline = False
    multiline_func = eval

    def __new__(cls, pdoc, *args, **kwargs):
        obj = Node.__new__(cls, pdoc)
        obj._children = []
        if 'multiline' in kwargs:
            obj.multiline = kwargs['multiline']
        return obj

    def index(self, obj):
        """
        Return the index of the given object in our list of children.
        """
        return self._children.index(obj)

    def append(self, obj):
        """
        Appends an object to the current node. It will be reparented, that
        means it will be removed from it's former parent (if it had one).
        """
        assert isinstance(obj, Node)
        self._children.append(obj)
        obj.reparent(self)

    def insert(self, where, obj):
        """
        Insert at index, or just before another node.
        """
        assert isinstance(obj, Node)
        if isinstance(where, Node):
           where = self.index(where)
        obj.reparent(self)
        self._children.insert(where, obj)

    def remove(self, obj):
        """
        Removes the given child object.
        See also: removeFromParent()
        """
        self._children.remove(obj)
        obj.parent = None

    def replace(self, what, obj):
        """
        Replace child at index or specified Node with a replacement object.
        """
        assert isinstance(obj, Node)
        if isinstance(what, Node):
            old = what
            what = self.index(what)
        else:
            old = self[what]
        obj.reparent(self)
        self._children[what] = obj
        old.parent = None

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

    def __contains__(self, obj):
        return obj in self._children

    def clear(self):
        """ Remove all children """
        del self[:]

    def copy(self):
        """
        Return a deep copy of this object, as a dangling tree belonging
        to the same document.
        """
        n = super(Container, self).copy()
        for i in self:
            n.append(i.copy())
        return n

    def __str__(self):
        join = self.multiline and '\n' or ' '
        # while joining, remove the join character if the previous
        # element already ends with a newline (e.g. a comment).
        s = '\0'.join(i for i in map(unicode, self) if i)
        return s.replace('\n\0', '\n').replace('\0\n', '\n').replace('\0', join)

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

    def xml(self, indent = 0):
        """
        Generates XML (line by line / element by element) of the current node.
        """
        ind = self.doc.xmlIndentStr * indent
        tag = self.__class__.__name__
        attrs = xmlformatattrs(self.xmlattrs())
        if len(self):
            yield '%s<%s%s>\n' % (ind, tag, attrs)
            for i in self:
                for x in i.xml(indent + 1):
                    yield x
            yield '%s</%s>\n' % (ind, tag)
        else:
            yield '%s<%s%s/>\n' % (ind, tag, attrs)


class Text(Node):
    """ Any piece of text """
    def __init__(self, pdoc, text):
        self.text = text

    def __str__(self):
        return self.text


class Newline(Node):
    """
    One or more newlines.
    Use this to go to a new line or insert blank lines.
    """
    count = 1

    def __init__(self, pdoc, count = None):
        if count is not None:
            self.count = count

    def __str__(self):
        return '\n' * self.count


class Comment(Text):
    """ A LilyPond comment line """
    level_func = int

    def __init__(self, pdoc, text, level = 2):
        self.text = text
        self.level = level

    def __str__(self):
        if self.level <= self.doc.commentLevel:
            return self._outputComment()
        else:
            return ''

    def _outputComment(self):
        # comment lines end with a newline.
        return ''.join('%%%s\n' % i for i in self.text.splitlines())


class BlockComment(Comment):
    """ A LilyPond comment block. The block must not contain a %} . """
    def _outputComment(self):
        t = self.text.replace('%}', '')
        if '\n' in t:
            return '%%{\n%s\n%%}' % t.strip()
        else:
            return '%%{ %s %%}' % t.strip()


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


class Scheme(Text):
    """ A Scheme expression, without the extra # prepended """
    def __str__(self):
        return '#%s' % self.text


class Version(Text):
    """ a LilyPond version instruction """
    def __str__(self):
        return r'\version "%s"' % self.text


class EnclosedBase(Container):
    """
    The abstract base class for enclosed blocks (in << >>, { }, < >, etc.)
    """
    pre, post = '', ''

    def __str__(self):
        s = super(EnclosedBase, self).__str__()
        join = ('\n' in s or s and self.multiline) and '\n' or ' '
        s = '\0'.join(i for i in (self.pre, s, self.post) if i)
        return s.replace('\n\0', '\n').replace('\0', join)


class Body(EnclosedBase):
    """
    A vertical list of LilyPond lines/statements, joined with newlines.
    """
    pre, post = '', ''
    multiline = True
    pass


class Seq(EnclosedBase):
    """ Sequential expressions """
    pre, post = '{', '}'
    pass


class Sim(EnclosedBase):
    """ Simultaneous expressions """
    pre, post = '<<', '>>'
    pass


class _RemoveFormattingIfOneChild(object):
    """
    (Mixin)
    Removes formatting if the element has exactly one child, and that child
    is not a Text node with spaces in it.
    """
    def __str__(self):
        if len(self) != 1 or isinstance(self[0], Text) \
                and len(self[0].text.split()) != 1:
            return super(_RemoveFormattingIfOneChild, self).__str__()
        else:
            return unicode(self[0])


class _RemoveIfEmpty(object):
    """ (mixin) Do not output anything if we have no children """
    def __str__(self):
        if len(self):
            return super(_RemoveIfEmpty, self).__str__()
        else:
            return ''


class Seqr(_RemoveFormattingIfOneChild, Seq): pass
class Simr(_RemoveFormattingIfOneChild, Sim): pass


class Assignment(Container):
    """ A varname = value construct with it's value as its first child """
    nullStr = '""'

    def __init__(self, pdoc, name, valueObj=None):
        self.name = name
        if valueObj:
            self.append(valueObj)

    # Convenience methods:
    def setValue(self, obj):
        self.clear()
        self.append(obj)

    def value(self):
        if len(self):
            return self[0]

    def __str__(self):
        return '%s = %s' % (self.name, unicode(self.value() or self.nullStr))


class Identifier(Node):
    r"""
    An identifier, prints as \name.

    The name can refer to e.g. Assignments that are in the toplevel,
    to find the contents of the identifier.
    """
    def __init__(self, pdoc, name):
        self.name = name

    def __str__(self):
        return '\\%s' % self.name


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
        for i in self.descendantsLike(self.childClass, 1):
            yield i.name, i.value()

    def ifbasestring(func):
        """
        Ensure that the method is only called for basestring objects.
        Otherwise the same method from the super class is called.
        """
        def newfunc(obj, name, *args):
            if isinstance(name, basestring):
                return func(obj, name, *args)
            else:
                f = getattr(super(_HandleVars, obj), func.func_name)
                return f(name, *args)
        return newfunc

    @ifbasestring
    def __getitem__(self, name):
        for i in self.descendantsLike(self.childClass, 1):
            if i.name == name:
                return i

    @ifbasestring
    def __setitem__(self, name, valueObj):
        if not isinstance(valueObj, Node):
            valueObj = self.importNode(valueObj)
        h = self[name]
        if h:
            h.setValue(valueObj)
        else:
            self.childClass(self, name, valueObj)

    @ifbasestring
    def __contains__(self, name):
        return bool(self[name])

    @ifbasestring
    def __delitem__(self, name):
        h = self[name]
        if h:
            self.remove(h)

    def importNode(self, obj):
        """
        Try to interpret the object and transform it into a Node object
        of the right species.
        """
        return QuotedString(self.doc, obj)


class _Name(object):
    """ (Mixin) prints a prefix, useable for a command """
    name = ''
    def __str__(self):
        s = super(_Name, self).__str__()
        if s:
            return '\\%s %s' % (self.name, s)
        else:
            return '\\%s' % self.name


class Section(_Name, EnclosedBase):
    r"""
    (abstract)
    A section like \header, \score, \paper, \with, etc.
    with the children inside braces { }
    """
    pre, post = '{', '}'
    multiline = True
    pass


class Book(Section):
    r""" A \book should only contain \score or \paper blocks """
    name = 'book'
    pass


class Score(Section):
    name = 'score'
    pass


class Paper(_HandleVars, Section):
    name = 'paper'
    pass


class HeaderEntry(Assignment):
    """ A header with its value as its first child """
    pass


class Header(_HandleVars, Section):
    name = 'header'
    childClass = HeaderEntry
    pass


class Layout(_HandleVars, Section):
    name = 'layout'
    pass


class Midi(_HandleVars, Section):
    name = 'midi'
    pass


class With(_RemoveIfEmpty, _HandleVars, Section):
    name = 'with'
    pass


class Context(With):
    name = 'context'

    def __init__(self, pdoc, name = None, **kwargs):
        if name is not None:
            ContextName(self, name)


class ContextName(Text):
    def __str__(self):
        return '\\%s' % self.text


class ContextType(Container):
    r"""
    \new or \context Staff = 'bla' \with { } << music >>

    A \with (With) element is added automatically as the first child as soon
    as you use our convenience methods that manipulate the variables
    in \with. If the \with element is empty, it does not print anything.
    You should add one other music object to this.
    """
    cid = ''
    name = '' # only used in subclasses!
    newcontext = True
    newcontext_func = eval

    def __init__(self, pdoc, cid = '', new = None):
        if cid:
            self.cid = cid # LilyPond context id
        if new is not None:
            self.newcontext = new # print \new (True) or \context (False)

    def __str__(self):
        res = [self.newcontext and '\\new' or '\\context',
            self.name or self.__class__.__name__]
        if self.cid:
            res.append('= "%s"' % self.cid)
        res.append(super(ContextType, self).__str__())
        return ' '.join(res)

    def instrName(self, longName = None, shortName = None):
        """
        Puts instrumentName assignments in the attached with clause.
        """
        w = self.getWith()
        if longName is None:
            del w['instrumentName']
        else:
            w['instrumentName'] = longName
        if shortName is None:
            del w['shortInstrumentName']
        else:
            w['shortInstrumentName'] = shortName

    def getWith(self):
        """
        Gets the attached with clause. Creates it if not there.
        """
        if len(self) == 0 or not isinstance(self[0], With):
            self.insert(0, With(self.doc))
        return self[0]


class ChoirStaff(ContextType): pass
class ChordNames(ContextType): pass
class CueVoice(ContextType): pass
class Devnull(ContextType): pass
class DrumStaff(ContextType): pass
class DrumVoice(ContextType): pass
class FiguredBass(ContextType): pass
class FretBoards(ContextType): pass
class Global(ContextType): pass
class GrandStaff(ContextType): pass
class GregorianTranscriptionStaff(ContextType): pass
class GregorianTranscriptionVoice(ContextType): pass
class InnerChoirStaff(ContextType): pass
class InnerStaffGroup(ContextType): pass
class Lyrics(ContextType): pass
class MensuralStaff(ContextType): pass
class MensuralVoice(ContextType): pass
class NoteNames(ContextType): pass
class PianoStaff(ContextType): pass
class RhythmicStaff(ContextType): pass
class ScoreContext(ContextType):
    r"""
    Represents the Score context in LilyPond, but the name would
    collide with the Score class that represents \score { } constructs.

    Because the latter is used more often, use ScoreContext to get
    \new Score etc.
    """
    name = 'Score'
    pass
class Staff(ContextType): pass
class StaffGroup(ContextType): pass
class TabStaff(ContextType): pass
class TabVoice(ContextType): pass
class VaticanaStaff(ContextType): pass
class VaticanaVoice(ContextType): pass
class Voice(ContextType): pass


class UserContext(ContextType):
    r"""
    Represents a context the user creates.
    e.g. \new MyStaff = cid << music >>
    """
    def __init__(self, pdoc, name, *args):
        super(UserContext, self).__init__(pdoc, *args)
        self.name = name


class ContextProperty(Node):
    """
    A Context.property or Context.layoutObject construct.

    call e.g. ContextProperty(p, 'aDueText', 'Staff') to get 'Staff.aDueText'.
    """
    def __init__(self, pdoc, prop, context = ""):
        self.prop = prop
        self.context = context

    def __str__(self):
        if self.context:
            f = '%s.%s'
            # TODO: if in \lyricmode or \lyrics, spaces around dot.
            return f % (self.context, self.prop)
        else:
            return self.prop


class Pitch(Node):
    """
    A pitch with octave, note, alter.
    octave is specified by an integer, zero for the octave containing middle C.
    note is a number from 0 to 6, with 0 corresponding to pitch C and 6
    corresponding to pitch B.
    alter is the number of whole tones for alteration (can be int or Rational)
    """
    octave_func = int
    note_func = int
    alter_func = staticmethod(str2rat)

    def __init__(self, pdoc, octave = 0, note = 0, alter = 0):
        self.octave = octave
        self.note = note
        self.alter = Rational(alter)

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


class Duration(Node):
    r"""
    A duration with duration (in logarithmical form): (-2 ... 8),
    where -2 = \longa, -1 = \breve, 0 = 1, 1 = 2, 2 = 4, 3 = 8, 4 = 15, etc,
    dots (number of dots),
    factor (Rational giving the scaling of the duration).
    """

    dur_func = int
    dots_func = int
    factor_func = staticmethod(str2rat)

    def __init__(self, pdoc, dur, dots = 0, factor = 1):
        self.dur = dur # log
        self.dots = dots
        self.factor = Rational(factor)

    def __str__(self):
        s = self.dur == -2 and '\\longa' or \
            self.dur == -1 and '\\breve' or '%i' % (1 << self.dur)
        s += '.' * self.dots
        if self.factor != 1:
            s += '*%s' % str(self.factor)
        return s


class Relative(_Name, Container):
    r"""
    relative <pitch> music

    You should add a Pitch (optionally) and another music object,
    e.g. Sim or Seq, etc.
    """
    name = 'relative'
    pass


class KeySignature(Node):
    r"""
    A key signature expression, like:

    \key c \major
    The pitch should be given in the arguments note and alter and is written
    out in the document's language.
    """
    note_func = int
    alter_func = staticmethod(str2rat)

    def __init__(self, pdoc, note = 0, alter = 0, mode = "major"):
        self.note = note
        self.alter = Rational(alter)
        self.mode = mode

    def __str__(self):
        pitch = pitchNames[self.doc.language](self.note, self.alter)
        return '\\key %s \\%s' % (pitch, self.mode)


class TimeSignature(Node):
    r"""
    A time signature, like: \time 4/4
    """
    attr_func = int

    def __init__(self, pdoc, num, beat):
        self.num = num
        self.beat = beat

    def __str__(self):
        return '\\time %i/%i' % (self.num, self.beat)


class Markup(_Name, Seqr):
    r"""
    The \markup command.
    You can add many children, in that case Markup automatically prints
    { and } around them.
    """
    name = 'markup'
    pass


class MarkupEncl(_Name, Seqr):
    """
    A markup that auto-encloses all its arguments, like 'italic', 'bold'
    etc.  You must supply the name.
    """
    def __init__(self, pdoc, name, *args):
        self.name = name


class MarkupCmd(_Name, Container):
    """
    A markup command with more or no arguments, that does not auto-enclose
    its arguments. Useful for commands like note-by-number or hspace.

    You must supply the name. Its arguments are its children.
    If one argument can be a markup list, use a Seq(r) construct for that.
    """
    def __init__(self, pdoc, name, *args):
        self.name = name


