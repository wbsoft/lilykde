\version "2.12.0"

\include "glissando_defaults.ily"

\relative c' {
  \override Glissando #'thickness = #1.5
  \override Glissando #'style = #'dotted-line
  d2\glissando f'
}
