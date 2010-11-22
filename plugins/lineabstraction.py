import sys

KE = "%s does not support %s"
KE2 = "%s does not support strides != 1, your stride was %s"
TE = "%s requires lines that subclass from basestring not %s"

def Property(name, bases, dict):
    get = dict.get('get', None)
    set = dict.get('set', None)
    de1 = dict.get('de1', None) #that's a numeral 1
    doc = dict.get('__doc__', None)
    return property(get, set, de1, doc)

class LineAbstraction(object):
    if 1:
        '''
        A 0-indexed line abstraction that supports manipulation of the
        provided document.
        '''
    
    def __init__(self, stc):
        self.stc = stc
    
    class curline:
        if 1:
            '''
            Manipulates the current line.
            '''
        __metaclass__ = Property
        def get(self):
            return self[self.curlinei]
        def set(self, value):
            self[self.curlinei] = value
        def de1(self):
            del self[self.curlinei]
    
    class curlinei:
        if 1:
            '''
            Manipulates the current line's index.
            '''
        __metaclass__ = Property
        def get(self):
            x = self.stc.GetCurrentPos()
            return self.stc.LineFromPosition(x)
        def set(self, index):
            x,y = self._line_range(index)
            self.stc.SetSelection(x,x)
    
    class curlinep:
        if 1:
            '''
            Manipulates the cursor position in the current line.
            '''
        __metaclass__ = Property
        def get(self):
            x = self.stc.GetCurrentPos()
            y = self.stc.LineFromPosition(x)
            y = self.stc.PositionFromLine(y)
            curline = self.curline
            if type(curline) is not unicode:
                return x-y
            #the stc gives offsets related to character positions in utf-8
            #encoded text
            return len(curline.encode('utf-8')[:x-y].decode('utf-8'))
        def set(self, posn):
            x = self.stc.GetCurrentPos()
            y = self.stc.LineFromPosition(x)
            y = self.stc.PositionFromLine(y)
            curline = self.curline
            if posn < 0:
                posn %= len(curline)
            if posn > len(curline):
                posn = len(curline)
            #need to convert to utf-8 encoded offsets on unicode platforms
            if type(curline) is unicode:
                posn = len(curline[:posn].encode('utf-8'))
            self.stc.SetSelection(y+posn, y+posn)
    
    class selectedlines:
        if 1:
            '''
            Manipulates the currently selected lines.
            Setting requires a sequence of lines, CR and LF endings are
            pre-rstripped from the input lines, inserted one between each line
            during setting.
            '''
        __metaclass__ = Property
        def get(self):
            return [self[i] for i in xrange(*self.selectedlinesi)]
        
        def set(self, value):
            self.selectedlinesi = self.selectedlinesi
            p = self.stc.GetSelection()[0]
            self.stc.ReplaceSelection(self.stc.format.join([i.rstrip('\r\n') for i in value] + ['']))
            self.stc.SetSelection(p, self.stc.GetSelection()[1])
        
        def de1(self):
            self.selectedlinesi = self.selectedlinesi
            self.stc.ReplaceSelection('')
    
    class selectedlinesi:
        if 1:
            '''
            Manipulates the indices of the currently selected lines.
            '''
        __metaclass__ = Property
        def get(self):
            x,y = self.stc.GetSelection()
            start = self._line_range(self.stc.LineFromPosition(x))[0]
            end = self._line_range(self.stc.LineFromPosition(y))[1]
            return self.stc.LineFromPosition(start), self.stc.LineFromPosition(max(end-1, start))+1
        
        def set(self, range):
            try:
                start, end = range
            except:
                raise ValueError, "selected line range must be a sequence of integers of length 2"
            if end < start:
                start, end = end, start
            start = self._line_range(start)[0]
            end = self._line_range(end)[0]
            self.stc.SetSelection(start, end)
    
    def __len__(self):
        return self.stc.GetLineCount()
    
    def _line_range(self, index):
        '''
        Utility method for getting the starting and ending position of this
        line.
        '''
        if not isinstance(index, (int, long)):
            raise KeyError, KE%(self.__class__, type(index))
        x = len(self)
        if index < 0:
            index %= x
        y = self.stc.GetTextLength()
        if index >= x:
            return y,y
        elif x == 1:
            return 0,y
        elif index == 0:
            return 0, self.stc.PositionFromLine(1)
        elif index == x-1:
            return self.stc.PositionFromLine(index), y
        else:
            return self.stc.PositionFromLine(index), self.stc.PositionFromLine(index+1)
    
    def __getitem__(self, index):
        '''
        Gets a line or contiguous sequence of lines.
        That is, it supports slices, but step must be equal to 1.
        '''
        if not isinstance(index, (int, long, slice)):
            raise KeyError, KE%(self.__class__, type(index))
        if isinstance(index, slice):
            if index.step not in (1, None):
                raise KeyError, KE2%(self.__class__, index.step)
            start = max(index.start, 0)
            stop = index.stop
            if stop == None:
                stop = sys.maxint
            stop = min(stop, len(self)-1)
            return [self[i] for i in xrange(start, stop)]
        return self.stc.GetTextRange(*self._line_range(index))
    
    def __setitem__(self, index, value):
        '''
        Changes the content of a line.
        Your new line must include a line ending if you want to keep this line
        separate from the next.
        Does not support slices.
        '''
        
        if not isinstance(value, basestring):
            raise TypeError, TE%(self.__class__, type(value))
        y,z = self._line_range(index)
        self.stc.SetTargetStart(y)
        self.stc.SetTargetEnd(z)
        self.stc.ReplaceTarget(value)
    
    def __delitem__(self, index):
        '''
        Deletes a particular line.
        '''
        self[index] = ''
    
    def __iter__(self):
        '''
        Yields every line in the file in order (uses a 'current line' index,
        so things like:
            
            for i,j in enumerate(lines):
                del lines[i]
        
        will actually delete every other line.
        '''
        i = 0
        while i < len(self):
            yield self[i]
            i += 1
