"""
LilyPond DOM

a simple Document Object Model for LilyPond documents.

The purpose is to easily build a LilyPond document with good syntax,
not to fully understand all features LilyPond supports.


"""

import re

class Document(object):
    """ A single LilyPond document """

    commentLevel = 8
    typographicalQuotes = True

    pass


class Node(object):
    """ Abstract base class """

    def __init__(self, pdoc):
        """
        if pdoc is a Document, save a pointer.
        if pdoc is a Node, append self to parent, and
        keep a pointer of the parent's doc.
        """
        if isinstance(pdoc, Node):
            pdoc.append(self)
            self.doc = pdoc.doc
        else:
            self.doc = pdoc
            self.parent = None


class Text(Node):
    """ A piece of text """
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
    mfmt, mjoin = '\n%s\n', '\n'
    multiline = False

    def __init__(self, *args):
        Node.__init__(self, *args)
        self.children = []

    def append(self, obj):
        self.children.append(obj)
        if obj.parent:
            obj.parent.remove(obj)
        obj.parent = self

    def remove(self, obj):
        self.children.remove(obj)
        obj.parent = None

    def childrenStr(self):
        return (unicode(i) for i in self.children)

    def __str__(self):
        if self.multiline:
            return self.mfmt % self.mjoin.join(self.childrenStr())
        else:
            return self.fmt % self.join.join(self.childrenStr())


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
    """ (abstract) removes pre and post if exactly one child """
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


