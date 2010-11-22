
'''
If MyShell is passed a boolean true filter value, it will attempt to parse
lines recieved as if it were recieving Python.  This allows you to add and
change code you want sent to the interpreter until you get it right.  When a
complete "command" is ready to be sent to the underlying shell, PyPE will
attempt to interact with the underlying Python shell as you would.  Sometimes
this doesn't work quite as well as one would hope, and there are extra '...'
and '>>>' which make it to the Python shell.  This shouldn't affect the actual
execution of the code you send to the Python shell, just what you see.

If you don't like this buffering, etc., you can run the command shell (pass a
boolean false filter value), which only buffers a single line at a time.
Whenever the user hits "enter", the current command line is immediately sent
to the underlying shell.  This allows you to use a standard Python shell,
without buffering (you get the actual command-line interaction) via:
    python -u -i -c ""

Note that for some reason, the 'python -u' doesn't work.  Your guess is as
good as mine as to why this is.
'''

import sys
if __name__ == '__main__':
    if not hasattr(sys, 'frozen'):
        import wxversion;wxversion.ensureMinimal('2.6')
sys.ps1 = '>>> '
sys.ps2 = '... '
sys.ps3 = '<-- '
import keyword
import code
import new
import os
from codeop import compile_command
import atexit

import wx
import traceback
from wx import stc
from wx.py.editwindow import FACES
from wx.py.shell import NAVKEYS, Shell

if __name__ != '__main__':
    import __main__

import shell
import lineabstraction

def unimpl_factory(name):
    def _(*args, **kwargs):
        print >>sys.__stdout__, name
    return _

remote = []

def KillProcess():
    for i in remote:
        i.Kill('SIGKILL')

atexit.register(KillProcess)

print_transfer = 0
pushlines_t = 20
poll_t = 50
update_t = 100

def partition(st, sep):
    if sep in st:
        p = st.find(sep)
        return st[:p], sep, st[p+len(sep):]
    return st, '', ''

if sys.platform == 'win32':
    prefix = os.environ.get("COMSPEC", "cmd.exe")
    if " " in prefix:
        prefix = '"%s"'%prefix
    prefix += " /c "
else:
    prefix = "/bin/sh -c "

def rsplit(st):
    st = list(st)
    st.reverse()
    st = list(''.join(st).split(None, 1)[1])
    st.reverse()
    return ''.join(st)

def spliti(string, sep):
    r = []
    start = 0
    end = string.find(sep)
    while end > -1:
        r.append(string[start:end+len(sep)])
        start += len(r[-1])
        end = string.find(sep, start)
    r.append(string[start:])
    return r

unimplemented = ''.split()
cpy = '''
getCommand getMultilineCommand lstripPrompt OnKeyDown replaceFromHistory
OnHistoryReplace OnHistoryInsert clearCommand Copy CopyWithPrompts
CopyWithPromptsPrefixed _clip OnHistorySearch'''.split()

pypecopy = '''
GetSaveState jump GetText SetText Undo Redo changeStyle pos_ch OnUpdateUI
do'''.split()
pypeprefix = '''SetSaveState'''.split()

console_help = '''import sys;print 'Python %s on %s\\n%s'%(sys.version,\
 sys.platform, 'Type \\'help\\', \\'copyright\\', \\'credits\\' or \\'license\\'\
 for more information.');sys.__stdout__ = sys.stdout = sys.__stderr__;del sys;\
 import __builtin__;__builtin__.quit = __builtin__.exit = \
 'use Ctrl-Break to restart *this* interpreter';del __builtin__;'''

encode_error = '''\
UnicodeEncodeError: '%s' codec cannot encode characters from line %i column \
%i to line %i column %i of the input: %s
'''

pypestc = None

MAXLINES = 10000
COLS = 100
MAXDATA = MAXLINES*COLS

