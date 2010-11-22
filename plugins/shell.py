
import os
import sys
import compiler

import wx

import popup

ToggleButton = wx.ToggleButton
if wx.Platform == "__WXX11__":
    ToggleButton = wx.CheckBox

enabled = 1

def fix(cb, c, count=10):
    o = cb.FindString(c)
    if o != wx.NOT_FOUND:
        cb.Delete(o)
    cb.Insert(c, 0)
    cb.SetSelection(0)
    while cb.GetCount() > 10:
        cb.Delete(10)

def get_combo_list(cb):
    r = []
    for i in xrange(cb.GetCount()):
        r.append(cb.GetString(i))
    return r

quickhelp = '''\
 - You can use %(path)s, %(file)s, and %(full)s to represent the path,
   filename, and full path of the current document (paths/files with spaces
   are automatically quoted).  If no documents are open, or the file is
   untitled, it will abort with a status message.
 - For some processes, closing stdin may not kill it immediately.
 - SIGTERM is the 'nice' way to kill runaway programs (if stdin closing does
   not work).
 - SIGKILL is the 'mean' way to kill runaway programs (if stdin closing and
   SIGTERM do not work).
 - Scrollback size is limited to 100,000 lines, buf if you want it to perform
   reasonably well, stick to 10,000 lines or less.  It actually makes sure you
   have at most X lines and at most X*linewidth characters (where linewidth is
   extrapolated from font size and the width of the text control).
'''

win = '''\
Note: On Windows, some command line programs have issues dealing with
buffering.  In those cases, you may want to opt for "new window", which will
use 'start' to start the process externally with its own console if necessary.
If you would like to have a Python console in the shell tab, you can use:
    python -u -i -c ""
(remember to enable echo)

 - Sending '\\x03' (including quotes and using unescape) does not actually
   get one a keyboard interrupt on Windows.  If anyone has ideas, I'd like to
   hear them.
'''

all_but_mac = '''
(drag me around, or right-click to close me)'''

choices = [('normal', "")]
chsuffix = {}
if sys.platform == 'win32':
    prefix = os.environ.get("COMSPEC", "cmd.exe")
    if " " in prefix:
        prefix = '"%s"'%prefix
    prefix += " /c "
    choices.append(('via shell', prefix))
    choices.append(('new console', prefix + 'start "" '))
    quickhelp = win + quickhelp
else:
    choices.append(('via shell', "/bin/sh -c "))
    choices.append(('new console', "xterm -e "))
    chsuffix['new console'] = ' &'
    

if wx.Platform == '__WXMAC__':
    wx.PopupWindow = wx.Window
else:
    quickhelp = quickhelp + all_but_mac

chnames = [i[0] for i in choices]
chlookup = dict(choices)

class StartupError(Exception):
    pass

close_stdin = "<CLOSE STDIN>"
blocksize = 512

class process:
    def __init__(self, parent, cmd, end_callback):
        self.process = wx.Process(parent)
        self.process.Redirect()
        self.process.pid = wx.Execute(cmd, wx.EXEC_ASYNC, self.process)
        self.b = []
        if self.process.pid:
            #what was up with wx.Process.Get*Stream names?
            self.process._stdin_ = self.process.GetOutputStream()
            self.process._stdout_ = self.process.GetInputStream()
            self.process._stderr_ = self.process.GetErrorStream()
            self.process.Bind(wx.EVT_END_PROCESS, end_callback)
            return
        raise StartupError
            
    def Poll(self, input=''):
        if (input or self.b) and self.process and self.process._stdin_:
            if self.b or len(input) > blocksize:
                if input:
                    #if we don't chop up our input into resonably sized chunks,
                    #some platforms (like Windows) will send some small number
                    #of bytes per .write() call (sometimes 2 in the case of
                    #Windows).
                    self.b.extend([input[i:i+blocksize] for i in xrange(0, len(input), blocksize)])
                input = self.b.pop(0)
            self.process._stdin_.write(input)
            if hasattr(self.process._stdin_, "LastWrite"):
                y = self.process._stdin_.LastWrite()
                if y != len(input):
                    self.b.insert(0, input[y:])
        x = []
        for s in (self.process._stderr_, self.process._stdout_):
            if s and s.CanRead():
                x.append(s.read())
            else:
                x.append('')
        return x
        
    def CloseInp(self):
        if self.process and self.process._stdin_:
            self.process.CloseOutput()
            self.process._stdin_ = None
    
    def Kill(self, ks):
        errors = {wx.KILL_BAD_SIGNAL: "KILL_BAD_SIGNAL",
                  wx.KILL_ACCESS_DENIED: "KILL_ACCESS_DENIED",
                  wx.KILL_ERROR: "KILL_ERROR"}
        if self.process:
            if ks == close_stdin:
                self.CloseInp()
                return 1, None
            elif wx.Process.Exists(self.process.pid):
                signal = getattr(wx, ks)
                r = wx.Process.Kill(self.process.pid, signal, flags=wx.KILL_CHILDREN)
            else:
                r = 65535
                self.CloseInp()
                return 1, None
            
            if r not in (wx.KILL_OK, wx.KILL_NO_PROCESS, 65535):
                return 0, (self.process.pid, signal, errors.get(r, "UNKNOWN_KILL_ERROR %s"%r))
            else:
                return 1, None

