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

__all__ = ("Hyphenator")

# cache of per-file Hyph_dict objects
hdcache = {}

# precompile some stuff
parse_hex = re.compile(r'\^{2}([0-9a-f]{2})').sub
parse = re.compile(r'(\d?)(\D?)').findall

def hexrepl(matchObj):
    return unichr(int(matchObj.group(1), 16))


class parse_alt(object):
    """
    Parse nonstandard hyphen pattern alternative.
    The instance returns a special int with data about the current position
    in the pattern when called with an odd value.
    """
    def __init__(self, pat, alt):
        alt = alt.split(',')
        self.change = alt[0]
        if len(alt) > 2:
            self.index = int(alt[1])
            self.cut = int(alt[2]) + 1
        else:
            self.index = 0
            self.cut = len(re.sub(r'[\d\.]', '', pat)) + 1
        if pat.startswith('.'):
            self.index += 1

    def __call__(self, val):
        self.index -= 1
        val = int(val)
        if val & 1:
            return dint(val, (self.change, self.index, self.cut))
        else:
            return val


class dint(int):
    """
    Just an int some other data can be stuck to in a data attribute.
    call with ref=other to use the data from the other dint.
    """
    def __new__(cls, value, data=None, ref=None):
        obj = int.__new__(cls, value)
        if ref and type(ref) == dint:
            obj.data = ref.data
        else:
            obj.data = data
        return obj


class Hyph_dict(object):
    """
    Reads a hyph_*.dic file and stores the hyphenation patterns.
    Parameters:
    -filename : filename of hyph_*.dic to read
    """
    def __init__(self, filename):
        self.patterns = {}
        f = open(filename)
        charset = f.readline().strip()
        if charset.startswith('charset '):
            charset = charset[8:].strip()

        for pat in f:
            if pat[0] == '%': continue
            pat = pat.decode(charset).strip()
            # replace ^^hh with the real character
            pat = parse_hex(hexrepl, pat)
            # read nonstandard hyphen alternatives
            if '/' in pat:
                pat, alt = pat.split('/', 1)
                factory = parse_alt(pat, alt)
            else:
                factory = int
            tag, value = zip(*[(s, factory(i or "0")) for i, s in parse(pat)])
            # chop zeros from beginning and end, and store start offset.
            start, end = 0, len(value)
            while not value[start]: start += 1
            while not value[end-1]: end -= 1
            self.patterns[''.join(tag)] = start, value[start:end]
        f.close()


class Hyphenator(object):
    """
    Reads a hyph_*.dic file and stores the hyphenation patterns.
    Provides methods to hyphenate strings in various ways.
    Parameters:
    -filename : filename of hyph_*.dic to read
    -left: make the first syllabe not shorter than this
    -right: make the last syllabe not shorter than this
    -cache: if true (default), use a cached copy of the dic file, if possible

    left and right may also later be changed:
      h = Hyphenator(file)
      h.left = 1
    """
    def __init__(self, filename, left=2, right=2, cache=True):
        self.left  = left
        self.right = right
        if cache and filename in hdcache:
            self.hd = hdcache[filename]
        else:
            self.hd = Hyph_dict(filename)
            self.hd.cache = {}
            hdcache[filename] = self.hd

    def hyphenate(self, word):
        """
        Returns a list of positions where the word can be hyphenated.
        E.g. for the dutch word 'lettergrepen' this method returns
        the list [3, 6, 9].

        Each position is a 'data int' (dint) with a data attribute.
        If the data attribute is not None, it contains a tuple with
        information about nonstandard hyphenation at that point:
        (change, index, cut)

        change: is a string like 'ff=f', that describes how hyphenation
            should take place.
        index: where to substitute the change, counting from the current
            point
        cut: how many characters to remove while substituting the nonstandard
            hyphenation
        """
        word = word.lower()
        points = self.hd.cache.get(word)
        if not points:
            prepWord = '.%s.' % word
            res = [0] * (len(prepWord) + 1)
            for i in range(len(prepWord) - 1):
                for j in range(i, len(prepWord)):
                    p = self.hd.patterns.get(prepWord[i:j+1])
                    if p:
                        offset, value = p
                        s = slice(i + offset, i + offset + len(value))
                        res[s] = map(max, value, res[s])

            points = [dint(i - 1, ref=r) for i,r in enumerate(res) if r % 2]
            self.hd.cache[word] = points

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
            if p.data:
                # get the nonstandard hyphenation data
                change, index, cut = p.data
                if word.isupper():
                    change = change.upper()
                l[p + index: p + index + cut] = change.replace('=', hyphen)
            else:
                l.insert(p, hyphen)
        return u''.join(l)

    visualize = visualise


p = Hyphenator("hyph_nl.dic", left=1, right=1)
#print repr(p.patterns)

print (p.visualise(unicode(sys.argv[1].decode('iso-8859-1'))))

