
import time
import sys
import wx
import cStringIO
import Queue

class pseudo_logger:
    def __init__(self):
        self.buffer = cStringIO.StringIO()
        self.softspace = 0
        self.lg = 1
        self.lt = None
        sys.stdout = self
        sys.stderr = self

    def write(self, data):
        ## print >>sys.__stdout__, repr(data), self.softspace
        if self.lg and self.lt != time.asctime():
            self.lt = time.asctime()
            x = '[ %s ] '%self.lt
            self.buffer.write(x)
            sys.__stdout__.write(x)
        
        self.lg = data[-1:] == '\n'
        x = data.replace('\r', '').replace('\n', '\r\n')
        self.buffer.write(x)
        sys.__stdout__.write(x.encode('utf8'))
    
    def flush(self):
        sys.__stdout__.flush()

l = pseudo_logger()

class logger(wx.TextCtrl):
    def __init__(self, parent):
        wx.TextCtrl.__init__(self, parent, -1, style=wx.TE_READONLY|wx.TE_MULTILINE|wx.TE_RICH)
        self.softspace = 0
        self.lg = 1
        self.lt = None
        sys.stdout = self
        sys.stderr = self
        l.buffer.seek(0)
        self.AppendText(l.buffer.read())
        del globals()['l']
        self.data = Queue.Queue()
    
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
        x = data.replace('\r', '').replace('\n', '\r\n')
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
            self.AppendText(self.data.get())
