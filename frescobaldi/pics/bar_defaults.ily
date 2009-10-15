\header { tagline = ##f }
#(set-global-staff-size 14.2857)

\layout {
  indent = #0
  \context {
    \Score
    \override StaffSymbol #'width = #'4
    \override StaffSymbol #'extra-offset = #'(3.3 . 0)
  }
  \context {
    \Staff
    \remove "Clef_engraver"
    \remove "Time_signature_engraver"
  }
}
