\version "2.10.0"
\include "bar_defaults.ily"
\layout {
  \context {
    \Score
    \override StaffSymbol #'extra-offset = #'(4.8 . 0)
  }
}

{ s \bar ":|:" s }
