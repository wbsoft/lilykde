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


class Hyphenator(object):

    _comments_re    = re.compile(r'%.*$')
    _hex_re         = re.compile(r'\^{2}([0-9a-f]{2})')
    _zero_start_re  = re.compile(r'^(?=\D)')
    _zero_insert_re = re.compile(r'(\D)(?=\D)')

    def _hexrepl(self, matchObj):
        return unichr(int(matchObj.group(1), 16))

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
            line = line.decode(charset)

            # remove comments and whitespace
            line = self._comments_re.sub('', line.strip())

            # replace ^^hh with the real character
            line = self._hex_re.sub(self._hexrepl, line)

            for pat in re.split(r'\s+', line):
                pat = self._zero_insert_re.sub(r'\g<1>0', pat)
                pat = self._zero_start_re.sub('0', pat)
                tag   = pat[1::2]
                value = tuple(map(int, pat[0::2]))
                self.patterns[tag] = value
        f.close()

    def hyphenate(self, word):
        word = word.lower()
        if word in self.cache:
            points = self.cache[word]
        else:
            prepWord = '.%s.' % word
            result = [0] * (len(prepWord) + 1)
            for i in range(len(prepWord)):
                for j in range(i, len(prepWord)):
                    s = prepWord[i:j+1]
                    if s in self.patterns:
                        v = self.patterns[s]
                        result[i:i+len(v)] = map(max, zip(v, result[i:i+len(v)]))

            points = [i - 1 for i,r in enumerate(result) if r % 2]
            self.cache[word] = points

        # correct for left and right
        right = len(word) - self.right
        return [i for i in points if self.left <= i <= right]

    def visualise(self, word, hyphen='-'):
        l = list(word)
        for p in sorted(self.hyphenate(word), reverse=True):
            l[p:p] = hyphen
        return u''.join(l)

p = Hyphenator("hyph_nl.dic", left=1, right=1)
#print repr(p.patterns)

print repr(p.visualise(sys.argv[1]))

