
#site-packages imports
from wxPython.lib.mixins.listctrl import wxListCtrlAutoWidthMixin
import wx
from findinfiles import FoundTable

class vTodo(FoundTable, wxListCtrlAutoWidthMixin):
    def OnGetItemText(self, item, col):
        return "%s" % (self.data[item][col-1],)

columns = (
    (0, "", 0, 0),
    (1, "Category", 100, 0),
    (2, "Line", 60, wx.LIST_FORMAT_RIGHT),
    (3, "!", 50, wx.LIST_FORMAT_RIGHT),
    (4, "Todo", 550, 0))

class VirtualTodo(wx.Panel):
    
    def __init__(self, parent, root):
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)
        self.root = root
        tID = wx.NewId()

        self.vtd = vTodo(self, columns)
        
        wx.EVT_SIZE(self, self.OnSize)
        
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
    
    def OnSize(self, event):
        w,h = self.GetClientSizeTuple()
        self.vtd.SetDimensions(0, 0, w, h)
