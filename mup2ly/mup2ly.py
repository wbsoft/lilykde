#!/usr/bin/python

"""
This script requires Python 2.4 or newer (due to yes-no regexps and generator expressions)

Author: Wilbert Berendsen <info@wilbertberendsen.nl>

Released under the GPL
"""

import sys
import re
import os
import getopt


def warn(message):
    global warnings

    if warnings:
        sys.stderr.write("warning: %s\n" % message)




# Preprocessor code.
# works very well, TODO: really support ternairy operator in if-clauses

class Macro:
    def __init__(self, body, args=[]):
        self.body = body
        self.args = args

class Preprocessor:
    
    # commonly used regexp patterns
    pats = {
        'macro'  : r'[A-Z][A-Z0-9_]*',
        'string' : r'"(\\["\\]|.)*?"',
        'comment': r'//[^\n]*'
    }

    # regexp for the preprocessor
    scan = re.compile(
        r"(?P<comment>%(comment)s)"             # comment
        r"|(?P<text>%(string)s)"                # quoted string
        r"|\binclude\s*"                        # include file
            r'(?P<include>(\\["\\]|.)*?)'
        r"|\bdefine\s*"                         # define macro
            r"(?P<define>%(macro)s)"            # NAME
            r"(\((?P<defargs>.*?)\))?"          # args ?
            r"(?P<defbody>(\\[@\\]|[^@])*)@"    # body
        r"|\bundef\s*(?P<undef>%(macro)s)"      # undef MACRO
        r"|(?P<macrowithargs>%(macro)s)\("      # MACRO subst with args
            r"(?P<args>(\\\)|[^)])*)\)"
        r"|(?P<macro>%(macro)s)"                # MACRO subst, or local arg
        r"|`(?P<qlocalarg>%(macro)s)`"          # local arg in backticks
        r"|\bifdef\s*(?P<ifdef>%(macro)s)"      # ifdef MACRO
        r"|\bifndef\s*(?P<ifndef>%(macro)s)"    # ifndef MACRO
        r"|\bif\s*(?P<if>.*?)\bthen\b"          # general if clause
        r"|(?P<else>\belse\b)"                  # else
        r"|(?P<endif>\bendif\b)"                # endif
        "" % pats, re.S).finditer

    # regexp for general if-clause
    mup2py_sub = re.compile(
        r"%(comment)s"                      # delete comments
        r"|(?P<text>%(string)s)"            # leave quoted string alone
        r"|\bdefined\b\s*"                  # defined MACRO or (MACRO)
            r"(?P<p>\()?\s*(?P<def>%(macro)s)\s*(?(p)\))"
        r"|(?P<op>!|&&|\|\||\?|:)"          # operators
        r"|(?P<macro>%(macro)s)"            # a macro to expand (only numbers)
        "" % pats).sub

    # mup operators and their python replacements
    mup2py_table = {
        '!' : ' not ',
        '&&': ' and ',
        '||': ' or ',
        '?' : ' and ',  # hack: the ternairy operator x ? y : z is converted
        ':' : ' or '    # to x and y or z. In most cases this works.
    }


    def __init__(self, text, macros={}):

        self.macros = macros		# defined macros at the command line
        self.active = [True]		# if all are True = print, else don't
        self.output = self.preprocess(text)
        if len(self.active) > 1:
            warn('missing endif at end of file')


    def find_include_file(self, filename):
        """tries to find the include file, also searches in MUPPATH"""
        if os.path.isfile(filename):
            return filename
        elif not os.path.isabs(filename) and 'MUPPATH' in os.environ:
            for p in [os.path.join(p, filename) for p in \
                                os.environ['MUPPATH'].split(os.path.pathsep)]:
                if os.path.isfile(p):
                    return p
        else:
            warn('include file "%s" not found' % filename)


    def mup2py(self, expr):
        """converts a mup if-clause expression to a python expression"""
        return self.mup2py_sub(self._mup2py, expr)


    def _mup2py(self, matchObj):
        """the callback function for re_mup2p regexp substitution"""
        m = matchObj.group
        if m('text'):
            return m('text')
        elif m('def'):
            return ' %s ' % str(m('def') in self.macros)
        elif m('op'):
            return self.mup2py_table[m('op')]
        elif m('macro'):
            name = m('macro')
            if name in self.macros:
                return ' %s ' % self.macros[name].body.strip()
            else:
                return ' 0 '
        else:
            return ''


    def preprocess (self, text, localargs={} ):
        """Preprocess a string of Mup text, suppressing output if inside
        ifdef-constructs, etc. localargs can be a dict containing additional
        names with associated values, for the arguments of macros.
        """
        pos = 0                     # keep track of unprocessed parts
        output = []                 # output is first collected in a list

        def out(t):
            if min(self.active):
                output.append(t)    # only output if not suppressed (ifdef etc)

        for	m in self.scan(text):
            out(text[pos:m.start()])    # the part before the match
            pos = m.end()
            m = m.group

            if m('ifdef'):
                self.active.append(m('ifdef') in self.macros)

            elif m('ifndef'):
                self.active.append(m('ifndef') not in self.macros)

            elif m('if'):           # general if clause
                self.active.append(bool(eval(self.mup2py(m('if')))))

            elif m('else'):
                if len(self.active) > 1:
                    self.active[-1] = not self.active[-1]
                else:
                    warn('else encountered outside if-construct')

            elif m('endif'):
                if len(self.active) > 1:
                    self.active.pop()
                else:
                    warn('endif encountered outside if-construct')

            elif min(self.active):      # are we executing/printing?

                if m('text'):           # text string
                    out(m())

                elif m('comment'):      # comment
                    out(m())

                elif m('include'):      # include file
                    file = self.find_include_file (m('include'))
                    if file:
                        try:
                            f = open(file)
                            t = f.read()
                        finally:
                            f.close()
                        out(self.preprocess (t, localargs))

                elif m('define'):       # keyword: define
                    name = m('define')
                    if name in self.macros:
                        warn ('macro %s already exists, overwriting' % name)
                    # change \\ in \ and \@ in @ inside body
                    body = re.compile(r'\\([\\@])').sub(r'\1', m('defbody'))
                    if m('defargs'):
                        args = re.compile(r'[\s,]+').split(m('defargs').strip())
                    else:
                        args = []
                    self.macros[name] = Macro(body, args)

                elif m('undef'):        # undef MACRO
                    name = m('undef')
                    if name in self.macros:
                        del self.macros[name]
                    else:
                        warn('macro %s does not exist' % name)

                elif m('qlocalarg'):    # a local argument with quotes
                    name = m('qlocalarg')
                    if name in localargs:
                        out('"%s"' % localargs[name])
                    else:
                        warn('local argument %s does not exist' % name)

                elif m('macro'):        # a macro or local arg inside expansion
                    name = m('macro')
                    if name in localargs:
                        out(localargs[name])    # already preprocessed
                    elif name in self.macros:
                        out(self.preprocess(self.macros[name].body))
                    else:
                        warn('macro %s does not exist' % name)

                elif m('macrowithargs'):        # a macro with arguments
                    name = m('macrowithargs')
                    if name in self.macros:
                        # split at commas but mind escaped commas
                        args = re.compile(r'(?:\\.|[^,])+', re.S).findall(m('args'))
                        # change \\ in \ ; \, in , and \) in ) inside args
                        args = [re.compile(r'\\([\\,)])').sub(r'\1',x) for x in args]
                        # preprocess the args already, expanding macros, etc.
                        args = [self.preprocess(x, localargs) for x in args]
                        # create dict containing the argument names and these args
                        newlocalargs = dict(zip(self.macros[name].args, args))
                        out(self.preprocess(self.macros[name].body, newlocalargs))
                    else:
                        warn('macro %s does not exist' % name)

        out(text[pos:]) # the part after the last match
        return ''.join(output)
    # end of self.preprocess method

# end of preprocessor code







# Start of main code, set some defaults

warnings = True
preprocess_only = False
output_file = ''
macros = {}

# parse command line
(options, files) = getopt.getopt (sys.argv[1:], 'vho:qED:')

for o,a in options:
    if o == '-v':
        version()
        sys.exit(0)
    elif o == '-h':
        usage()
        sys.exit(0)
    elif o == '-q':
        warnings = False
    elif o == '-E':
        preprocess_only = True
    elif o == '-o':
        output_file = a
    elif o == '-D':
        m = a.split('=')
        m.append('')    # ensure the empty string if no body is given
        macros[m[0]] = Macro(m[1])
    else:
        usage()
        sys.exit(2)

if not files:
    files = ['-']

for filename in files:
    f = open(filename)
    text = f.read()
    f.close()

    p = Preprocessor(text, macros)

    # TODO: if only preprocess just save p.output now.

    print p.output



# kate: indent-width 4; encoding iso-8859-1;
