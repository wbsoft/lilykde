\version "2.12.0"

#(set-global-staff-size 17)

\header {
  tagline = ##f
}

\layout {
  \context {
    \Staff
    \override StaffSymbol #'transparent = ##t
    \remove "Clef_engraver"
    \remove "Time_signature_engraver"
  }
  \context {
    \Voice
    \override NoteHead #'no-ledgers = ##t
    \override NoteHead #'transparent = ##t
    \override Stem #'transparent = ##t
  }
}
