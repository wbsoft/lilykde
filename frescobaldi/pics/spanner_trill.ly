\version "2.12.0"

#(set-global-staff-size 15)

\header {
  tagline = ##f
}

\markup {
  \concat {
    \musicglyph #"scripts.trill"
    \translate #'(0.5 . 0.6)
    \concat {
      \musicglyph #"scripts.trill_element"
      \musicglyph #"scripts.trill_element"
    }
  }
}

