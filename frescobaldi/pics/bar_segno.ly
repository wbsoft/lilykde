\version "2.13.19"
\include "bar_defaults.ily"

#(set-global-staff-size (* 20 (/ 11 28)))

{ 
  s
  \once \override Staff.BarLine #'extra-offset = #'(-1 . 0)
  \bar "S"
  s
}
