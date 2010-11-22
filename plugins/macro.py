
import os
import sys
import todo
import imp
import time
import random
import mylistmix
import keydialog
import thread
import threading
__main__ = _pype
import wx

macropath = os.path.join(_pype.runpath, 'macros')

columns = (
    (0, "Macro Name", 150, 0),
    (1, "Hotkey", 50, 0),
    )

class macroList(todo.vTodo, mylistmix.ListSelect):
    def __init__(self, parent, columns):
        todo.vTodo.__init__(self, parent, columns)
        self.parent = parent
    def Refresh(self):
        self.SetItemCount(0)
        try:
            wx.Yield()
        except:
            pass
        self.SetItemCount(len(self.data))
        todo.vTodo.Refresh(self)
    def OnGetItemText(self, item, col):
        if col == 0:
            return "%s" % (self.data[item][col],)
        elif col == 1:
            x = self.parent.d.get(self.data[item][1], (None, None))[1]
            if hasattr(x, "hotkeydisplay"):
                return "%s"%(x.hotkeydisplay,)
            elif hasattr(x, "hotkeyaccept"):
                return "%s"%(x.hotkeyaccept,)
        return ""
    def OnGetItemAttr(self, item):
        if not self.parent.d[self.data[item][1]][1]:
            return red
        return None

template = '''
creation_date = %r
name = %r
hotkeydisplay = ""
hotkeyaccept = ""

%s

'''

hlp = '''\
#Copy and paste the following code into the
#source of the macro that you would like to
#have this hotkey bound to.

%(h)s

#for example:
#...
%(d)s
#...
#def macro(self):
#    ...
'''

def kill_main_thread_in(condition, seconds=6):
    a = threading.Thread(target=_kill_main_thread_in, args=(condition, seconds))
    a.setDaemon(1)
    a.start()

def _kill_main_thread_in(condition, seconds):
    time.sleep(seconds)
    if condition:
        thread.interrupt_main()

red = wx.ListItemAttr()
red.SetTextColour(wx.Colour(200, 0, 0))

timeout = None

def macro_timeout(a,b,c):
    del a, b, c
    if time.time() > timeout:
        raise KeyboardInterrupt, "Macro took more than 5 seconds!"
    try:
        wx.Yield()
    except:
        pass
    return macro_timeout

def start_macro():
    global timeout
    timeout = time.time() + 5
    sys.settrace(macro_timeout)

def end_macro():
    sys.settrace(None)

def rpartition(str, sep):
    if not sep in str:
        return str, ''
    i = str.rfind(sep)
    return str[:i], str[i+len(sep):]

nostart = '''\
Couldn't start macro because some other long-term action is
already being performed within PyPE.  Please wait a few
moments until it is complete, and try again.'''

def load_module(name, fname):
    x = imp.new_module(name)
    x.__file__ = fname
    x.__name__ = name
    x.__builtins__ = __builtins__
    execfile(fname, x.__dict__)
    return x

def Button1(parent, id, which, help, extra):
    bitmap = wx.ArtProvider_GetBitmap(which, wx.ART_TOOLBAR, (16,16))
    z = wx.BitmapButton(parent, id, bitmap, (16,16), (26,26))
    z.SetToolTipString(help)
    return z

def Button2(parent, id, which, help, extra):
    z = wx.Button(parent, id, extra)
    z.SetToolTipString(help)
    return z

