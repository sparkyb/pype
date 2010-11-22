
'''
This software is licensed under the GPL (GNU General Public License) version 2
as it appears here: http://www.gnu.org/copyleft/gpl.html
It is also included with this archive as `gpl.txt <gpl.txt>`_.
'''


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
import stat
from codeop import compile_command
import parser
import atexit
## import heapq
import scheduler
try:
    import _winreg
except:
    pass


import wx
import time
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
    for i in remote[:]:
        try:
            i.Kill('SIGKILL')
        except:
            pass

atexit.register(KillProcess)

print_transfer = 0
pushlines_t = 20
poll_t = 50

def partition(st, sep):
    if sep in st:
        p = st.find(sep)
        return st[:p], sep, st[p+len(sep):]
    return st, '', ''

workingplatforms = ('win32', 'linux2')

if sys.platform == 'win32':
    command = os.environ.get("COMSPEC", "cmd.exe")
    if " " in command:
        command = '"%s"'%command
elif sys.platform == 'linux2':
    command = '/bin/sh --noediting -i'
else:
    command = '/bin/sh'

def discover_python_installs(print_discovered=0):
    seen = {}
    possible_pythons = []
    ok = '2.2 2.3 2.4 2.5 2.6 3.0 .exe'.split()    
    
    pf = 0
    
    se = sys.executable
    se1 = os.path.split(se)[1]
    if se1.startswith('python') and se1[6:].lower() in ok:
        try:
            se = os.path.realpath(sys.executable)
        except:
            pass
        if print_discovered: print "sys.executable:", se
        possible_pythons.append((sys.maxint, sys.executable))
        seen[os.path.normcase(se)] = None
    del se
    sp = ':'
    if sys.platform == 'win32':
        #check the registry on Windows
        for mainkey in (_winreg.HKEY_LOCAL_MACHINE, _winreg.HKEY_CURRENT_USER):
            a = None
            try:
                try:
                    a = _winreg.ConnectRegistry(None,mainkey)
                    
                    for ver in '2.6 2.5 2.4 2.3 2.2 3.0'.split():
                        spth = 'SOFTWARE\\Python\\PythonCore\\%s\\InstallPath'%ver
                        b = None
                        try:
                            try:
                                b = _winreg.OpenKey(a, spth)
                                
                                i_pth = _winreg.QueryValue(b, None)
                                i_pth = os.path.join(i_pth, 'python.exe')
                                i_pth = os.path.realpath(i_pth)
                                
                                if os.path.normcase(i_pth) in seen:
                                    continue
                                
                                m = os.stat(i_pth)
                                
                                if stat.S_ISREG(m.st_mode):
                                    if print_discovered: print "In Registry:", i_pth
                                    possible_pythons.append((m.st_mtime, i_pth))
                                    seen[os.path.normcase(i_pth)] = None
                                
                            except:
                                pass
                        finally:
                            if b:
                                try:
                                    _winreg.CloseKey(b)
                                except:
                                    pass
                        del b
                except:
                    pass
            finally:
                if a:
                    try:
                        _winreg.CloseKey(a)
                    except:
                        pass
                del a
        sp = ';'
    
    #check PATH on all platforms
    for _pth in os.environ.get('PATH', '').split(';'):
        if _pth:
            try:
                x = os.listdir(_pth)
            except:
                continue
            for i in x:
                if not i.startswith('python') or i[6:].lower() not in ok:
                    continue
                i_pth = os.path.join(_pth, i)
                i_pth = os.path.realpath(i_pth)
                
                if os.path.normcase(i_pth) in seen:
                    continue
                try:
                    m = os.stat(i_pth)
                except:
                    continue
                if stat.S_ISREG(m.st_mode):
                    pf += 1
                    if print_discovered: print "On Path:", i_pth
                    possible_pythons.insert(-1, (sys.maxint-pf, i_pth))
                    seen[os.path.normcase(i_pth)] = None
    
    possible_pythons.sort()
    possible_pythons.reverse()
        
    return [j for i,j in possible_pythons], seen
    
python_choices, pythons_seen = discover_python_installs()
which_python = (python_choices or ['python'])[0]

