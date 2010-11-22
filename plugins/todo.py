
#site-packages imports
import wx

#local imports
from findinfiles import FoundTable

class vTodo(FoundTable):
    def OnGetItemText(self, item, col):
        return "%s" % (self.data[item][col],)


columns = (
    (0, "Category", 100, 0),
    (1, "Line", 60, wx.LIST_FORMAT_RIGHT),
    (2, "!", 25, wx.LIST_FORMAT_RIGHT),
    (3, "Todo", 5, 0)
)

class VirtualTodo(wx.Panel):
    def __init__(self, parent, root):
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)
        self.root = root
        self.parent = parent
        self.vtd = vTodo(self, columns)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.vtd, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.vtd.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        
    def NewItemList(self, items):
        self.vtd.setData(items, copy=0)
    
    def OnItemActivated(self, event):
        num, win = self.root.getNumWin(event)
        sel = self.vtd.data[event.m_itemIndex][1]
        if sel < win.GetLineCount():
            sel -= 1
            linepos = win.GetLineEndPosition(sel)
            win.EnsureVisible(sel)
            win.SetSelection(linepos-len(win.GetLine(sel))+len(win.format), linepos)
            win.ScrollToColumn(0)
  