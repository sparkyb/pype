
import wx
import wx.lib.mixins.listctrl as listmix
import __main__ as _main

class KeySink(wx.Window):
    def __init__(self, parent, defa):
        wx.Window.__init__(self, parent, -1, style=wx.WANTS_CHARS)
        self.SetBackgroundColour(wx.BLUE)
        self.haveFocus = False
        self.parent = parent
        self.defa = defa

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouse)
        self.Bind(wx.EVT_KEY_DOWN, self.Detect)
        self.Bind(wx.EVT_CHAR, self.Show)
       
    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        rect = self.GetClientRect()
        dc.SetTextForeground(wx.WHITE)
        dc.DrawLabel(("Click here and type a key\n"
                      "(without the above modifiers)\n"
                      "Default: %s")%self.defa,
                      rect, wx.ALIGN_CENTER | wx.ALIGN_TOP)
        if self.haveFocus:
            dc.SetTextForeground(wx.GREEN)
            dc.DrawLabel("Have Focus", rect, wx.ALIGN_RIGHT | wx.ALIGN_BOTTOM)
        else:
            dc.SetTextForeground(wx.RED)
            dc.DrawLabel("Need Focus!", rect, wx.ALIGN_RIGHT | wx.ALIGN_BOTTOM)

    def OnSetFocus(self, evt):
        self.haveFocus = True
        self.Refresh()

    def OnKillFocus(self, evt):
        self.haveFocus = False
        self.Refresh()

    def OnMouse(self, evt):
        if evt.ButtonDown():
            self.SetFocus()
    
    def Detect(self, evt):
        self.parent.pressed = _main.GetKeyPress(evt)
        self.parent.update()
        evt.Skip()
    def Show(self, evt):
        self.parent.character = _main.GetKeyPress(evt)
        self.parent.update()

class GetKeyDialog(wx.Dialog):
    def __init__(self, parent, defa, curr, currk=''):
        wx.Dialog.__init__(self, parent, -1, "Define your hotkey",
                          style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER,
                          size=(320, 240))
        
        self.parent = parent
        
        self.curr = curr
        self.currk = currk or curr
        
        self.pressed = self.curr
        self.character = self.currk
        
        self.event = self.pressed
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, -1, "Step 1:"), 0, wx.ALIGN_CENTER|wx.ALL, 3)
        for i in 'ctrl alt shift meta'.split():
            it = i.title()
            x = wx.CheckBox(self, -1, it)
            if (it + '+') in curr:
                x.SetValue(1)
            self.Bind(wx.EVT_CHECKBOX, self.OnChecked, x)
            setattr(self, i, x)
            row.Add(x, 1, wx.GROW|wx.ALL, 3)
        sizer.Add(row)
        
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, -1, "Step 2:"), 0, wx.ALIGN_CENTER|wx.ALL, 3)
        self.keysink = KeySink(self, defa)
        row.Add(self.keysink, 1, wx.GROW|wx.ALL, 3)
        sizer.Add(row, 1, wx.GROW)
        
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, -1, "Verify:"), 0, wx.ALIGN_CENTER|wx.ALL, 3)
        self.text = wx.TextCtrl(self, -1, curr, style=wx.TE_READONLY|wx.TE_LEFT)
        row.Add(self.text, 1, wx.GROW|wx.ALL, 3)
        sizer.Add(row, 0, wx.GROW)
        
        row = wx.BoxSizer(wx.HORIZONTAL)
        ok = wx.Button(self, -1, "Ok")
        cancel = wx.Button(self, -1, "Cancel")
        row.Add(ok, 0, wx.ALL, 3)
        row.Add(cancel, 0, wx.ALL, 3)
        sizer.Add(row, 0, wx.ALIGN_RIGHT)
        
        self.Bind(wx.EVT_BUTTON, self.OnOk, ok)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, cancel)
        
        self.SetSizer(sizer)
    
    def OnChecked(self, e):
        self.update()

    def update(self):
        for (p, ctrl) in ((self.pressed, 0), (self.character, 1)):
            if p == '+':
                k = p
            elif p.endswith('++'):
                k = '+'
            else:
                k = p.split('+')[-1]
                if len(k) == 1:
                    k = k.upper()
            
            key = ''
            for i in 'ctrl alt shift meta'.split():
                if not ctrl and (i.title() + '+') in p:
                    getattr(self, i).SetValue(1)
                if getattr(self, i).GetValue():
                    key += i.title() + '+'
            
            if not ctrl:
                self.pressed = k
            
            key += k
            
            if ctrl:
                self.text.SetValue(key)
            else:
                self.event = key
    
    def OnOk(self, evt):
        self.parent.accelerator = self.event
        self.parent.acceleratork = self.text.GetValue()
        self.Destroy()
    
    def OnCancel(self, evt):
        self.parent.accelerator = self.curr
        self.parent.acceleratork = self.currk
        self.Destroy()
    