def check_paths(lst, ch=None):
    for i in lst:
        if os.path.normcase(i) not in pythons_seen:
            try:
                m = os.stat(i)
            except:
                continue
            
            if stat.S_ISREG(m.st_mode):
                python_choices.append(i)
                pythons_seen[os.path.normcase(i)] = None

    if ch and os.path.normcase(ch) in pythons_seen:
        global which_python
        which_python = ch
    
    try:
        _ = python_choices.remove(which_python)
    except:
        pass
    
    python_choices.insert(0, which_python)
    

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
do indicate_text gotcharacter _gotcharacter'''.split()
pypeprefix = '''SetSaveState'''.split()

python_cmd = '''%s -u -c "import sys;sys.stderr=sys.__stderr__=\
 sys.stdout;import __builtin__;__builtin__.quit=__builtin__.exit=\
 'use Ctrl-Break to restart *this* interpreter';import code;\
 code.interact(readfunc=raw_input)"'''

encode_error = '''\
UnicodeEncodeError: '%s' codec cannot encode characters from line %i column \
%i to line %i column %i of the input: %s
'''

pypestc = None

MAXLINES = 1000
COLS = 100
MAXDATA = MAXLINES*COLS
LIMIT_LENGTH = 0

osxshellmessage = '''\
Your shell may not output a prompt even if it is working otherwise.
If you would like to help fix this, please contact the author.
'''

killsteps = ['SIGKILL', shell.close_stdin]
if 'win' not in sys.platform:
    #non-windows platforms should have a working signal implementation
    killsteps.append('SIGINT')

fc = []

def FutureCall(delay, fcn, *args, **kwargs):
	scheduler.FutureCall(delay, fcn, *args, **kwargs)

instances = []

def poll_all(arg=None):
    j = 0
    while j < len(instances):
        i = instances[j]
        try:
            i.root
        except:
            del instances[j]
        else:
            j += 1
            try:
                i.OnPoll()
            except:
                traceback.print_exc()
    
    ## tt = time.time()
    ## while fc and fc[0][0] < tt:
        ## _, fcn, args, kwargs = heapq.heappop(fc)
        ## try:
            ## fcn(*args, **kwargs)
        ## except:
            ## traceback.print_exc()

_Poller = scheduler.Timer(poll_all)

class MyShell(stc.StyledTextCtrl):
    if 1:
        dirty = 0
        cached = [], [], {}, []
    def __init__(self, parent, id, root, trees=None, filter=1):
        stc.StyledTextCtrl.__init__(self, parent, id)
        self.lines = lineabstraction.LineAbstraction(self)
        self.NEWDOCUMENT = _pype.NEWDOCUMENT+1
        
        global pypestc
        if not pypestc:
            if not __name__ == '__main__':
                pypestc = _pype.PythonSTC
            else:
                class _pypestc:
                    pass
                pypestc = _pypestc
        
        self.root = root
        self.parent = parent
        self.filter = filter==1
        if filter:
            self.lexer = 'python'
        else:
            self.lexer = 'text'
        self._config()
        self.promptPosEnd = 0
        for i in unimplemented:
            setattr(self, i, unimpl_factory(i))
        self.restartable = filter != 3
        self.restart = not self.restartable
        self.more = False
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
        self.MakeClean = self.MakeDirty
        self.noteMode = 0
        ## wx.stc.StyledTextCtrl.SetText(self, "def foo():\n...     pass")
        if sys.platform not in workingplatforms and self.filter == 0 and self.restartable:
            self.write(osxshellmessage)
        self.has_bad = 0
        self.recording = 0
        self.lastparse = 50
        self.lastparse2 = 100
        self.m1 = None
        self.m2 = None
        
        self.Restart(None)
        instances.append(self)
		
        if not _Poller.IsRunning():
            _Poller.Start(10)
    
    def _gotcharacter2(self, e=None):
        pass
    
    def _update_fold(self, *args):
        pass
    
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
        if self.filter==1:
            x = "<Python Shell %i>"
        elif self.filter==0 and self.restartable:
            x = "<Command Shell %i>"
        else:
            x = "<Command Output %i>"
        x = x%self.NEWDOCUMENT
        return x
    def getlong(self):
        return self.getshort()
    
    def SetSaveState(self, state):
        state['FOLD'] = state['BM'] = []
        self._SetSaveState(state)
    
    def kill(self):
        self.restart = 1
        if hasattr(self, 'remote'):
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
        if not hasattr(self, 'remote'):
            return
        if not self.remote:
            return
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
        self.pushlines()
        ## wx.FutureCall(poll_t, self.OnPoll)
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
        data = data.replace('\r', '')
        s,e = self.GetSelection()
        lp = self.promptPosEnd
        x = self.GetTextLength() #to handle unicode and line endings
        
        self.SetTargetStart(lp)
        self.SetTargetEnd(lp)
        self.ReplaceTarget(data)
        
        ld = self.GetTextLength()-x #to handle unicode and line endings
        self.promptPosEnd += ld
        
        if __name__ != '__main__':
            self.indicate_text(lp, ld, 1)
        
        x = 0
        
        if LIMIT_LENGTH:
            lm = 0
            #handle too much raw data
            gtl = self.GetTextLength()
            if gtl > MAXDATA:
                posn = gtl-MAXDATA
                ll = 0
                lm = len(lines)
                
                while ll < lm:
                    lmi = (ll+lm)//2
                    if lines._line_range(lmi)[1] < posn:
                        ll = lmi + 1
                    else:
                        lm = lmi
            
            #handle too many lines
            if len(lines) > MAXLINES:
                lm = max(lm, len(lines)-MAXLINES)
            
            #adjust the actual content
            if lm:
                lines.selectedlinesi = 0, lm+1
                lines.selectedlines = []
                gtl -= self.GetTextLength()
                x = gtl
        
        self.promptPosEnd -= x
        self.SetSelection(s+ld-x, e+ld-x)
        
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
        ## print "Restart"
        #we start up the console in the future so that if we get a Restart
        #call from the subprocess ending, we can *hopefully* pull the
        #exception from the subprocess shell
        
        try:
            self.restart
        except:
            print "Process Ended, pid:%s,  exitCode: %s"%(evt.GetPid(), evt.GetExitCode())
            return
        
        if not self.restart:
            ## print "not restart"
            self.restart = 1
            if self.restartable:
                ## print "restartable!"
                FutureCall(100, self._Restart, evt)
            else:
                ## print "not restartable"
                FutureCall(100, self._close, evt)
        else:
            ## print "tried to close!"
            self._close(evt)
            ## raise Exception
        
        ## try:
        ## except:
            ## pass
    def _close(self, evt):
        ## print "_close", evt
        if evt:
            print "Process Ended, pid:%s,  exitCode: %s"%(evt.GetPid(), evt.GetExitCode())
            remote.remove(self.remote)
            del self.remote
            if not self.restartable:
                self.write('\n**** End of process output ****\n')
    def _Restart(self, evt):
        ## print "_Restart"
        if evt and not isinstance(evt, tuple):
            self._close(evt)
        del self.queue[:]
        self.killsteps = killsteps[:]
        
        if self.restartable:
            ## print "Restartable!"
            d = ''
            if self.filter:
                wp = which_python
                if ' ' in wp:
                    wp = '"%s"'%wp
                c = python_cmd%wp
            else:
                c = command
        elif isinstance(evt, tuple) and len(evt) == 2:
            ## print "Starting!"
            d, c = evt
        else:
            ## print "quitting!"
            return
        
        if d:
            x = os.getcwd()
            try:
                os.chdir(d)
            except:
                self.write("could not switch to %r\n"%d)
                return
        self.remote = shell.process(self, c, self.Restart)
        if d:
            os.chdir(x)
        
        print "Process started, pid:%s"%self.remote.process.pid
        remote.append(self.remote)
        self.restart = 0

    def OnChar(self, event):
        # Prevent modification of previously submitted
        # commands/responses.
        if not self.CanEdit():
            ## print "can't edit!"
            return
        key = GetKeyCode(event)
        # Return (Enter) needs to be ignored in this handler.
        if key == wx.WXK_RETURN:
            pass
        else:
            # Allow the normal event handling to take place.
            event.Skip()
            if self.filter and __name__ != '__main__':
                self.gotcharacter
    
    def _kill_me(self):
        self.clearCommand()
        if self.killsteps:
            how = self.killsteps.pop()
            if how == 'SIGKILL':
                self.write("#Trying to terminate with SIGKILL\n")
            elif how == 'SIGINT':
                self.write("#Trying to interrupt with SIGINT\n")
            elif how == shell.close_stdin:
                self.write("#Closing subshell STDIN\n")
            self.remote.Kill(how)
    
    def OnKeyDown2(self, event):
        ## print event.GetEventType()
        key = event.GetKeyCode()
        controlDown = event.ControlDown()
        if controlDown and key in (wx.WXK_CANCEL, wx.WXK_PAUSE):
            self._kill_me()
        elif not controlDown and key in (wx.WXK_SCROLL, wx.WXK_CANCEL, wx.WXK_PAUSE):
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
        if self.filter and __name__ != '__main__':
            self.gotcharacter

    def getcmd(self, ue=1):
        startpos = self.promptPosEnd
        endpos = self.GetTextLength()
        
        ps2 = str(sys.ps2)
        
        if ue:
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
        
        x,y = self.GetSelection()
        if x < self.promptPosEnd:
            x = self.promptPosEnd
        if y < self.promptPosEnd:
            y = self.promptPosEnd
        self.SetSelection(x,y)
        
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
        ## wx.FutureCall(pushlines_t, self.pushlines)
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
    def _activity(self):
        pass

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
