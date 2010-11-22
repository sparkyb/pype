
import wx
import wx.lib.mixins.listctrl as listmix

#todo: add icon support

class pseudo_event(object):
    def __init__(self, index):
        self.index = index
    def GetIndex(self):
        return self.index

class hbrowser(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, containers, items):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_NO_HEADER|wx.LC_REPORT|wx.LC_ALIGN_LEFT|wx.LC_SINGLE_SEL)#|wx.LC_SMALL_ICON
        self.InsertColumn(0, 'unseen')
        listmix.ListCtrlAutoWidthMixin.__init__(self)
        self.parent = parent
        self.containers = {}
        self.items = {}
        for i,j in containers:
            x = self.InsertStringItem(2147483647, "[%s]"%i)
            self.containers[x] = i,j
        for i,j in items:
            x = self.InsertStringItem(2147483647, i)
            self.items[x] = i,j
        
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnSelected)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnActivated)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnClicked)
    
    def Back(self, which=None):
        if which is None:
            which = self.GetFirstSelected()
        self.OnSelected(pseudo_event(which))
    
    def OnClicked(self, e):
        index = self.HitTest(e.GetPosition())[0]
        if index == self.GetFirstSelected():
            self.Back()
        else:
            e.Skip()
    
    def OnSelected(self, e):
        it = e.GetIndex()
        if it in self.containers:
            name, token = self.containers[it]
            self.parent.ExpandChildren(self, token)
        else:
            self.parent.ClearChildren(self, dc=1)
    
    def OnActivated(self, e):
        it = e.GetIndex()
        if it in self.containers:
            name, token = self.containers[it]
            self.parent.ExpandChildren(self, token, dc=1)
        else:
            name, token = self.items[it]
            self.parent.ChildActivated(self, token)

class HorizontalBrowser(wx.Panel):
    def __init__(self, parent, get_children, on_activation):
        wx.Panel.__init__(self, parent)
        
        self.get_children = get_children
        self.on_activation = on_activation
        containers, items = get_children(None)
        self.lcs = [wx.Panel(self), wx.Panel(self), hbrowser(self, containers, items)]
        
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        for i in self.lcs:
            self.sizer.Add(i, 1, wx.ALL|wx.EXPAND, 2)
        
        othersizer = wx.BoxSizer(wx.HORIZONTAL)
        p = wx.Panel(self)
        btn = wx.Button(p, -1, "Back")
        othersizer.Add(p, 1, wx.ALL|wx.EXPAND, 2)
        othersizer.Add(wx.StaticText(self, -1, "Current"), 1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTER, 2)
        othersizer.Add(wx.StaticText(self, -1, "Forward"), 1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTER, 2)
        
        self.Bind(wx.EVT_BUTTON, self.OnBack, btn)
        
        sizer2 = wx.BoxSizer(wx.VERTICAL)
        sizer2.Add(othersizer, 0, wx.EXPAND)
        sizer2.Add(self.sizer, 1, wx.EXPAND)
        
        self.SetSizer(sizer2)
    
    def OnBack(self, e):
        if isinstance(self.lcs[-3], hbrowser):
            self.lcs[-3].Back()
    
    def ClearChildren(self, lc, dc=0):
        self.Freeze()
        while self.lcs[-1] != lc:
            popped = self.lcs.pop()
            self.sizer.Remove(popped)
            popped.Destroy()
        for i in xrange(min(3+dc, len(self.lcs))):
            self.lcs[-1-i].Hide()
        if dc:
            self.lcs.append(wx.Panel(self))
            self.sizer.Add(self.lcs[-1], 1, wx.ALL|wx.EXPAND, 2)
        for i in xrange(3):
            self.lcs[-1-i].Show()
        self.Layout()
        self.Thaw()
    
    def ExpandChildren(self, lc, token, dc=0):
        if dc:
            dc = lc == self.lcs[-2]
            print "dc:", dc
        self.ClearChildren(lc)
        self.Freeze()
        for i in xrange(3):
            self.lcs[-1-i].Hide()
        containers, items = self.get_children(token)
        self.lcs.append(hbrowser(self, containers, items))
        self.sizer.Add(self.lcs[-1], 1, wx.ALL|wx.EXPAND, 2)
        if dc:
            self.lcs.append(wx.Panel(self))
            self.sizer.Add(self.lcs[-1], 1, wx.ALL|wx.EXPAND, 2)
        for i in xrange(3):
            self.lcs[-1-i].Show()
        self.Layout()
        self.Thaw()
    
    def ChildActivated(self, lc, token):
        print token


if __name__ == '__main__':
    ## def get_children(token):
        ## if token is None:
            ## token = ()
        ## return [("<dir %s>"%(token+(i,),), token+(i,)) for i in xrange(5)], [("file_%s"%(token+(i,),), token+(i,)) for i in xrange(5)]
    
    import os, stat
    
    root = ["C:\\", "D:\\", "E:\\", "F:\\"]
    
    sfcn = lambda a,b: cmp(a[0].lower(), b[0].lower())
    
    def get_children(token):
        if token is None:
            return [(i,i) for i in root], []
        try:
            l = os.listdir(token)
        except:
            return [], []
        dire = []
        file = []
        for i in l:
            j = os.path.join(token, i)
            try:
                if stat.S_ISDIR(os.stat(j).st_mode):
                    dire.append((i,j))
                else:
                    file.append((i,j))
            except:
                pass
        
        dire.sort(sfcn)
        file.sort(sfcn)
        
        return dire, file
    
    def on_activation(token):
        pass
    
    a = wx.App(0)
    b = wx.Frame(None, title="spacial browser")
    c = HorizontalBrowser(b, get_children, on_activation)
    b.Show(1)
    b.SetSize((800,400))
    a.MainLoop()
