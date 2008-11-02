/** kate-script
 * name: LilyPond
 * license: LGPL
 * author: Wilbert Berendsen <info@wilbertberendsen.nl>
 * version: 1
 * kate-version: 3.0
 * type: indentation
 */

var triggerCharacters = "}>";

reOpener = /\{|\<\</g;
reCloser = /\}|\>\>/g;
reStartClosers = /^(\s*(%?\}|\>\>))+/
reSpaceLine = /^\s*$/;
reRemove = /"[^"]*"|%\{.*%\}|%(?![{}]).*$/;

function indent(line, indentWidth, ch)
{
  // not necessary to indent the first line
  if (line == 0)
    return -2;

  // search backwards for first non-space line.
  var prev = line;
  while ((prev -= 1) >= 0) {
    if (!document.line(prev).match(reSpaceLine)) {
      // remove text between double quotes
      var c = document.line(line); // current line
      var p = document.line(prev); // previous non-space line
      var oldIndent = document.firstVirtualColumn(prev);
      // count the number of openers and closers in the previous line,
      // discarding first closers, strings and comments.
      p = p.replace(reStartClosers, '').replace(reRemove, '');
      var delta = p.match(reOpener).length - p.match(reCloser).length;
      // now count the number of closers in the beginning of the current line.
      if (m = c.match(reStartClosers))
	delta -= m[0].match(reCloser).length;
      return Math.max(0, oldIndent + delta * indentWidth);
    }
  }
  return 0;
}
