\version "2.10.0"

\paper {
  indent = 3\mm
  line-width = 3.2\in
  oddFooterMarkup = ##f
  oddHeaderMarkup = ##f
  bookTitleMarkup = ##f
  scoreTitleMarkup = ##f
}

\layout {
  \context {
    \Score
    \remove "Bar_number_engraver"
  }
}

\header {
  tagline = ##f
}

\score {
  \new PianoStaff <<
    \new Staff \relative c' { c2 d4 e f g a b c1 \bar"|."}
    \new Staff \relative c' { \clef F c2 b4 a g f e d c1 }
  >>
}
