# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009  Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

import re
from rational import Rational

# pitches
class pitchwriter(object):
    def __init__(self, names, accs, replacements=()):
        self.names = names
        self.accs = accs
        self.replacements = replacements

    def __call__(self, note, alter = 0, warn = False):
        """
        Returns a string representing the pitch in our language.
        If warn == True and the requested pitch has an alteration not present
        in the current language, False is returned.
        """
        pitch = self.names[note]
        if alter:
            acc = self.accs[int(alter * 4 + 4)]
            # warn if a quarter tone is requested but not present in the
            # current language.
            if warn and acc == '':
                return False
            pitch += acc
        for s, r in self.replacements:
            if pitch.startswith(s):
                pitch = r + pitch[len(s):]
                break
        return pitch


class pitchreader(object):
    def __init__(self, names, accs, replacements=()):
        self.names = list(names)
        self.accs = list(accs)
        self.replacements = replacements
        
        rx = "(%s)" % "|".join(names)
        rx += "(%s)?$" % "|".join(acc for acc in accs if acc)
        self.rx = re.compile(rx)

    def __call__(self, text):
        for s, r in self.replacements:
            if text.startswith(r):
                text = s + text[len(r):]
        for dummy in 1, 2:
            m = self.rx.match(text)
            if m:
                note = self.names.index(m.group(1))
                if m.group(2):
                    alter = Rational(self.accs.index(m.group(2)) - 4, 4)
                else:
                    alter = 0
                return note, alter
            # HACK: were we using (rarely used) long english syntax?
            text = text.replace('flat', 'f').replace('sharp', 's')
        return False
            
            
pitchInfo = {
    'nederlands': (
        ('c','d','e','f','g','a','b'),
        ('eses', 'eseh', 'es', 'eh', '', 'ih','is','isih','isis'),
        (('ees', 'es'), ('aes', 'as'))
    ),
    'english': (
        ('c','d','e','f','g','a','b'),
        ('ff', 'tqf', 'f', 'qf', '', 'qs', 's', 'tqs', 'ss'),
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
    'portugues': (
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


pitchWriter = dict(
    (lang, pitchwriter(*data)) for lang, data in pitchInfo.iteritems())

pitchReader = dict(
    (lang, pitchreader(*data)) for lang, data in pitchInfo.iteritems())
    

class Pitch(object):
    """
    A pitch with note, alter and octave.
    """
    def __init__(self):
        self.octave = 0
        self.note = 0
        self.alter = 0
        

class Transposer(object):
    """
    Transpose pitches.
    
    Instantiate with a from- and to-Pitch, and optionally a scale.
    The scale is a list with the pitch height of the unaltered step (0 .. 6).
    The default scale is the normal scale: C, D, E, F, G, A, B.
    """
    scale = (0, 1, 2, Rational(5, 2), Rational(7, 2), Rational(9, 2), Rational(11, 2))
        
    def __init__(self, fromPitch, toPitch, scale = None):
        if scale is not None:
            self.scale = scale
        
        # the number of octaves we need to transpose
        self.octave = toPitch.octave - fromPitch.octave
        
        # the number of base note steps (c->d == 1, e->f == 1, etc.)
        self.steps = toPitch.note - fromPitch.note
        
        # the number (fraction) of real whole steps
        self.alter = (self.scale[toPitch.note] + toPitch.alter -
                      self.scale[fromPitch.note] - fromPitch.alter)
                  
    def transpose(self, pitch):
        doct, note = divmod(pitch.note + self.steps, 7)
        pitch.alter += self.alter - doct * 6 - self.scale[note] + self.scale[pitch.note]
        pitch.octave += self.octave + doct
        pitch.note = note


    