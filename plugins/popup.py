
'''
This software is licensed under the GPL (GNU General Public License) version 2
as it appears here: http://www.gnu.org/copyleft/gpl.html
It is also included with this archive as `gpl.txt <gpl.txt>`_.
'''


import wx

#Popup window and location calculation in OnShowPopup borrowed from the
#wxPython demo
class Popup(wx.PopupWindow):
    def __init__(self, parent, text, style=wx.SIMPLE_BORDER, color=None):
        wx.PopupWindow.__init__(self, parent, style)
        if color:
            self.SetBackgroundColour(color)
        else:
            self.SetBackgroundColour("MEDIUM GOLDENROD")

        st = wx.StaticText(self, -1, text, pos=(10,10))

        sz = st.GetBestSize()
        self.SetSize( (sz.width+20, sz.height+20) )

        self.Bind(wx.EVT_LEFT_DOWN, self.OnMouseLeftDown)
        self.Bind(wx.EVT_MOTION, self.OnMouseMotion)
        self.Bind(wx.EVT_LEFT_UP, self.OnMouseLeftUp)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)

        st.Bind(wx.EVT_LEFT_DOWN, self.OnMouseLeftDown)
        st.Bind(wx.EVT_MOTION, self.OnMouseMotion)
        st.Bind(wx.EVT_LEFT_UP, self.OnMouseLeftUp)
        st.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)

        wx.CallAfter(self.Refresh)

    def OnMouseLeftDown(self, evt):
        self.Refresh()
        self.ldPos = evt.GetEventObject().ClientToScreen(evt.GetPosition())
        self.wPos = self.ClientToScreen((0,0))
        self.CaptureMouse()

    def OnMouseMotion(self, evt):
        if evt.Dragging() and evt.LeftIsDown():
            dPos = evt.GetEventObject().ClientToScreen(evt.GetPosition())
            nPos = (self.wPos.x + (dPos.x - self.ldPos.x),
                    self.wPos.y + (dPos.y - self.ldPos.y))
            self.Move(nPos)

    def OnMouseLeftUp(self, evt):
        self.ReleaseMouse()

    def OnRightUp(self, evt):
        self.Show(False)
        self.Destroy()
