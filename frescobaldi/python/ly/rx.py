# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008  Wilbert Berendsen
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# See http://www.gnu.org/licenses/ for more information.

""" All kinds or regular expressions dealing with the LilyPond format """

import re

step = (
    r"\b([a-h]((iss){1,2}|(ess){1,2}|(is){1,2}|(es){1,2}|"
    r"(sharp){1,2}|(flat){1,2}|ss?|ff?)?"
    r"|(do|re|mi|fa|sol|la|si)(dd?|bb?|ss?|kk?)?)"
)
named_step = "(?P<step>" + step + ")"

cautionary = r"[?!]?"
named_cautionary = "(?P<cautionary>" + cautionary + ")"

rest = r"(\b[Rrs]|\\skip)(?![A-Za-z])"
named_rest = "(?P<rest>" + rest + ")"

octave = r"('+|,+|(?![A-Za-z]))"
named_octave = "(?P<octave>" + octave + ")"

octcheck = "=[',]*"
named_octcheck = "(?P<octcheck>" + octcheck + ")"

pitch = (
    step + cautionary + octave + r"(\s*" + octcheck + r")?")
named_pitch = (
    named_step + named_cautionary + named_octave + r"(\s*" +
    named_octcheck + r")?")

duration = (
    r"(?P<duration>"
        r"(?P<dur>"
            r"\\(maxima|longa|breve)\b|"
            r"(1|2|4|8|16|32|64|128|256|512|1024|2048)(?!\d)"
        r")"
        r"(\s*(?P<dots>\.+))?"
        r"(?P<scale>(\s*\*\s*\d+(/\d+)?)*)"
    r")"
)

quotedstring = r"\"(?:\\\\|\\\"|[^\"])*\""

skip_pitches = (
    # skip \relative or \transpose pitch, etc:
    r"\\(relative|transposition)\s+" + pitch +
    r"|\\transpose\s+" + pitch + r"\s*" + pitch +
    # and skip commands
    r"|\\[A-Za-z]+"
)

# a sounding pitch/chord with duration
chord = re.compile(
    # skip this:
    r"<<|>>|" + quotedstring +
    # but catch either a pitch plus an octave
    r"|(?P<full>(?P<chord>" + named_pitch +
    # or a chord:
    r"|<(\\[A-Za-z]+|" + quotedstring + r"|[^>])*>"
    r")"
    # finally a duration?
    r"(\s*" + duration + r")?)"
    r"|" + skip_pitches
)

# a sounding pitch/chord OR rest/skip with duration
chord_rest = re.compile(
    # skip this:
    r"<<|>>|" + quotedstring +
    # but catch either a pitch plus an octave
    r"|(?P<full>(?P<chord>" + named_pitch +
    # or a chord:
    r"|<(\\[A-Za-z]+|" + quotedstring + r"|[^>])*>"
    # or a spacer or rest:
    r"|" + named_rest +
    r")"
    # finally a duration?
    r"(\s*" + duration + r")?)"
    r"|" + skip_pitches
)

finddurs = re.compile(duration)

lyric_word = re.compile(r'[^\W0-9_]+', re.U)

include_file = re.compile(r'\\include\s*"([^"]+)"')

# does not take percent signs inside quoted strings into account
all_comments = re.compile(r'%.*?\n|%\{.*?%\}')
