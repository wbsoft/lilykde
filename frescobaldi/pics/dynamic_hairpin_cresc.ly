\version "2.12.0"
\include "dynamic_defaults.ily"
#(set-global-staff-size 10)
\markup {
  \combine
  \draw-line #'(6 . 1)
  \draw-line #'(6 . -1)
}
