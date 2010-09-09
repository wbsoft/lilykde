\version "2.12.0"

\paper {
  line-width = 18\mm
  ragged-right = ##f
}

\header {
  tagline = ##f
}

\layout {
  indent = #0
  \context {
    \Staff
    \remove "Clef_engraver"
    \remove "Time_signature_engraver"
    \remove "Staff_symbol_engraver"
  }
  \context {
    \Voice
    \override NoteHead #'transparent = ##t
    \override Stem #'transparent = ##t
  }
}
