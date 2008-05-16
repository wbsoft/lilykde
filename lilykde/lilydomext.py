"""
LilyDOM extensions for LilyKDE

"""

from lilydom import *



class EDocument(Document):
    """
    Extends lilydom.Document with many methods to quickly
    instantiate all kinds of LilyDOM objects.
    """

    def make(self, arg):
        """
        Inteprete python arg and return a suitable Node object.
        """
        if isinstance(arg, Node):
            return arg
        if isinstance(arg, basestring):
            if len(arg) > 1 and arg.startswith('"') and arg.endswith('"'):
                return QuotedString(self, arg[1:-1])
            elif arg.startswith('#'):
                return Scheme(self, arg[1:])
            else:
                return Text(self, arg)
        if isinstance(arg, (int, long)):
            return Text(self, str(arg))

    def appendArgs(self, obj, args, kwargs):
        """
        Try to interpret all args and append suitable Node objects
        for them to the obj.
        """
        for a in args:
            obj.append(self.make(a))
        if 'multiline' in kwargs:
            obj.multiline = kwargs['multiline']
        return obj

    # helper methods to quickly instantiate certain Node objects:
    def _smarkup(self, command, *args, **kwargs):
        r"""
        Evaluate all the args and create a simple markup command
        like \italic, etc. enclosing the arguments.
        """
        return self.appendArgs(MarkupEncl(self, command), args, kwargs)

    def smarkup(f):
        """
        Decorator that returns a simple markup-creating function, containing
        a call to _smarkup with a command argument based on the function name.
        """
        def _smarkup_func(self, *args, **kwargs):
            return self._smarkup(f.func_name.replace('_', '-'), *args, **kwargs)
        _smarkup_func.__doc__ = f.__doc__
        return _smarkup_func


    # create a Markup object. (\markup { } )
    def markup(self, *args, **kwargs):
        return self.appendArgs(Markup(self), args, kwargs)


    # Markup types:
    #arrow-head axis (integer) direction (direction) filled (boolean)
    #  Produce an arrow head in specified direction and axis.
    #  Use the filled head if filled is specified.

    #beam width (number) slope (number) thickness (number)
    #  Create a beam with the specified parameters.

    @smarkup
    def bigger():
        "Increase the font size relative to current setting."
        pass

    @smarkup
    def bold():
        "Switch to bold font-series."
        pass

    @smarkup
    def box():
        "Draw a box round arg."
        pass

    @smarkup
    def bracket():
        "Draw vertical brackets around arg"
        pass

    @smarkup
    def caps():
        "Emit arg as small caps."
        pass

    @smarkup
    def center_align():
        "Put args in a centered column."
        pass

    #char num
    #Produce a single character. For example, \char #65 produces the letter A.

    @smarkup
    def circle():
        "Draw a circle around arg."
        pass

    @smarkup
    def column():
        "Stack the markups in args vertically."
        pass

    #combine m1 (markup) m2 (markup)

    @smarkup
    def concat():
        "Concatenate args in a horizontal line, without spaces inbetween."
        pass


    #...

