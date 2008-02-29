
"""

'a3c5b' --> 'acb': '035'

beter:
    'acb': (0,3,5)
    
    
    
    
    
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
    
    def __init__(self):
        self.patterns = {}
        self.left = 1
        self.right = 1
    
    def readfile(self, filename):
        
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
        # todo: implement caching
        
        word = '.%s.' % word
        result = [0] * (len(word) + 1)
        
        for i in range(len(word)):
            for j in range(i, len(word)):
                s = word[i:j+1]
                if s in self.patterns:
                    v = self.patterns[s]
                    result[i:i+len(v)] = map(max, zip(v, result[i:i+len(v)]))
        
        points = [i - 1 for i,r in enumerate(result) if r % 2]
        # correct for left and right
        right = len(word) - self.right - 2
        return [i for i in points if i >= self.left and i <= right]

    def visualise(self, word, hyphen='-'):
        l = list(word)
        for p in sorted(self.hyphenate(word), reverse=True):
            l[p:p] = hyphen
        return u''.join(l)

p = Hyphenator()
p.readfile("hyph_nl.dic")
#print repr(p.patterns)

print repr(p.visualise(sys.argv[1]))

