
'''
This software is licensed under the GPL (GNU General Public License) version 2
as it appears here: http://www.gnu.org/copyleft/gpl.html
It is also included with this archive as `gpl.txt <gpl.txt>`_.
'''


import wx

class TextRepr(wx.Panel):
    def __init__(self, parent, root):
        wx.Panel.__init__(self, parent, -1)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, -1, "Enter your text here:"))
        self.inp = wx.TextCtrl(self, -1, style=wx.TE_PROCESS_TAB|wx.TE_MULTILINE|wx.TE_RICH2)
        sizer.Add(self.inp, 1, wx.TOP|wx.EXPAND, 5)
        sizer.Add(wx.StaticText(self, -1, "Python repr() of that text (including quotes, u prefix, etc.):"), 0, wx.TOP, 5)
        self.out = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE|wx.TE_RICH2|wx.TE_READONLY)
        sizer.Add(self.out, 1, wx.TOP|wx.EXPAND, 5)
        
        self.inp.Bind(wx.EVT_TEXT, self.OnChar)
        
        self.SetSizer(sizer)
        self.SetAutoLayout(True)
    
    def OnChar(self, e):
        txt = self.inp.GetValue()
        try:
            txt = str(txt)
        except:
            pass
        self.out.SetValue(repr(txt))
