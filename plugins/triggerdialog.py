
import wx
import wx.lib.mixins.listctrl as listmix

class Editable(wx.ListCtrl, listmix.TextEditMixin):
    def __init__(self, parent, id, style):
        wx.ListCtrl.__init__(self, parent, id, style=style)
        listmix.TextEditMixin.__init__(self)

class TriggerDialog(wx.Dialog):
    def __init__(self, parent, stc, dct):
        wx.Dialog.__init__(self, parent, -1, "Set your Triggers",
                          style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER,
                          size=(800, 400))
        self.stc = stc
        self.parent = parent
        self.dct = dct
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        
        def addbutton(sizer, name, fcn, id):
            it = wx.Button(self, id, name)
            sizer.Add(it, 0, wx.RIGHT, border=5)
            self.Bind(wx.EVT_BUTTON, fcn, it)
        
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        #description/help text
        sizer.Add(wx.StaticText(self, -1, '''\
                                When editing a document, any time you type the string in the 'enter' column,
                                the string in the 'left' column replaces it, and the string in the 'right'
                                column is inserted to the right of the cursor.
                                
                                See the help for example uses.
                                
                                One may want to use such functionality for single or double quotes: '', ""
                                parens or square/curly/pointy braces: (), [], {}, <>
                                or even html tag expansion: ahref->"<a href='http://", "'></a>"
                                
                                Double-click to edit an entry in-place.
                                
                                If one entry in the 'enter' column is a suffix of another, the suffix item
                                will be removed.  Watch the log for such entries.
                                
                                NOTE: If any of your entries begins with a single or double quote, and is a
                                valid Python string definition, then it will be interpreted as the string
                                defined (allowing for escaped tabs, line endings, unicode characters, etc.).'''.replace(32*' ', '')
                               ), 0, wx.LEFT|wx.RIGHT, border=5)
        
        #wx.ListCtrl with editor
        self.list = Editable(self, -1, style=wx.LC_REPORT|wx.BORDER_NONE)
        self.list.InsertColumn(0, "enter");self.list.SetColumnWidth(0, 160)
        self.list.InsertColumn(1, "left");self.list.SetColumnWidth(1, 80)
        self.list.InsertColumn(2, "right");self.list.SetColumnWidth(2, 80)
        self.ResetData(dct)
        
        sizer.Add(self.list, 2, flag=wx.GROW|wx.ALL, border=5)
        
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        #new/delete
        addbutton(buttons, "New Trigger", self.OnNew, wx.NewId())
        addbutton(buttons, "Delete Trigger", self.OnDelete, wx.NewId())
        buttons.Add(wx.StaticText(self, -1, '     '), 1, wx.GROW)
        #OK/cancel
        addbutton(buttons, "OK", self.OnOK, wx.OK)
        addbutton(buttons, "Cancel", self.OnCancel, wx.CANCEL)
        sizer.Add(buttons, 0, wx.ALIGN_CENTER|wx.LEFT, border=5)
        
        sizer.Fit(self)
        self.SetSizer(sizer)

    def ResetData(self, data):
        def reconstruct(suf, x):
            if type(x) is tuple:
                yield suf, x[0], x[1]
            elif type(x) is dict:
                for key,value in x.iteritems():
                    for i,j,k in reconstruct(key+suf, value):
                        yield i,j,k
        
        self.list.DeleteAllItems()
        for x in reconstruct('', data):
            x_ = []
            for L in x:
                try:
                    L = str(L)
                except:
                    pass
                if not isinstance(L, unicode):
                    Lx = L.encode('string-escape')
                    if Lx != L:
                        L = repr(L)
                x_.append(L)
            i,j,k = x_
            indx = self.list.InsertStringItem(65536, 'X')
            self.list.SetStringItem(indx, 0, i)
            self.list.SetStringItem(indx, 1, j)
            self.list.SetStringItem(indx, 2, k)

    def OnNew(self, evt):
        index = self.list.InsertStringItem(65536, 'X')
        self.list.SetStringItem(index, 0, 'X')
        self.list.SetStringItem(index, 1, 'X')
        self.list.SetStringItem(index, 2, 'X')

    def OnDelete(self, evt):
        selected = self.list.GetNextItem(-1, state=wx.LIST_STATE_SELECTED)
        if selected != -1:
            self.list.DeleteItem(selected)

    def OnClose(self, evt):
        self.OnCancel(evt)

    def OnOK(self, evt):
        d = {}
        for row in xrange(self.list.GetItemCount()):
            #handle string escapes
            item = [self.list.GetItem(row, 0).GetText(),
                    self.list.GetItem(row, 1).GetText(),
                    self.list.GetItem(row, 2).GetText()]
            item_ = []
            for i in item:
                if i and i[0] in ['"', "'"]:
                    try:
                        i = [j for j in compiler.parse(str(i)).getChildren()[:1] if isinstance(j, basestring)][0]
                    except Exception, e:
                        pass
                item_.append(i)
            
            p, l, r = item_
            
            if not p:
                if len(l) or len(r):
                    print "null trigger has nonnull replacements (%r, %r)"%(l,r)
                continue
            if len(l) + len(r) == 0:
                print "nonnull trigger %r has null replacements"%p
            pr = None
            x = d
            good = 1
            for le,ch in enumerate(p[::-1]):
                n = x.get(ch, None)
                if type(n) is tuple:
                    if p[-le-1:] == p:
                        print "duplicate trigger %r with replacements (%r, %r), and is now removed"%(p, l, r)
                        break
                    print "trigger %r with replacements (%r, %r) is a suffix of %r, and is now removed"%(p[-le-1:], n[0], n[1], p)
                    n = None
                
                if n is None:
                    n = x[ch] = {}
                
                pr, x = x, n
            else:
                if len(x) != 0:
                    print "trigger %r with replacements (%r, %r) is a suffix of some entry, and is now removed"%(p, l, r)
                    continue
                pr[p[0]] = (l,r)
        
        self.stc.triggers = d
        self.Destroy()

    def OnCancel(self, evt):
        self.Destroy()
