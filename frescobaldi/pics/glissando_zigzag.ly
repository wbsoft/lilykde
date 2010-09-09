\version "2.12.0"

\include "glissando_defaults.ily"

\relative c' {
  \override Glissando #'style = #'zigzag
  d2\glissando f'
}
