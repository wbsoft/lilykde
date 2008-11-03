/** kate-script
 * name: LilyPond
 * license: LGPL
 * author: Wilbert Berendsen <info@wilbertberendsen.nl>
 * version: 1
 * kate-version: 3.0
 * type: indentation
 * required-syntax-style: lilypond
 * indent-languages: lilypond
 */

var triggerCharacters = "}>%;";

function dbg(s) {
  // debug to the term in blue so that it's easier to make out amongst all
  // of Kate's other debug output.
  debug("\u001B[34m" + s + "\u001B[0m");
}

reOpener = /\{|\<\</g;
reCloser = /\}|\>\>/g;
reStartClosers = /^(\s*([%#]?\}|\>\>))+/
reSpaceLine = /^\s*$|^;;;|^%%%/;
reFullCommentLine = /^\s*(;;;|%%%)/;
reRemove = /"[^"]*"|%\{.*%\}|%(?![{}]).*$/;

function indent(line, indentWidth, ch)
{
  // not necessary to indent the first line
  if (line == 0)
    return -2;

  var c = document.line(line); // current line

  // return 0 for triple commented lines
  if (c.match(reFullCommentLine))
    return 0;

  // search backwards for first non-space line.
  var prev = line;
  while (prev--) {
    if (!document.line(prev).match(reSpaceLine)) {
      // remove text between double quotes
      var p = document.line(prev); // previous non-space line
      var prevIndent = document.firstVirtualColumn(prev);
      // count the number of openers and closers in the previous line,
      // discarding first closers.
      if (m = p.match(reStartClosers))
	var pos = m[0].length;
      else
	var pos = 0;
      var end = document.lineLength(prev);

      // the amount of normal lilypond openers { <<  and closers } >>
      var delta = 0;

      // the number of opened Scheme parentheses and the position of their
      // first occurence.
      var level = 0;
      var paren = new Array();

      while (pos < end) {
	// walk over openers and closers in the remainder of the previous line.
	var one = document.charAt(prev, pos);
	var two = one + (pos+1 < end ? document.charAt(prev, pos+1) : "");
	if (two == "%{") {
	  ++delta;
	  ++pos;
	}
	else if (two == "%}") {
	  --delta;
	  ++pos;
	}
	else if (!document.isString(prev, pos)) {
	  if (one == "%" || one == ";")
	    break; // discard rest of line
	  else if (two == "#{" || two == "<<") {
	    ++delta;
	    ++pos;
	  }
	  else if (two == "#}" || two == ">>") {
	    --delta;
	    ++pos;
	  }
	  else if (one == "{")
	    ++delta;
	  else if (one == "}")
	    --delta;
	  else if (one == "(") {
	    ++delta;
	    dbg("Opening paren, level="+level);
	    // save position of first
	    if (level >= 0 && paren[level] == null)
	      paren[level] = pos;
	    ++level;
	  }
	  else if (one == ")") {
	    --level;
	    --delta;
	    // have we seen an opening parenthesis in this line?
	    if (paren[level] != null) {
	      delta = 0;
	      prevIndent = document.toVirtualColumn(prev, paren[level]);
	    }
	    else {
	      var cur = document.anchor(prev, 0, "(");
	      if (cur) {
		delta = 0;
		// is this the final closing paren of a Scheme expression?
		if (document.attribute(prev, pos) == 26)
		  prevIndent = document.firstVirtualColumn(cur.line);
		else
		  prevIndent = document.toVirtualColumn(cur.line, cur.column);
	      }
	    }
	  }
	}
	++pos;
      }
      // now count the number of closers in the beginning of the current line.
      if (m = c.match(reStartClosers))
	delta -= m[0].match(reCloser).length;
      return Math.max(0, prevIndent + delta * indentWidth);
    }
  }
  return 0;
}
