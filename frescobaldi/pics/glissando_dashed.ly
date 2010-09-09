\version "2.12.0"

\include "glissando_defaults.ily"

\relative c' {
  \override Glissando #'style = #'dashed-line
  d2\glissando f'
}
