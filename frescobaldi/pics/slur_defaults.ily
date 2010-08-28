\version "2.12.0"

#(set-global-staff-size 23)

\paper {
  oddFooterMarkup = ##f
  evenFooterMarkup = ##f
  oddHeaderMarkup = ##f
  evenHeaderMarkup = ##f
}

\layout {
  \context {
    \Staff
    \override StaffSymbol #'transparent = ##t
    \override Clef #'transparent = ##t
    \override TimeSignature #'transparent = ##t
  }
  \context {
    \Voice
    \override NoteHead #'transparent = ##t
    \override Stem #'transparent = ##t
  }
}
