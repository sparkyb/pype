
import time
import sys
import os
import re
import wx
import cStringIO
import Queue


lerexp = re.compile('(\r\n)|(\r)|(\n)')
def fixle(st):
    return lerexp.sub(os.linesep, st)

class pseudo_logger:
    def __init__(self):
        self.buffer = cStringIO.StringIO()
        self.softspace = 0
        self.lg = 1
        self.lt = None
        sys.stdout = sys.stderr = self

    def write(self, data):
        ## print >>sys.__stdout__, repr(data), self.softspace
        if self.lg and self.lt != time.asctime():
            self.lt = time.asctime()
            x = '[ %s ] '%self.lt
            self.buffer.write(x)
            sys.__stdout__.write(x)
        
        self.lg = data[-1:] == '\n'
        x = fixle(data)
        self.buffer.write(x)
        sys.__stdout__.write(x.encode('utf8'))
    
    def flush(self):
        sys.__stdout__.flush()

l = pseudo_logger()

class logger(wx.TextCtrl):
    def __init__(self, parent):
        global l
        wx.TextCtrl.__init__(self, parent, -1, style=wx.TE_READONLY|wx.TE_MULTILINE|wx.TE_RICH)
        self.softspace = 0
        self.lg = 1
        self.lt = None
        sys.stdout = sys.stderr = self
        l.buffer.seek(0)
        wx.TextCtrl.AppendText(self, l.buffer.read())
        self.data = Queue.Queue()
        l = self
    
    def write(self, data):
        ## print >>sys.__stdout__, repr(data), self.softspace
        if self.lg and self.lt != time.asctime():
            self.lt = time.asctime()
            x = '[ %s ] '%self.lt
            self.data.put(x)
            try:
                sys.__stdout__.write(x)
            except:
                pass
            
        self.lg = data[-1:] == '\n'
        x = fixle(data)
        self.data.put(x)
        try:
            sys.__stdout__.write(data.encode('utf8'))
        except:
            pass
        wx.CallAfter(self.handle_writes)
    
    def flush(self):
        try:
            sys.__stdout__.flush()
        except:
            pass
    
    def handle_writes(self):
        while self.data.qsize():
            wx.TextCtrl.AppendText(self, self.data.get())
    
    def AppendText(self, txt):
        self.write(txt)
