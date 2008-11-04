# This file is part of LilyKDE, http://lilykde.googlecode.com/
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

"""
All information related to LilyPond interfaces and layout objects.
"""

class prop(object):
    """Base class for LilyPond properties."""
    pass

# types:
class number(prop):
    pass

class symbol(prop):
    pass

class boolean(prop):
    pass

class dimension(prop):
    """distance, in staff spaces"""
    pass

class direction(prop):
    pass

class string(prop):
    pass

class markup(prop):
    pass

class slist(prop):
    """a scheme list, named so to not collide with python list"""
    pass

class alist(prop):
    pass

class pair(prop):
    pass

class pairnum(pair):
    pass

class unknown(prop):
    pass



class align_dir(direction):
    __doc__ = _("Which side to align? "
        "-1: left side, 0: around center of width, 1: right side.")


class allow_span_bar(boolean):
    __doc__ = _("If false, no inter-staff bar line will be created below "
        "this bar line.")


class alteration(number):
    __doc__ = _("Alteration numbers for accidental. "
        "A direct number or a function that returns a value.")


class annotation(string):
    __doc__ = _("Annotate a grob for debug purposes.")


class arpeggio_direction(direction):
    __doc__ = _("If set, put an arrow on the arpeggio squiggly line.")


class auto_knee_gap(dimension):
    __doc__ = _("If a gap is found between note heads where a horizontal beam "
        "fits that is larger than this number, make a kneed beam.")


class avoid_slur(symbol):
    __doc__ = _("How to handle slur collisions.")
    choices = (
        ('around', _("Only move the script if there is a collision "
                "between the object and a slur.")),
        ('inside', _("Try to keep the object inside a slur.")),
        ('outside', _("Always move the object outside a slur.")),
    )


class axes(slist):
    __doc__ = _("List of axis numbers. In the case of alignment grobs, "
        "this should contain only one number.")


class bar_size(dimension):
    __doc__ = _("The size of a bar line.")


class beamed_stem_shorten(slist):
    __doc__ = _("How much to shorten beamed stems, when their direction is "
        "forced. It is a list, since the value is different depending on the "
        "number of flags and beams.")


class beaming(pair):
    __doc__ = _("Pair of number lists. Each number list specifies which beams "
        "to make. 0 is the central beam, 1 is the next beam toward the note, "
        "etc. This information is used to determine how to connect the beaming "
        "patterns from stem to stem inside a beam.")


class break_overshoot(pairnum):
    __doc__ = _("How much does a broken spanner stick out of its bounds?")


class clip_edges(boolean):
    __doc__ = _("Allow outward pointing beamlets at the edges of beams?")


class concaveness(number):
    __doc__ = _("A beam is concave if its inner stems are closer to the beam "
        "than the two outside stems. This number is a measure of the closeness "
        "of the inner stems. It is used for damping the slope of the beam.")


class damping(number):
    __doc__ = _("Amount of beam slope damping.")


class forced(boolean):
    __doc__ = _("Is this a manually forced accidental.")


class gap(dimension):
    __doc__ = _("Size of a gap in a variable symbol.")


class gap_count(integer):
    __doc__ = _("Number of gapped beams for tremolo.")


class glyph(string):
    __doc__ = _("A string determining what 'style' of glyph is typeset. "
        "Valid choices depend on the function that is reading this property.")


class glyph_name_alist(alist):
    __doc__ = _("An alist of key-string pairs, determining which glyph to "
        "use for which alteration value.")


class grow_direction(direction):
    __doc__ = _("Crescendo or decrescendo, or open/close feathering beams.")


class hair_thickness(number):
    __doc__ = _("Thickness of the thin line in a bar line.")


class implicit(boolean):
    __doc__ = _("Is this an implicit bass figure?")


class inspect_quants(pairnum):
    __doc__ = _("If debugging is set, set beam and slur quants to this "
        "position, and print the respective scores.")


class keep_fixed_while_stretching(boolean):
    __doc__ = _("A grob with this property set to true is fixed relative "
        "to the staff above it when systems are stretched.")


class kern(dimension):
    __doc__ = _("Amount of extra white space to add. For bar lines, this is "
        "the amount of space after a thick line.")


class knee(boolean):
    __doc__ = _("Is this beam kneed?")


class left_padding(dimension):
    __doc__ = _("The amount of space that is put left to an object "
        "(e.g., a group of accidentals).")


class length_fraction(number):
    __doc__ = _("Multiplier for lengths. Used for determining ledger "
        "lines and stem lengths.")


class max_stretch(number):
    __doc__ = _("The maximum amount that this VerticalAxisGroup can be "
        "vertically stretched (for example, in order to better fill a page).")


class neutral_direction(direction):
    __doc__ = _("Which direction to take in the center of the staff.")


class no_alignment(boolean):
    __doc__ = _("If set, don’t place this grob in a VerticalAlignment; "
        "rather, place it using its own Y-offset callback.")


class padding(dimension):
    __doc__ = _("Add this much extra space between objects that "
        "are next to each other.")


class parenthesized(boolean):
    __doc__ = _("Parenthesize this object.")


class positions(pairnum):
    __doc__ = _("Pair of staff coordinates (left . right), "
        "where both left and right are in staff-space units of the "
        "current staff. For slurs, this value selects which slur candidate "
        "to use; if extreme positions are requested, the closest one is taken.")


class restore_first(boolean):
    __doc__ = _("Print a natural before the accidental.")


class right_padding(dimension):
    __doc__ = _("Space to insert on the right side of an object "
        "(e.g., between note and its accidentals).")


class script_priority(number):
    __doc__ = _("A sorting key that determines in what order a script "
        "is within a stack of scripts.")


class stacking_dir(direction):
    __doc__ = _("Stack objects in which direction?")


class text(markup):
    __doc__ = _("Text markup.")


class thickness(number):
    __doc__ = _("Line thickness, generally measured in line-thickness.")


class thick_thickness(number):
    __doc__ = _("Bar line thickness, measured in line-thickness.")


class thin_kern(number):
    __doc__ = _("The space after a hair-line in a bar line.")


class threshold(pairnum):
    __doc__ = _("(min . max), where min and max are dimensions in staff space.")


class vertical_skylines(unknown):
    __doc__ = _("Two skylines, one above and one below this grob.")



# Interfaces
interfaces = {
    'accidental': (
        alteration,
        avoid_slur,
        forced,
        glyph_name_alist,
        parenthesized,
        restore_first,
    ),

    'accidental-placement': (
        left_padding,
        padding,
        right_padding,
        script_priority,
    ),

    'accidental-suggestion': (
    ),

    'align': (
        align_dir,
        axes,
        padding,
        stacking_dir,
        threshold,
    ),

    'ambitus': (
        thickness,
    ),

    'arpeggio': (
        arpeggio_direction,
        positions,
        script_priority,
    ),

    'axis-group': (
        axes,
        keep_fixed_while_stretching,
        max_stretch,
        no_alignment,
        vertical_skylines,
    ),

    'balloon': (
        padding,
        text,
    ),

    'barline': (
        allow_span_bar,
        bar_size,
        gap,
        glyph,
        hair_thickness,
        kern,
        thick_thickness,
        thin_kern,
    ),

    'bass-figure-alignment': (
    ),

    'bass-figure': (
        implicit,
    ),

    'beam': (
        annotation,
        auto_knee_gap,
        beamed_stem_shorten,
        beaming,
        break_overshoot,
        clip_edges,
        concaveness,
        damping,
        direction,
        gap_count,
        grow_direction,
        inspect_quants,
        knee,
        length_fraction,
        neutral_direction,
        positions,
        thickness,
    ),



}