class HotkeyList(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1,
                            style=wx.LC_REPORT|wx.LC_VIRTUAL|wx.LC_HRULES|wx.LC_VRULES|wx.LC_SINGLE_SEL)
        listmix.ListCtrlAutoWidthMixin.__init__(self)
        self.parent = parent
        self.sel = None
        self.col = None

        self.InsertColumn(0, "Default Menu Hierarchy")
        self.InsertColumn(1, "Current Name")
        self.InsertColumn(2, "Default Hotkey")
        self.InsertColumn(3, "Current Hotkey")
        self.SetColumnWidth(0, 250)
        self.SetColumnWidth(1, 150)
        self.SetColumnWidth(2, 100)

        self.items = []
        self.SetItemCount(0)

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnClick)
    
    def OnClick(self, event):
        if event.GetX() <= self.GetColumnWidth(0) + self.GetColumnWidth(1):
            self.col = 0
        else:
            self.col = 1
        event.Skip()

    def OnItemActivated(self, event):
        inum = event.GetIndex()
        item = self.items[inum]
        
        if self.col != 1:
            dlg = wx.TextEntryDialog(self,
                "Enter the new name of the menu item\n"\
                "Default: %s  Current: %s"%(item[0].split('->')[-1], item[1]),\
                "What should the item be called?")
            dlg.SetValue(item[1])
            rslt = dlg.ShowModal()
            name = None
            if rslt == wx.ID_OK:
                name = dlg.GetValue()
            dlg.Destroy()
            if not name:
                return
            if item[0].find('->') == -1 or not item[4]:
                self.items[inum] = (item[0], name, '', '', 0, '')
                return self.RefreshItem(inum)
            item = (item[0], name) + item[2:]
        if self.col != 0:
            item5 = item[3]
            if len(item) == 6:
                item5 = item[5]
            else:
                item5 = item[4]
            dlg = GetKeyDialog(self, item[2], item[3], item5)
            dlg.ShowModal()
            #dlg.Destroy() #this dialog destroys itself.
            item = item[:3] + (self.accelerator, 1, self.acceleratork)
        
        self.items[inum] = item
        self.RefreshItem(inum)

    def getColumnText(self, index, col):
        return self.items[index][col]

    def OnGetItemText(self, item, col):
        return self.items[item][col]

    def OnGetItemImage(self, item):
        return -1

    def OnGetItemAttr(self, item):
        return None

    def OnItemSelected(self, evt):
        self.sel = evt.GetIndex()

class HotkeyListPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)
        self.vm = HotkeyList(self)
        self.refresh(_main.MENULIST)
        
        self.parent = parent

        self.Bind(wx.EVT_SIZE, self.OnSize)

    def refresh(self, items):
        self.vm.items = []
        self.vm.SetItemCount(0)
        self.vm.items = items
        self.vm.SetItemCount(len(items))
        if self.vm.sel is not None:
            self.vm.EnsureVisible(self.vm.sel)

    def OnSize(self, event):
        w,h = self.GetClientSizeTuple()
        self.vm.SetDimensions(0, 0, w, h)

class MenuItemDialog(wx.Dialog):
    def __init__(self, parent, root):
        wx.Dialog.__init__(self, parent, -1, "Menu item names and hotkey bindings.",
                          size=(640,480), style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)

        self.root = root
        self.vmu = HotkeyListPanel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(self, -1,
                               "Double click on a name to change the name, and the hotkey to change the hotkey.  Most hotkeys should work fine.\n"
                               "Name changes with accelerators should work fine, as long as there are no accelerator key collisions."))
        sizer.Add(self.vmu, 1, wx.GROW)

        s2 = wx.BoxSizer(wx.HORIZONTAL)

        ok = wx.Button(self, wx.OK, "OK")
        clear = wx.Button(self, -1, "Clear Hotkey")
        revert = wx.Button(self, -1, "Revert Name and Hotkey")
        cancel = wx.Button(self, wx.CANCEL, "Cancel")

        s2.Add(ok)
        s2.Add(clear)
        s2.Add(revert)
        s2.Add(cancel)
        sizer.Add(s2, 0, wx.ALIGN_RIGHT)

        self.SetSizer(sizer)
        self.SetAutoLayout(True)

        self.Bind(wx.EVT_BUTTON, self.OnOK, ok)
        self.Bind(wx.EVT_BUTTON, self.OnClear, clear)
        self.Bind(wx.EVT_BUTTON, self.OnRevert, revert)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, cancel)

    def OnOK(self, evt):
        MENUPREF = _main.MENUPREF
        MENULIST = _main.MENULIST
        nmu = {}
        changed = 0
        for X in self.vmu.vm.items:
            if len(X) == 5:
                hier, cn, da, ca, hk = X
                kk = ca
            else:
                hier, cn, da, ca, hk, kk = X
            if MENUPREF[hier] != (cn, ca, kk):
                changed = 1
            nmu[hier] = (cn, ca, kk)
        if changed:
            MENUPREF.clear()
            MENUPREF.update(nmu)
            MENULIST[:] = self.vmu.vm.items
            self.root.dialog("You must restart in order for your\n"
                             "menu item changes to go into effect.",
                             "Restart Required")
        self.Destroy()

    def OnClear(self, evt):
        IL = self.vmu.vm
        items = IL.items
        indx = IL.sel
        items[indx] = items[indx][:3] + ('', items[indx][4], '')
        IL.RefreshItem(indx)

    def OnRevert(self, evt):
        IL = self.vmu.vm
        items = IL.items
        indx = IL.sel
        item = items[indx]
        items[indx] = (item[0], item[0].split('->')[-1], item[2], item[2], item[4], item[2])
        IL.RefreshItem(indx)

    def OnCancel(self, evt):
        self.Destroy()
