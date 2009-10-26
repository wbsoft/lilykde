\version "2.10.0"

#(set-global-staff-size (* 20 (/ 4 7)))

\paper {
  ragged-right = ##t
}

\header {
  tagline = ##f
}

music = {
  s1
}

\layout {
  indent = #0
  \context {
    \Score
    \remove "Bar_number_engraver"
    defaultBarType = #""
  }
  \context {
    \Staff
    \remove "Time_signature_engraver"
    \remove "Clef_engraver"
    \override StaffSymbol #'line-count = #4
    \override VerticalAxisGroup #'minimum-Y-extent = #'(-3 . 3)
  }
}
