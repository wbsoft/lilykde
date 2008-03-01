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


# precompile some stuff
_re_hex = re.compile(r'\^{2}([0-9a-f]{2})').sub
_re_parse = re.compile(r'(\d?)(\D?)').findall

def _hexrepl(matchObj):
    return unichr(int(matchObj.group(1), 16))


class Hyphenator(object):

    def __init__(self, files, left=2, right=2):
        self.left = left
        self.right = right
        self.patterns = {}
        self.cache = {}
        if type(files) not in (tuple, list):
            files = (files,)
        for f in files: self._readfile(f)

    def _readfile(self, filename):
        f = open(filename)
        charset = f.readline().strip()
        if charset.startswith('charset '):
            charset = charset[7:].strip()

        for line in f:
            if line[0] == '%': continue
            # replace ^^hh with the real character
            pat = _re_hex(_hexrepl, line.decode(charset).strip())

            tag, value = zip(*[(s or "", int(i or "0"))
                for i,s in _re_parse(pat)][:-1])
            self.patterns[''.join(tag)] = value
        f.close()

    def hyphenate(self, word):
        word = word.lower()
        if word in self.cache:
            points = self.cache[word]
        else:
            prepWord = '.%s.' % word
            res = [0] * (len(prepWord) + 1)
            for i in range(len(prepWord)):
                for j in range(i, len(prepWord)):
                    s = prepWord[i:j+1]
                    if s in self.patterns:
                        v = self.patterns[s]
                        res[i:i+len(v)] = map(max, zip(v, res[i:i+len(v)]))

            points = [i - 1 for i,r in enumerate(res) if r % 2]
            self.cache[word] = points

        # correct for left and right
        right = len(word) - self.right
        return [i for i in points if self.left <= i <= right]

    def visualise(self, word, hyphen='-'):
        l = list(word)
        for p in reversed(self.hyphenate(word)):
            l[p:p] = hyphen
        return u''.join(l)

    visualize = visualise

p = Hyphenator("hyph_nl.dic", left=1, right=1)
#print repr(p.patterns)

print repr(p.visualise(sys.argv[1]))

