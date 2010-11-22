
#site-packages imports
import wx

#local imports
from findinfiles import FoundTable

class vTodo(FoundTable):
    if 1:
        _col = 0
    def OnGetItemText(self, item, col):
        return "%s" % (self.data[item][col],)
    
    def SortItems(self, *args, **kwargs):
        # Override listctrl mixin
        col=self._col
        ascending = self._colSortFlag[col]
        
        if ascending:
            fcn = lambda a,b:cmp(a[col], b[col])
        else:
            fcn = lambda a,b:-cmp(a[col], b[col])
        
        self.data.sort(fcn)
        self.Refresh()
    
    def setData(self, data, copy=1, sort=0):
        FoundTable.setData(self, data, copy=copy)
        if sort:
            self.SortItems()

columns = (
    (0, "Category", 100, 0),
    (1, "Line", 60, wx.LIST_FORMAT_RIGHT),
    (2, "!", 25, wx.LIST_FORMAT_RIGHT),
    (3, "Todo", 5, 0)
)

option = 1

class VirtualTodo(wx.Panel):
    def __init__(self, parent, root):
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)
        self.root = root
        self.parent = parent
        
        self.cb = wx.CheckBox(self, -1, "Include Tags")
        
        self.data = []
        
        self.vtd = vTodo(self, columns)
        
        self.vtd.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        self.cb.Bind(wx.EVT_CHECKBOX, self.OnCheck)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.cb, 0, wx.EXPAND|wx.ALL|wx.ALIGN_CENTRE, 5)
        sizer.Add(self.vtd, 1, wx.EXPAND)
        self.SetSizer(sizer)
        
    def NewItemList(self, items, sort=0):
        self.data = items
        if not self.cb.GetValue():
            self.vtd.setData([i for i in items if i[0] != 'tags'], copy=0, sort=sort)
        else:
            self.vtd.setData(items, copy=0, sort=sort)
    
    def OnItemActivated(self, event):
        num, win = self.root.getNumWin(event)
        sel = self.vtd.data[event.m_itemIndex][1]
        if sel < win.GetLineCount():
            sel -= 1
            linepos = win.GetLineEndPosition(sel)
            win.EnsureVisible(sel)
            win.SetSelection(linepos-len(win.GetLine(sel))+len(win.format), linepos)
            win.ScrollToColumn(0)
    
    def OnCheck(self, e):
        global option
        self.Freeze()
        option = self.cb.GetValue()
        self.NewItemList(self.data, 1)
        self.Thaw()
        e.Skip()
    
    def Show(self):
        self.Freeze()
        self.cb.SetValue(option)
        self.NewItemList(self.data)
        self.Thaw()
        wx.Panel.Show(self)
    