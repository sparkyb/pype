
#system imports
import os
import stat
import sys

#site-packages imports
import wx

#local imports
import filehistory

class FilesystemBrowser(wx.Panel):
    def __init__(self, parent, root, pathnames=[], maxlen=0):
        wx.Panel.__init__(self, parent)
        self.root = root
        
        self.sizer = sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.button = wx.Button(self, -1, "Pathmark...")
        wx.EVT_BUTTON(self, self.button.GetId(), self.OnButton)
        sizer.Add(self.button, 0, wx.EXPAND)
        
        self.browser = wx.GenericDirCtrl(self, -1, style=wx.DIRCTRL_SHOW_FILTERS, filter=sys.modules['configuration'].wildcard, defaultFilter=0)
        self.browser.ShowHidden(1)
        tree = self.browser.GetTreeCtrl()
        tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate, tree)
        sizer.Add(self.browser, 1, wx.EXPAND)
        
        #create menu
        
        self.m = wx.Menu()
        np = wx.NewId()
        self.m.Append(np, "Add Selected Path")
        wx.EVT_MENU(self, np, self.OnNewPathmark)
        
        self.op = filehistory.FileHistory(self, callback=[self.chdir, self.browser.SetPath], seq=pathnames,maxlen=maxlen)
        self.rp = filehistory.FileHistory(self, remove=1, callback=[self.op.ItemRemove], seq=pathnames,maxlen=maxlen,
                                delmsg=('Are you sure you want to delete the pathmark?\n%s', "Delete Pathmark?"))
        self.op.callback.append(self.rp.ItemAdd)
        self.m.AppendMenu(wx.NewId(), "Choose Path", self.op)
        self.m.AppendSeparator()
        self.m.AppendMenu(wx.NewId(), "Remove Path", self.rp)
        
        self.sizer.Fit(self)
        self.SetSizer(self.sizer)
    
    def chdir(self, path):
        self.root.config.pop('lastpath', None)
        os.chdir(path)
    
    def gethier(self):
        p = self.browser.GetFilePath()
        ## print "Path:", p
        return p

    def OnActivate(self, evt):
        fn = self.gethier()
        try:
            st = os.stat(fn)[0]
            if stat.S_ISREG(st):
                self.root.OnDrop([fn])
        except:
            evt.Skip()
    
    def OnNewPathmark(self, evt):
        fn = self.gethier()
        try:
            st = os.stat(fn)[0]
            if stat.S_ISDIR(st):
                self.op.ItemAdd(fn)
                self.rp.ItemAdd(fn)
        except:
            evt.Skip()
    
    def OnButton(self, evt):
        self.PopupMenu(self.m, self.button.GetPositionTuple())
