
import __main__

class _MethodHelper(object):
    __slots__ = ['root', 'name']
    def __init__(self, root, name):
        self.root = root
        self.name = name
    def __call__(self, event):
        num, stc = self.root.getNumWin(event)
        if stc.recording:
            stc.macro.append((None, None, self.name))
            if __main__.PRINTMACROS: print "recorded menu item", stc.macro[-1]
        getattr(stc, self.name)(event)

class MethodHelper(object):
    __slots__ = ['root']
    def __init__(self, root):
        self.root = root
    def __getattr__(self, name):
        return _MethodHelper(self.root, name)