class Shell(wx.Panel):
    def __init__(self, parent, root, prefs={}):
        wx.Panel.__init__(self, parent, -1)
        self.root = root

        self.subprocess = None
        
        # Make the controls
        prompt = wx.StaticText(self, -1, 'Command line:')
        self.cmd = wx.ComboBox(self, -1, choices=prefs.get('cmds', []), style=wx.TE_PROCESS_ENTER|wx.CB_DROPDOWN)
        self.how = wx.Choice(self, -1, choices=chnames)
        self.how.SetSelection(prefs.get('how', 0))
        self.exBtn = wx.Button(self, -1, 'Execute')
        self.set1 = [self.cmd, self.how, self.exBtn]
        expl = wx.StaticText(self, -1, 'Scrollback:')
        self.ss = wx.TextCtrl(self, -1, "1000", size=(70, -1))
        b = wx.Button(self, -1, "?", size=(16,16))

        self.out = wx.TextCtrl(self, -1, '', style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2)
        fnt = wx.SystemSettings_GetFont(wx.SYS_ANSI_FIXED_FONT)
        self.fontsize = fnt.GetPointSize()
        ta = wx.TextAttr()
        ta.SetFont(fnt)
        self.out.SetDefaultStyle(ta)

        ch =  ('<CLOSE_STDIN> SIGHUP SIGINT SIGQUIT SIGILL SIGTRAP SIGABRT SIGEMT '
               'SIGFPE SIGKILL SIGBUS SIGSEGV SIGSYS SIGPIPE SIGALRM SIGTERM').split()
        ch[0] = ch[0].replace('_', ' ')
        if sys.platform == 'win32':
            ch = [ch[0], ch[9], ch[15]]

        self.inp = wx.ComboBox(self, -1, choices=prefs.get('history', []), style=wx.TE_PROCESS_ENTER|wx.CB_DROPDOWN|wx.WANTS_CHARS)
        self.sndBtn = wx.Button(self, -1, 'Send')
        self.echo = ToggleButton(self, -1, 'Echo')
        self.echo.SetValue(prefs.get('echo', 0))
        self.unescape = ToggleButton(self, -1, 'Unescape')
        self.unescape.SetValue(prefs.get('unescape', 0))
        self.autoscroll = ToggleButton(self, -1, 'Auto scroll')
        self.autoscroll.SetValue(prefs.get('scroll', 1))
        self.pause = ToggleButton(self, -1, 'Pause')
        self.pause.SetValue(prefs.get('pause', 0))
        self.killBtn = wx.Button(self, -1, 'End Process')
        self.killSel = wx.ComboBox(self, -1, choices=ch, style=wx.CB_READONLY)
        self.killSel.SetSelection(0)
        self.set2 = [self.inp, self.sndBtn, self.echo, self.unescape, self.autoscroll, self.pause, self.killBtn, self.killSel]    
        
        for i in self.set2:
            i.Enable(False)

        # Hook up the events
        self.Bind(wx.EVT_BUTTON, self.OnExecuteBtn, self.exBtn)
        self.Bind(wx.EVT_BUTTON, self.OnShowPopup, b)
        self.Bind(wx.EVT_BUTTON, self.OnSendText, self.sndBtn)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnSendText, self.inp)
        self.inp.Bind(wx.EVT_CHAR, self.OnChar, self.inp)
        self.Bind(wx.EVT_BUTTON, self.OnKillProcess, self.killBtn)

        # Do the layout
        box1 = wx.BoxSizer(wx.HORIZONTAL)
        box1.Add(prompt, 0, wx.ALIGN_CENTER)
        box1.Add(self.cmd, 1, wx.ALIGN_CENTER|wx.LEFT, 5)
        box1.Add(self.how, 0, wx.ALIGN_CENTER|wx.LEFT, 5)
        box1.Add(self.exBtn, 0, wx.LEFT, 5)
        box1.Add(expl, 0, wx.ALIGN_CENTER|wx.LEFT, 5)
        box1.Add(self.ss, 0, wx.ALIGN_CENTER|wx.LEFT, 5)
        box1.Add(b, 0, wx.ALIGN_CENTER|wx.LEFT, 5)

        box2 = wx.BoxSizer(wx.HORIZONTAL)
        for i,j in enumerate(self.set2):
            box2.Add(j, i==0, wx.ALIGN_CENTER|wx.LEFT, (0, 5)[i>0])

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(box1, 0, wx.EXPAND|wx.ALL, 10)
        sizer.Add(self.out, 1, wx.EXPAND|wx.ALL, 10)
        sizer.Add(box2, 0, wx.EXPAND|wx.ALL, 10)

        self.SetSizer(sizer)
        self.SetAutoLayout(True)
        
        #create a timer
        self.timer = wx.Timer(self, -1)
        self.Bind(wx.EVT_TIMER, self.OnPoll, self.timer)
    
    def OnChar(self, evt):
        if evt.GetKeyCode() == wx.WXK_TAB:
            f,t = self.inp.GetMark()
            self.inp.Remove(f,t)
            val = self.inp.GetValue()
            self.inp.SetValue(val[:f] + '\t' + val[f:])
            self.inp.SetMark(f+1,f+1)
        else:
            evt.Skip()

    def OnShowPopup(self, evt):
        win = popup.Popup(self, quickhelp)

        # Show the popup right below or above the button
        # depending on available screen space...
        btn = evt.GetEventObject()
        pos = btn.ClientToScreen( (0,0) )
        sz =  btn.GetSize()
        win.Position(pos, (0, sz[1]))

        win.Show(True)
    
    def save_prefs(self):
        return {'cmds':get_combo_list(self.cmd),
                'how':self.how.GetSelection(),
                'history':get_combo_list(self.inp),
                'echo':self.echo.GetValue(),
                'unescape':self.unescape.GetValue(),
                'scroll':self.autoscroll.GetValue(),
                'pause':self.pause.GetValue()}
                
    
    def started(self):
        for i in self.set1:
            i.Enable(False)
        for i in self.set2:
            i.Enable(True)
        self.timer.Start(50, wx.TIMER_CONTINUOUS)
    
    def OnExecuteBtn(self, evt):
        cmd = self.cmd.GetValue()
        fix(self.cmd, cmd, 10)
        
        how = self.how.GetStringSelection()
        prefix = chlookup.get(how, '')
        if not cmd.startswith(prefix):
            if sys.platform == 'win32' and how == 'new console':
                prefix = prefix.replace('""', '"' + cmd.replace('"', "'") + '"')
            cmd = prefix + cmd
        suffix = chsuffix.get(how, '')
        if not cmd.endswith(suffix):
            cmd += suffix
        
        incl_paths = 0
        for i in ('%(path)s', '%(file)s', '%(full)s'):
            if i in cmd:
                incl_paths = 1
                break
        
        if incl_paths:
            try:
                num, win = self.root.getNumWin(evt)
            except cancelled:
                self.root.SetStatusText("Cannot use document expansions, no documents open.")
                return
            
            dn, fn = win.dirname, win.filename
            if not (dn and fn):
                self.root.SetStatusText("Cannot use document expansions, untitled document selected.")
            
            x = {'path':dn, 'file':fn, 'full':os.path.join(dn, fn)}
            #handle quoting
            for k,v in x.items():
                if ' ' in v:
                    x[k] = '"%s"'%v
            
            cmd = cmd%x
        
        try:
            self.process = process(self, cmd, self.OnProcessEnded)
            self.started()
            self.root.SetStatusText("Started, pid: %i command: %s"%(self.process.process.pid, cmd))
        except StartupError:
            self.process = None
            self.root.SetStatusText("Couldn't start command: %s"%cmd)
            self.root.SetStatusText("Try disabling/enabling the use of a shell, or running the shell directly")            

    def ended(self):
        self.process = None
        for i in self.set1:
            i.Enable(True)
        for i in self.set2:
            i.Enable(False)
        self.timer.Stop()
    
    def OnProcessEnded(self, evt):
        self.OnCloseStream(evt)
        for i in self.process.Poll():
            self.AppendText(i)
        self.root.SetStatusText("Process Ended, pid:%s,  exitCode: %s"%(evt.GetPid(), evt.GetExitCode()))
        self.ended()
    
    def OnSendText(self, evt):
        if self.process and self.process.process._stdin_:
            c = self.inp.GetValue()
            #handle string escaping...
            if c.strip():
                fix(self.inp, c, 10)
            if c and c[-1] in ['"', "'"] and self.unescape.GetValue():
                try:
                    c = [i for i in compiler.parse(str(c)).getChildren()[:1] if isinstance(i, basestring)][0]
                except Exception, e:
                    pass
            try:
                c = str(c+'\n')
            except UnicodeEncodeError, why:
                self.root.SetStatusText("Couldn't send to subprocess: %s"%why)
                return
            ta = self.process.Poll(c)
            if self.echo.GetValue():
                self.AppendText(c)
            for i in ta:
                self.AppendText(i)
            self.inp.SetValue('')
            self.inp.SetFocus()

    def OnCloseStream(self, evt):
        self.process.CloseInp()
        self.inp.Enable(False)
        self.sndBtn.Enable(False)
    
    def OnKillProcess(self, evt):
        if self.process:
            succ, args = self.process.Kill(self.killSel.GetValue())
            if succ:
                self.OnCloseStream(evt)
            else:
                self.root.SetStatusText("***Error killing process: %i  with signal: %i  error: %s ***"%args)
    
    def AppendText(self, txt):
        if not txt:
            return
        
        posn = self.out.GetInsertionPoint()
        self.out.AppendText(txt)
        
