"""

This is a Python module to hyphenate text.

It is inspired by Ruby's Text::Hyphen, but currently reads standard *.dic files,
that must be installed separately.

In the future it's maybe nice if dictionaries could be distributed together with
this module, in a slightly prepared form, like in Ruby's Text::Hyphen.

Wilbert Berendsen, March 2008
info@wilbertberendsen.nl

License: LGPL.

"""

import sys
import re


# cache of hyph_*.dic file per-file patterns
_hdcache = {}

# precompile some stuff
_re_hex = re.compile(r'\^{2}([0-9a-f]{2})').sub
_re_parse = re.compile(r'(\d?)(\D?)').findall

def _hexrepl(matchObj):
    return unichr(int(matchObj.group(1), 16))


def int_alt(alt):
    """
    return a factory that instantiates ints with alt attached as
    the .alt attribute.
    """
    class Point(int):
        def __new__(cls, value):
            obj = int.__new__(cls, value)
            obj.alt = alt
            return obj
    return Point


class Hyphenator(object):
    """
    Reads a hyph_*.dic file and stores the hyphenation patterns.
    parameters:
    -filename : filename of hyph_*.dic to read
    -left: make the first syllabe not shorter than this
    -right: make the last syllabe not shorter than this
    -cache: if true, use a cached copy of the dic file, if possible

    left and right may also later be changed:
      h = Hyphenator(file)
      h.left = 1
    """

    def __init__(self, filename, left=2, right=2, cache=True):
        self.left = left
        self.right = right
        if cache and filename in _hdcache:
            self.patterns, self.cache = _hdcache[filename]
        else:
            self.patterns, self.cache = ({}, {})
            self._readfile(filename)
            _hdcache[filename] = (self.patterns, self.cache)

    def _readfile(self, filename):
        f = open(filename)
        charset = f.readline().strip()
        if charset.startswith('charset '):
            charset = charset[8:].strip()

        for line in f:
            if line[0] == '%': continue
            line = line.decode(charset).strip()
            # replace ^^hh with the real character
            pat = _re_hex(_hexrepl, line)
            # read nonstandard hyphen alternatives
            if '/' in pat:
                pat, alt = pat.split('/', 1)
                factory = int_alt(alt)
            else:
                factory = int
            tag, value = zip(*[(s or "", factory(i or "0"))
                for i,s in _re_parse(pat)][:-1])
            # chop zero's from beginning and end, and store start offset.
            start, end = 0, -1
            while value[start] == 0: start += 1
            while value[end] == 0:   end -= 1
            self.patterns[''.join(tag)] = start, value[start:(end+1 or None)]
        f.close()

    def hyphenate(self, word):
        """
        Returns a list of positions where the word can be hyphenated.
        E.g. for the dutch word 'lettergrepen' this method returns
        the list [3, 6, 9].
        """
        word = word.lower()
        points = self.cache.get(word)
        if not points:
            prepWord = '.%s.' % word
            res = [0] * (len(prepWord) + 1)
            for i in range(len(prepWord) - 1):
                for j in range(i, len(prepWord)):
                    p = self.patterns.get(prepWord[i:j+1])
                    if p:
                        offset, value = p
                        start, end = i + offset, i + offset + len(value)
                        res[start:end] = map(max, value, res[start:end])

            points = [i - 1 for i,r in enumerate(res) if r % 2]
            self.cache[word] = points

        # correct for left and right
        right = len(word) - self.right
        return [i for i in points if self.left <= i <= right]

    def visualise(self, word, hyphen='-'):
        """
        Returns the word as a string with al the possible hyphens inserted.
        E.g. for the dutch word 'lettergrepen' this method returns
        the string 'let-ter-gre-pen'. The hyphen string to use can be
        given as the second parameter, that defaults to '-'.

        This method can also be called as visualize().
        """
        l = list(word)
        for p in reversed(self.hyphenate(word)):
            l[p:p] = hyphen
        return u''.join(l)

    visualize = visualise

p = Hyphenator("hyph_nl.dic", left=1, right=1)
#print repr(p.patterns)

print repr(p.visualise(sys.argv[1]))

