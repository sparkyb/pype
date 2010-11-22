
import wx
from findinfiles import FoundTable
import todo

columns = (
    (0, "", 0, 0),
    (1, "Hierarchy", 75, 0),
    (2, "Definition", 20, 0),
    )

class filtertable(todo.vTodo):
    def OnGetItemText(self, item, col):
        if col == 0:
            return ""
        elif col == 1:
            return '%s'%(self.data[item][2],)
        else:
            return '%s'%(self.data[item][0],)

## blue = wx.Colour(0, 0, 200)
## red = wx.Colour(200, 0, 0)
## green = wx.Colour(0, 200, 0)
## D = {'cl':blue,
     ## 'de':red,
     ## 'cd':green,
     ## '\\l':red,
     ## '\\s':blue}

def partition(str, sep):
    if sep not in str:
        return str, '', ''
    x = str.find(sep)
    return str[:x], sep, str[x+len(sep):]

class DefinitionList(wx.Panel):
    def __init__(self, parent, root):
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)
        self.root = root
        self.parent = parent
        
        sizer = wx.BoxSizer(wx.VERTICAL)
            
        self.filter = wx.TextCtrl(self, -1, "")
        sizer.Add(self.filter, 0, wx.EXPAND|wx.ALL, 3)
        
        if 1:
            s2 = wx.BoxSizer(wx.HORIZONTAL)
            
            self.cs = wx.CheckBox(self, -1, "Case Sensitive")
            s2.Add(self.cs, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
            
            self.how = wx.ComboBox(self, -1, "exact", choices=["exact", "any", "all"], style=wx.CB_READONLY)
            s2.Add(self.how, 1, wx.EXPAND)
        sizer.Add(s2, 0, wx.EXPAND|wx.ALL, 3)
        
        self.cmdlist = filtertable(self, columns)
        sizer.Add(self.cmdlist, 1, wx.EXPAND|wx.ALL, 3)
        
        self.SetSizer(sizer)
        
        self.Bind(wx.EVT_TEXT, self.OnText)
        self.Bind(wx.EVT_CHECKBOX, self.OnText)
        self.Bind(wx.EVT_COMBOBOX, self.OnText)
        self.cmdlist.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        
    def new_hierarchy(self, hier):
        #parse the hierarchy, set the data
        names = []
        stk = [hier[::-1]]
        nstk = []
        while stk:
            cur = stk.pop()
            if cur is None:
                _ = nstk.pop()
                continue
            
            while cur:
                name, line_no, leading, children = cur.pop()
                shortname = name.split(None, 1)[-1]
                shortname = partition(partition(shortname, ':')[0], '(')[0]
                
                names.append((name, line_no, '.'.join(nstk+[shortname])))
                
                if children:
                    stk.append(cur)
                    nstk.append(shortname)
                    stk.append(None)
                    cur = children[::-1]
        self.names = names
        self.update()
    
    def OnText(self, e):
        self.update()
        e.Skip()
    
    def update(self):
        txt = self.filter.GetValue()
        
        lower = not self.cs.GetValue()
        if lower:
            txt = txt.lower()
        
        if not txt.strip():
            names = self.names
        else:
            if self.how.GetValue() == 'exact':
                if lower:
                    names = [i for i in self.names if txt in i[0].lower()]
                else:
                    names = [i for i in self.names if txt in i[0]]
            else:
                names = []
                txt = txt.split()
                
                all = self.how.GetValue() == 'all'
                any = self.how.GetValue() == 'any'
    
                for i in self.names:
                    it = i[0]
                    if lower:
                        it = it.lower()
                    for j in txt:
                        if j not in it:
                            if all:
                                break
                        elif any:
                            names.append(i)
                            break
                    else:
                        if all:
                            names.append(i)
        
        self.cmdlist.setData(names, copy=0)
        #colors don't seem to work
        ## colors = D
        ## for i,j in enumerate(names):
            ## self.cmdlist.GetItem(i).SetTextColour(colors.get(j[0][:2], blue))
    
    def OnItemActivated(self, event):
        num, win = self.root.getNumWin(event)
        sel = self.cmdlist.data[event.m_itemIndex][1][1]
        if sel < win.GetLineCount():
            sel -= 1
            linepos = win.GetLineEndPosition(sel)
            win.EnsureVisible(sel)
            win.SetSelection(linepos-len(win.GetLine(sel))+len(win.format), linepos)
            win.ScrollToColumn(0)