#------------------------ handle scrollback overflow -------------------------
        x = self.ss.GetValue()
        v = 1000
        try:
            v = int(x)
        except:
            pass
        if v < 1:
            v = 100000
        #estimated number of characters per line.
        w = v*max(self.out.GetSizeTuple()[0]//self.fontsize, 1)

        #handle line count overflow
        cl = self.out.GetNumberOfLines()
        lp = 0
        i = -1
        if cl > v:
            lp = cl-v
            for i in xrange(0, lp):
                lp += self.out.GetLineLength(i)

        #handle data volume overflow
        cp = self.out.GetLastPosition()
        i += 1
        while (cp - lp) > w:
            lp += self.out.GetLineLength(i) + 1
            i += 1
        
        asc = self.autoscroll.GetValue()
        if not asc:
            self.out.SetInsertionPoint(posn)
        
        if lp:
            self.out.Remove(0, lp)
        
        if asc:
            screenlines = max(3*self.out.GetSizeTuple()[1]//(self.fontsize*5), 1)
            lp = self.out.GetLastPosition()
            lines = self.out.GetNumberOfLines()
            for i in xrange(lines-1, max(lines-screenlines-1, -1), -1):
                lp -= self.out.GetLineLength(i) + (i != lines-1)
            self.out.ShowPosition(lp)
    
    def OnPoll(self, evt):
        
        if self.process and not self.pause.GetValue():
            for i in self.process.Poll():
                self.AppendText(i)