class MyShell(stc.StyledTextCtrl):
    if 1:
        dirty = 0
        cached = [], [], {}, []
    def __init__(self, parent, id, root, trees=None, filter=1):
        stc.StyledTextCtrl.__init__(self, parent, id)
        self.lines = lineabstraction.LineAbstraction(self)
        
        global pypestc
        if not pypestc:
            if not __name__ == '__main__':
                import __main__
                pypestc = __main__.PythonSTC
            else:
                class _pypestc:
                    pass
                pypestc = _pypestc
        
        self.root = root
        self.parent = parent
        self.filter = filter
        self._config()
        self.promptPosEnd = 0
        for i in unimplemented:
            setattr(self, i, unimpl_factory(i))
        self.restart = 0
        self.more = False
        self.Restart(None)
        for name in cpy:
            setattr(self, name, new.instancemethod(getattr(Shell, name).im_func, self, self.__class__))
        
        for name in pypecopy:
            if not hasattr(pypestc, name):
                continue
            setattr(self, name, new.instancemethod(getattr(pypestc, name).im_func, self, self.__class__))
        
        for name in pypeprefix:
            if not hasattr(pypestc, name):
                continue
            setattr(self, '_' + name, new.instancemethod(getattr(pypestc, name).im_func, self, self.__class__))
        
        wx.EVT_KEY_DOWN(self, self.OnKeyDown)
        wx.EVT_KEY_DOWN(self, self.OnKeyDown2)
        wx.EVT_CHAR(self, self.OnChar)
        self.Bind(wx.stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        self.scroll = 1
        self.history = []
        self.historyIndex = -1
        self.queue = []
        self.expect = ''
        self.waiting_for = 0
        wx.FutureCall(pushlines_t, self.pushlines)
        wx.FutureCall(poll_t, self.OnPoll)
        self.MakeClean = self.MakeDirty
        self.noteMode = 0
        ## wx.stc.StyledTextCtrl.SetText(self, "def foo():\n...     pass")
        self.trimt = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._trim, self.trimt)
    
    def _config(self):
        self.setStyles(FACES)
        # Do we want to automatically pop up command completion options?
        self.autoComplete = False
        self.autoCompleteIncludeMagic = True
        self.autoCompleteIncludeSingle = True
        self.autoCompleteIncludeDouble = True
        self.autoCompleteCaseInsensitive = True
        self.autoCompleteAutoHide = False
        # Do we want to automatically pop up command argument help?
        self.autoCallTip = False
        try:
            self.SetEndAtLastLine(False)
        except AttributeError:
            pass
    
    def getshort(self):
        if self.filter:
            return "<Python Shell %i>"%self.NEWDOCUMENT
        else:
            return "<Command Shell %i>"%self.NEWDOCUMENT
    def getlong(self):
        return ''
    
    def SetSaveState(self, state):
        state['FOLD'] = state['BM'] = []
        self._SetSaveState(state)
    
    def kill(self):
        self.restart = 1
        self.remote.Kill("SIGKILL")
    
    def clear(self):
        self.ClearAll()
        self.more = 0
        self.promptPosEnd = 0
        self.push('', 0)

    def setStyles(self, faces):
        """Configure font size, typeface and color for lexer."""

        # Default style
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,
                          "face:%(mono)s,size:%(size)d,back:%(backcol)s" % \
                          faces)

        self.StyleClearAll()

        # Built in styles
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,
                          "back:#C0C0C0,face:%(mono)s,size:%(lnsize)d" % faces)
        self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR,
                          "face:%(mono)s" % faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,
                          "fore:#0000FF,back:#FFFF88")
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,
                          "fore:#FF0000,back:#FFFF88")

        # Python styles
        self.StyleSetSpec(stc.STC_P_DEFAULT,
                          "face:%(mono)s" % faces)
        self.StyleSetSpec(stc.STC_P_COMMENTLINE,
                          "fore:#007F00,face:%(mono)s" % faces)
        self.StyleSetSpec(stc.STC_P_NUMBER,
                          "")
        self.StyleSetSpec(stc.STC_P_STRING,
                          "fore:#7F007F,face:%(mono)s" % faces)
        self.StyleSetSpec(stc.STC_P_CHARACTER,
                          "fore:#7F007F,face:%(mono)s" % faces)
        self.StyleSetSpec(stc.STC_P_WORD,
                          "fore:#00007F,bold")
        self.StyleSetSpec(stc.STC_P_TRIPLE,
                          "fore:#7F0000")
        self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,
                          "fore:#000033,back:#FFFFE8")
        self.StyleSetSpec(stc.STC_P_CLASSNAME,
                          "fore:#0000FF,bold")
        self.StyleSetSpec(stc.STC_P_DEFNAME,
                          "fore:#007F7F,bold")
        self.StyleSetSpec(stc.STC_P_OPERATOR,
                          "")
        self.StyleSetSpec(stc.STC_P_IDENTIFIER,
                          "")
        self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,
                          "fore:#7F7F7F")
        self.StyleSetSpec(stc.STC_P_STRINGEOL,
                          "fore:#000000,face:%(mono)s,back:#E0C0E0,eolfilled" % faces)
    
    def EnsureCaretVisible(self):
        if self.scroll:
            stc.StyledTextCtrl.EnsureCaretVisible(self)
    
    def GetSelection(self):
        return self.GetCurrentPos(), self.GetAnchor()
    
    def SetSelection(self, cp, an):
        self.SetCurrentPos(cp)
        self.SetAnchor(an)
        self.ScrollToColumn(0)
    
    def real_poll(self, input=''):
        #todo: fix for unicode
        o = self.remote.Poll(input)
        sc = bool(o[0] or o[1])
        if sc:
            for i in (o[1], o[0]):
                while self.waiting_for > 1 and i.startswith(sys.ps2):
                    i = i[len(sys.ps2):]
                    self.waiting_for -= 1
                    if print_transfer==1: print "got ps2"
                if not i:
                    continue
                if self.waiting_for and i.startswith(sys.ps1):
                    self.write(sys.ps1)
                    i = i[len(sys.ps1):]
                    if print_transfer==1: print "got ps1"
                self.waiting_for = 0
                if i:
                    self.write(i)
            self.EnsureCaretVisible()
            self.ScrollToColumn(0)
            self.EmptyUndoBuffer()
    
    def OnPoll(self, evt=None):
        if hasattr(self, 'remote'):
            self.real_poll('')
        wx.FutureCall(poll_t, self.OnPoll)
    def push(self, command, remember=1):
        if remember:
            c = command
            if not self.filter:
                c = c.rstrip('\r\n')
            self.history.insert(0, c)
        self.historyIndex = -1
        
        if print_transfer==1: print '-->', repr(command)
        command = command.rstrip(os.linesep)
        x = command.split('\n')
        self.waiting_for = len(x) + 1
        if len(x) > 1:
            x.append('')
        x.append('')
        if print_transfer==1: print "need", self.waiting_for
        self.real_poll('\n'.join(x))
    
    def insertLineBreak(self):
        if self.CanEdit():
            self.ReplaceSelection(os.linesep)
            self.more = self.filter
            self.prompt()
    
    def prompt(self):
        if self.filter:
            skip = False
            if self.more:
                prompt = str(sys.ps2)
            else:
                prompt = str(sys.ps1)
            pos = self.GetCurLine()[1]
            if pos > 0:
                self.AddText(os.linesep)
            if not self.more:
                self.promptPosEnd = self.GetCurrentPos()
            if not skip:
                self.AddText(prompt)
        if not self.more:
            self.promptPosEnd = self.GetCurrentPos()
            # Keep the undo feature from undoing previous responses.
            self.EmptyUndoBuffer()
        self.EnsureCaretVisible()
        self.ScrollToColumn(0)
    
    def write(self, data):
        if not data:
            return
        
        lines = self.lines
        
        if print_transfer==1: print '<--', len(data), repr(data)
        s,e = self.GetSelection()
        lp = self.promptPosEnd
        x = self.GetTextLength() #to handle unicode and line endings
        
        self.SetTargetStart(lp)
        self.SetTargetEnd(lp)
        self.ReplaceTarget(data)
        
        ld = self.GetTextLength()-x #to handle unicode and line endings
        self.promptPosEnd += ld
        
        ## x=0
        
        if __name__ != '__main__':
            indic = __main__.SHELL_NUM_TO_INDIC[__main__.SHELL_OUTPUT]
            if indic != None:
                style = self.GetEndStyled()
                
                self.StartStyling(lp, stc.STC_INDIC2_MASK)
                self.SetStyling(ld, stc.STC_INDIC2_MASK)
                self.IndicatorSetStyle(2, indic)
                self.IndicatorSetForeground(2, __main__.SHELL_COLOR)
                
                self.StartStyling(style, stc.STC_INDIC2_MASK^0xff)
        self.SetSelection(s+ld, e+ld)
        ## self.trimt.Start(15, wx.TIMER_ONE_SHOT)
        ## if len(lines) > 500:
            ## self._trim(None)
    
    def _trim(self, e):
        pass
        ## lines = self.lines
        ## gtl = self.GetTextLength()
        ## if len(lines) > MAXLINES or gtl > MAXDATA:
            ## x = self.GetTextLength()
            ## for i in xrange(MAXLINES, len(lines)):
                ## lines[0] = ''
            ## x -= self.GetTextLength()
            ## self.promptPosEnd -= x
            
            ## ogtl = gtl = self.GetTextLength()
            ## while gtl > MAXDATA:
                ## l = lines[0]
                ## gtl -= len(l)
                ## if not l.endswith('\r\n'):
                    ## gtl -= 1
                ## lines[0] = ''
            
            ## ogtl -= self.GetTextLength()
            ## self.promptPosEnd -= x
    
    def processLine(self):
        thepos = self.GetCurrentPos()
        startpos = self.promptPosEnd
        endpos = self.GetTextLength()
        
        if not self.filter:
            tosend = self.GetTextRange(startpos, endpos) + '\n'
            self.AddText('\n')
            self.promptPosEnd = endpos + 1
            self.SetCurrentPos(self.promptPosEnd)
            self.push(tosend)
            return
        
        ps2 = str(sys.ps2)
        # If they hit RETURN inside the current command, execute the
        # command.
        if self.CanEdit():
            self.SetCurrentPos(endpos)
            self.more = 0
            command = self.GetTextRange(startpos, endpos)
            lines = command.split(os.linesep + ps2)
            command = '\n'.join(lines)
            
            if startpos < thepos < endpos:
                self.more = 1
                self.SetCurrentPos(thepos)
                self.prompt()
                return
            
            try:
                command = command.encode('ascii')
            except UnicodeEncodeError, why:
                self.AddText(os.linesep)
                more = 0
                ls = command.count('\n', 0, why.start) + 1
                lsc = command.rfind('\n', 0, why.start)
                if lsc == -1:
                    lsc = why.start
                else:
                    lsc = why.start - lsc
                
                le = command.count('\n', why.start, why.end-1) + ls
                lec = command.rfind('\n', 0, why.end)
                if lec == -1:
                    lec = why.end
                else:
                    lec = why.end - lec
                
                self.AddText(encode_error%(why.encoding, ls, lsc, le, lec, why.reason))
                self.promptPosEnd = self.GetTextLength()
                self.prompt()
                self.promptPosEnd = self.GetTextLength()
                return
            
            try:
                code = compile_command(command)
            except (OverflowError, SyntaxError, ValueError):
                self.AddText(os.linesep)
                self.more = 0
                self.promptPosEnd = self.GetTextLength()
                self.showsyntaxerror()
                self.prompt()
                self.promptPosEnd = self.GetTextLength()
                return

            if code is not None:
                self.AddText(os.linesep)
                self.more = 0
                s = self.GetSelection()
                self.SetSelection(startpos, self.GetTextLength())
                self.SetSelection(*s)
                self.promptPosEnd = self.GetTextLength()
                self.push(command)
            else:
                self.more = 1
                self.SetCurrentPos(thepos)
                self.prompt()
        # Or replace the current command with the other command.
        else:
            # If the line contains a command (even an invalid one).
            if self.getCommand(rstrip=False):
                command = self.getMultilineCommand()
                self.clearCommand()
                self.SetSelection(startpos, startpos)
                self.AddText(command)
            # Otherwise, put the cursor back where we started.
            else:
                self.SetCurrentPos(thepos)
                self.SetAnchor(thepos)
    
    def showsyntaxerror(self, filename=None):
        type, value, sys.last_traceback = sys.exc_info()
        sys.last_type = type
        sys.last_value = value
        if filename and type is SyntaxError:
            # Work hard to stuff the correct filename in the exception
            try:
                msg, (dummy_filename, lineno, offset, line) = value
            except:
                # Not the format we expect; leave it alone
                pass
            else:
                # Stuff in the right filename
                value = SyntaxError(msg, (filename, lineno, offset, line))
                sys.last_value = value
        list = traceback.format_exception_only(type, value)
        map(self.write, list)
    def Restart(self, evt):
        #we start up the console in the future so that if we get a Restart
        #call from the subprocess ending, we can *hopefully* pull the
        #exception from the subprocess shell
        try:
            if not self.restart:
                self.restart = 1
                wx.FutureCall(100, self._Restart, evt)
        except:
            pass
        
    def _Restart(self, evt):
        global remote
        if evt:
            print "Process Ended, pid:%s,  exitCode: %s"%(evt.GetPid(), evt.GetExitCode())
            remote.remove(self.remote)
        self.queue = []
        
        if self.filter:
            self.remote = shell.process(self, prefix + 'python -u -i -c "%s"'%console_help, self.Restart)
        else:
            self.remote = shell.process(self, rsplit(prefix), self.Restart)
        print "Process started, pid:%s"%self.remote.process.pid
        remote.append(self.remote)
        self.restart = 0

    def OnChar(self, event):
        # Prevent modification of previously submitted
        # commands/responses.
        if not self.CanEdit():
            return
        key = event.KeyCode()
        # Return (Enter) needs to be ignored in this handler.
        if key == wx.WXK_RETURN:
            pass
        else:
            # Allow the normal event handling to take place.
            event.Skip()

    def OnKeyDown2(self, event):
        ## print event.GetEventType()
        key = event.KeyCode()
        controlDown = event.ControlDown()
        if controlDown and key in (wx.WXK_CANCEL, wx.WXK_PAUSE):
            self.clearCommand()
            if not self.remote.process._stdin_:
                how = 'SIGKILL'
                self.write("#Trying to terminate with SIGKILL\n")
            else:
                how = shell.close_stdin
                self.write("#Closing subshell STDIN\n")
            self.remote.Kill(how)
        elif not controlDown and key in (wx.WXK_CANCEL, wx.WXK_PAUSE):
            self.scroll ^= 1
        elif not self.filter and key in (wx.WXK_UP, wx.WXK_DOWN):
            self.OnHistoryReplace(step={wx.WXK_DOWN:-1,wx.WXK_UP:1}[key])
        elif controlDown and key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            if not self.filter:
                return self.processLine()
            self.AddText('\n')
            command = self.getcmd()
            self.push(command)
        #todo: add better HOME/END handling
        elif key == wx.WXK_NUMPAD_ENTER:
            #emulate a standard enter keypress
            a = wx.KeyEvent(eventType=wx.wxEVT_KEY_DOWN)
            a.m_keyCode = wx.WXK_RETURN
            for i in ('m_altDown', 'm_controlDown', 'm_metaDown', 'm_rawFlags',
                      'm_scanCode', 'm_shiftDown', 'm_x', 'm_y'):
                setattr(a, i, getattr(event, i))
            wx.PostEvent(self, a)
        else:
            event.Skip()

    def getcmd(self):
        thepos = self.GetCurrentPos()
        startpos = self.promptPosEnd
        endpos = self.GetTextLength()
        
        ps2 = str(sys.ps2)

        self.SetCurrentPos(endpos)
        self.promptPosEnd = endpos
        self.more = 0
        command = self.GetTextRange(startpos, endpos)
        return '\n'.join(command.split(os.linesep + ps2))

    def GetReadOnly(self):
        return min(self.GetSelection()) < self.promptPosEnd

    def CanCopy(self):
        return self.GetSelectionStart() != self.GetSelectionEnd()

    def CanCut(self):
        return self.CanCopy() and self.CanEdit()

    def CanEdit(self):
        return not self.GetReadOnly()

    def CanPaste(self):
        return stc.StyledTextCtrl.CanPaste(self) and self.CanEdit()
    def Paste(self):
        success = False
        do = wx.TextDataObject()
        if wx.TheClipboard.Open():
            success = wx.TheClipboard.GetData(do)
            wx.TheClipboard.Close()

        if not success:
            return
        
        self.ReplaceSelection('')
        
        self.queue.extend(spliti(do.GetText(), '\n'))
    def Cut(self):
        if self.CanCut:
            stc.StyledTextCtrl.Cut(self)
    
    def pushlines(self):
        if not self.waiting_for and self.queue:
            x = self.queue.pop(0)
            self.AddText(x.rstrip('\r\n'))
            if x[-1:] == '\n':
                self.processLine()
        wx.FutureCall(pushlines_t, self.pushlines)
    def MakeDirty(self, e=None):
        f = self.filename
        if f == ' ':
            f = '<%s %i>'%(('Command Shell', 'Python Shell')[self.filter], self.NEWDOCUMENT)
        c = 0
        for i in self.root.control:
            if i == self:
                break
            c += 1
        self.root.control.SetPageText(c, f)
        self.root.redrawvisible(self)
    def DeleteSelection(self, e=None):
        range = self.GetSelection()
        mi = min(range)
        ma = max(range)
        if ma <= self.promptPosEnd:
            self.promptPosEnd -= ma-mi
        elif mi < self.promptPosEnd:
            self.promptPosEnd = mi
        stc.StyledTextCtrl.DeleteBack(self)

#

class MyShellFrame(wx.Frame):
    def __init__(self):
        """Create ShellFrame instance."""
        wx.Frame.__init__(self, None, -1, "Standalone PyPE Shell", size=(800, 400))
        self.shell = MyShell(self, -1, self, None, 1)
        self.CreateStatusBar(2)
        self.GetStatusBar().SetStatusWidths([-1, 95])
        # Override the shell so that status messages go to the status bar.
        self.shell.setStatusText = self.SetStatusText

def main():
    app = wx.App(0)
    wx.InitAllImageHandlers()
    frame = MyShellFrame()
    frame.Show()
    app.SetTopWindow(frame)
    frame.shell.SetFocus()
    app.MainLoop()

if __name__ == '__main__':
    print_transfer = 0
    main()
