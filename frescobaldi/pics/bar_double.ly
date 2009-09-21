\version "2.10.0"
\include "bar_defaults.ily"
\layout {
  \context {
    \Score
    \override StaffSymbol #'extra-offset = #'(3.4 . 0)
  }
}

{ s \bar "||" s }
