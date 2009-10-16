\version "2.10.0"
\include "clef_defaults.ily"
#(set-global-staff-size 11.3) 
\layout {
  \context {
    \TabStaff
    \remove "Time_signature_engraver"
    \override StaffSymbol #'width = #4
  }
}
\new TabStaff { s4 }
