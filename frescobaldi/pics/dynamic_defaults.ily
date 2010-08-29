\version "2.13.21"

\paper {
  paper-height = 0.5\in
  paper-width = 0.5\in
  top-margin = 0
  bottom-margin = 0
  left-margin = 0
  right-margin = 0
  oddFooterMarkup = ##f
  oddHeaderMarkup = ##f
  top-title-spacing = #'((space . 4.5))
}

#(define-markup-command
  (icon layout props size text)
  (number? markup?)
  (interpret-markup layout props
    (markup
      #:override (cons 'word-space 0)
		 (#:fill-line
		   (#:fontsize size text)))))

#(define size1 6)
#(define size2 3.5)
#(define size3 -0.5)


