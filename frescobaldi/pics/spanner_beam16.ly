\version "2.12.0"

#(set-global-staff-size 14)

\header {
  tagline = ##f
}

\relative c' {
  f16[ g]
}

\layout {
  \context {
    \Staff
    \override StaffSymbol #'transparent = ##t
    \override Clef #'transparent = ##t
    \override TimeSignature #'transparent = ##t
  }
}
