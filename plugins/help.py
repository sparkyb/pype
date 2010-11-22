
import wx
import wx.html as html
import sys
import os
import webbrowser

a = _pype.runpath + '/readme.html'

class MyHtmlWindow(html.HtmlWindow):
    def __init__(self, parent):
        html.HtmlWindow.__init__(self, parent,
            style=wx.NO_FULL_REPAINT_ON_RESIZE|wx.SUNKEN_BORDER)
        if "gtk2" in wx.PlatformInfo:
            self.SetStandardFonts()
        wx.CallAfter(self.LoadPage, a)
        
    def OnLinkClicked(self, link):
        a = link.GetHref()
        if a.startswith('#'):
            self.base_OnLinkClicked(link)
        else:
            webbrowser.open(a)
    
    def LoadPage(self, fn):
        self.SetPage(open(fn).read().replace('; charset=utf-8', ''))

class HtmlHelpDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title="PyPE Help",
            style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        
        w, h = parent.GetSizeTuple()
        self.SetSize((3*w//4, 3*h//4))
        self.CentreOnParent()
        
        p = self
        s = wx.BoxSizer(wx.VERTICAL)
        
        self.html = MyHtmlWindow(p)
        
        s.Add(self.html, 1, wx.EXPAND|wx.ALL, 5)
        
        s2 = wx.BoxSizer(wx.HORIZONTAL)
        s2.Add(wx.StaticText(p, -1, ""), 1, wx.EXPAND)
        s2.Add(wx.Button(p, wx.ID_OK, "OK"), 0, wx.EXPAND)
        s2.Add(wx.StaticText(p, -1, ""), 1, wx.EXPAND)
        
        s.Add(s2, 0, wx.EXPAND|wx.ALL, 5)
        
        p.SetSizer(s)
        p.SetAutoLayout(1)
        p.Layout()
