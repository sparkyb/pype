
import wx

class ListSelect(object):
    def __init__(self, tc=None, noctrl=0):
        if tc:
            tc.Bind(wx.EVT_CHAR, self.OnChar)
        self.__noctrl = noctrl

    def OnChar(self, e):
        key = e.GetKeyCode()
        up = key in (wx.WXK_UP, wx.WXK_NUMPAD_UP)
        down = key in (wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN)
        if (up or down) and ((self.__noctrl and not e.ControlDown()) or e.ControlDown()):
            self._select(down)
        elif key == wx.WXK_NUMPAD_ENTER or (e.AltDown() and key == wx.WXK_RETURN):
            if self.GetFirstSelected() == -1:
                self.SelectNext()
            wx.PostEvent(self, wx.ListEvent(wx.wxEVT_COMMAND_LIST_ITEM_ACTIVATED, self.GetId()))
        else:
            e.Skip()
    
    def _select(self, dire):
        down = dire == 1
        ls = self.GetItemCount()-1
        if ls == -1:
            return
        cs = self.GetFirstSelected()
        if cs == -1:
            if down:
                cs = 0
            else:
                cs = ls
        else:
            self.Select(cs, 0)
            if down:
                cs = min(cs + 1, ls)
            else:
                cs = max(cs - 1, 0)
        self.Select(cs)
        self.EnsureVisible(cs)
    
    def SelectNext(self):
        self._select(1)
        
    def SelectPrev(self):
        self._select(-1)