class macroPanel(wx.Panel):
    def __init__(self, parent, root):
        wx.Panel.__init__(self, parent)
        self.root = root
        
        if __main__.macro_images:
            bmButton = Button1
        else:
            bmButton = Button2
        
        self.rec1 = bmButton(self, -1, wx.ART_CDROM, "Start Recording", "Record")
        self.rec2 = bmButton(self, -1, wx.ART_ERROR, "Stop Recording", "Stop!"); self.rec2.Hide()
        self.edit = bmButton(self, -1, wx.ART_FOLDER_OPEN, "Edit Macro", "Edit")
        self.empty = bmButton(self, -1, wx.ART_NEW, "New Empty Macro", "New")
        self.hotkey = bmButton(self, -1, wx.ART_ADD_BOOKMARK, "Create Hotkey", "Hotkey")
        self.play = bmButton(self, -1, wx.ART_REDO, "Run Macro", "Run")
        self.de1 = bmButton(self, -1, wx.ART_DELETE, "Delete Macro", "Delete")
        
        
        sz = wx.BoxSizer(wx.HORIZONTAL)
        a = (1, wx.EXPAND|wx.ALL, 2)
        sz.Add(self.rec1, *a)
        sz.Add(self.rec2, *a)
        sz.Add(self.edit, *a)
        sz.Add(self.empty, *a)
        sz.Add(self.hotkey, *a)
        sz.Add(self.play, *a)
        sz.Add(self.de1, *a)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sz, 0, wx.EXPAND)
        
        self.macros = macroList(self, columns)
        sizer.Add(self.macros, 1, wx.EXPAND|wx.ALL, 3)
        
        self.SetSizer(sizer)
        
        self.m = []
        self.d = {}
        self.hotkeys = {}
        self.macros.setData(self.m, copy=0)

        self.t = wx.Timer(self)
        
        self.accelerator = ''
        self.acceleratork = ''
        
        self.macros.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        self.rec1.Bind(wx.EVT_BUTTON, self.OnRec)
        self.rec2.Bind(wx.EVT_BUTTON, self.OnRec)
        self.edit.Bind(wx.EVT_BUTTON, self.OnEdit)
        self.empty.Bind(wx.EVT_BUTTON, self.OnEmpty)
        self.hotkey.Bind(wx.EVT_BUTTON, self.GetHotkey)
        self.play.Bind(wx.EVT_BUTTON, self.OnPlay)
        self.de1.Bind(wx.EVT_BUTTON, self.OnDel)
        
        ## self.t.Bind(wx.EVT_TIMER, self.CheckMacros)
        self.Bind(wx.EVT_TIMER, self.CheckMacros)
        self.t.Start(1000, wx.TIMER_CONTINUOUS)
        
        wx.CallAfter(self.CheckMacros, None)
    
    def RunMacro(self, hotkey):
        if hotkey not in self.hotkeys:
            return 0
        which = self.hotkeys[hotkey]
        self.macros.SelectI(which)
        wx.CallAfter(self.OnPlay, None)
        return 1
    
    def update_button(self, stc=None):
        if not stc:
            stc = self.root.getNumWin(None)[1]
        
        if not hasattr(stc, 'recording'):
            return
        
        if stc.recording:
            self.rec1.Hide()
            self.rec2.Show()
            self.Layout()
        else:
            self.rec1.Show()
            self.rec2.Hide()
            self.Layout()
    
    def OnItemActivated(self, e):
        dc = __main__.macro_doubleclick
        if dc == 0:
            return
        elif dc == 1:
            self.OnEdit(e)
        elif dc == 2:
            self.OnPlay(e)
    
    def CheckMacros(self, e):
        try:
            a = os.listdir(macropath)
        except:
            return
        
        changed = 0
        
        ## self.m = [] #[(name, file), (name, file), ...]
        ## self.d = {} #file : (mtime, module)
        notseen = dict.fromkeys(self.d)
        for name in a:
            if not (name.endswith('.py') or name.endswith('.pyw')):
                if name.endswith('.pyc') or name.endswith('.pyo'):
                    try:
                        os.remove(os.path.join(macropath, name))
                    except:
                        pass
                continue
            
            file = os.path.join(macropath, name)
            
            name, ext = rpartition(name, '.')
            
            try:
                mtime = os.stat(file).st_mtime
            except:
                continue
            
            _ = notseen.pop(file, None)
            if file in self.d and self.d[file][0] == mtime:
                #the file hasn't changed
                continue
            
            module = None
            try:
                module = load_module('_'+name, file)
            except:
                #module load failure...
                #should probably report the exception...
                pass
            
            if hasattr(module, 'name'):
                name = module.name
            
            _ = notseen.pop(file, None)
            if file not in self.d:
                self.m.append((name, file))
                self.d[file] = (mtime, module)
                ## print "new", file
            else:
                for i, f in enumerate(self.m):
                    if f[1] == file:
                        self.m[i] = (name, file)
                        break
                self.d[file] = (mtime, module)
                ## print "updated", file
            changed = 1
        
        for f in notseen:
            i = 0
            while i < len(self.m):
                j = self.m[i]
                if j[1] == f:
                    del self.m[i]
                    del self.d[j[1]]
                    ## print "deleted", f
                    changed = 1
                    break
                else:
                    i += 1
            else:
                print "what?", f
                #not in either list?
                pass
        
        if changed:
            self.hotkeys.clear()
            for i, (n,f) in enumerate(self.m):
                x = self.d[f][1]
                hk = None
                if hasattr(x, "hotkeyaccept"):
                    hk = "%s"%(x.hotkeyaccept,)
                elif hasattr(x, "hotkeydisplay"):
                    hk = "%s"%(x.hotkeydisplay,)
                if hk and hk not in self.hotkeys:
                    self.hotkeys[hk] = i
            self.macros.Refresh()
    
    def OnRec(self, e):
        num, stc = self.root.getNumWin(None)
        if not hasattr(stc, 'recording'):
            return
        stc.MacroToggle(None)
        self.update_button()
        
        if not stc.recording:
            if stc.macro:
                source = stc._macro_to_source()
                self.OnEmpty(e, source)
    
    def OnEdit(self, e):
        x = self.macros.GetFirstSelected()
        if x == -1:
            return
        
        self.root.OnDrop([self.m[x][1]])
    
    def OnEmpty(self, e, source=None):
        if source == None:
            source = 'def macro(self):\n    pass'
        
        fname = 'macro_%i_%i.py'%(int(time.time()), random.randrange(65536))
        ctime = time.asctime()
        name = 'macro: %s'%ctime
        
        open(os.path.join(macropath, fname), 'w').write(template%(ctime, name, source))
        self.CheckMacros(None)
    
    def OnPlay(self, e):
        ## if self.play.GetLabel() == "Stop\nMacro":
            ## global timeout
            ## timeout = None
            ## return
        
        x = self.macros.GetFirstSelected()
        if x == -1:
            return
        
        module = self.d[self.m[x][1]][1]
        if not module:
            return
        
        if not hasattr(module, 'macro'):
            return
        
        stc = self.root.getNumWin(None)[1]
        
        if not hasattr(stc, 'recording'):
            return
        
        if stc.recording:
            self.root.dialog("You must stop recording a macro\nin order to play a macro.", 'Sorry')
            return
        
        try:
            wx.Yield()
        except:
            self.root.dialog(nostart, 'Sorry')
            return
        
        ## self.play.SetLabel("Stop\nMacro")
        
        finished = 0
        start_macro()
        condition = [None]
        kill_main_thread_in(condition)
        try:
            try:
                try:
                    getattr(module, 'macro')(stc)
                except Exception, why:
                    _ = condition.pop()
                    end_macro()
                    finished = 1
                    self.root.exceptDialog("Failure in macro!")
            finally:
                if condition:
                    _ = condition.pop()
                if not finished:
                    end_macro()
                    finished = 1
        finally:
            #We try to cleanup twice to guarantee that the cleanup happens;
            #the kill_main_thread_in() function only tries to kill us once.
            if condition:
                _ = condition.pop()
            if not finished:
                end_macro()
                finished = 1

    def OnDel(self, e):
        x = self.macros.GetFirstSelected()
        if x == -1:
            return
        
        dlg = wx.MessageDialog(self,
                ('Are you sure you want to delete the\n'
                 'the macro with name: %s\n'
                 'with location: %s'
                )%self.m[x],
                'Are you sure?',
                wx.YES_NO | wx.ICON_INFORMATION | wx.NO_DEFAULT
                )
        yesno = dlg.ShowModal()
        dlg.Destroy()
        
        if yesno != wx.ID_YES:
            return
        
        try:
            os.remove(self.m[x][1])
        except:
            self.root.exceptDialog("Macro deletion failed")
        self.CheckMacros(None)
    
    def GetHotkey(self, e):
        self.accelerator = ''
        self.acceleratork = ''
        
        dlg = keydialog.GetKeyDialog(self, '', '', '')
        dlg.ShowModal()
        
        if not (self.accelerator or self.acceleratork):
            return

        ha = 'hotkeyaccept = %r'%self.accelerator
        hd = 'hotkeydisplay = %r'%self.acceleratork
        
        if self.accelerator == self.acceleratork:
            h = ha
            d = '#'+h
        else:
            h = '\n'.join((ha,hd))
            d = '\n'.join(('#'+ha,'#'+hd))
        dlg = wx.lib.dialogs.ScrolledMessageDialog(self, hlp%locals(), "Your hotkey")
        dlg.ShowModal()
        dlg.Destroy()
