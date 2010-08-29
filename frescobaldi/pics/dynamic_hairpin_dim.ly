\version "2.13.21"
\include "dynamic_defaults.ily"
#(set-global-staff-size 22)
\paper {
  top-title-spacing = #'((space . 4.4))
}
\markup {
  \icon #0
  \combine
  \draw-line #'(6 . 1)
  \translate #'(0 . 2)
  \draw-line #'(6 . -1)
}
