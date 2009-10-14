\version "2.10.0"

\paper {
  oddFooterMarkup = ##f
  evenFooterMarkup = ##f
  oddHeaderMarkup = ##f
  evenHeaderMarkup = ##f
}

\layout {
  indent = #0
  \context {
    \Staff
    \remove "Time_signature_engraver"
    \override StaffSymbol #'width = #4
  }
}
