
import re
import wx
import todo

rexp = re.compile('[^0-9a-z]')

columns = ((0, "definition", 100, 0),)

## options = 1

def partition(st, sep):
    if sep not in st:
        return st, '', ''
    i = st.find(sep)
    return st[:i], sep, st[i+len(sep):]

class TagManager(wx.Panel):
    def __init__(self, parent, stc):
        wx.Panel.__init__(self, parent, -1)
        self.parent = parent
        self.stc = stc
        
        self.definitions = {}
        self.selected = None, (None, [])
        
        #define controls
        ## self.tb = wx.CheckBox(self, -1, "Tag above definition")
        self.defs = todo.vTodo(self, columns)
        self.tagtc = wx.TextCtrl(self)
        self.tagbtn = wx.Button(self, -1, "+", size=(16,16))
        self.tags = wx.CheckListBox(self, -1, choices=[])
        
        #define events
        ## self.tb.Bind(wx.EVT_CHECKBOX, self.OnCheck)
        self.defs.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnDefnClicked)
        self.tagbtn.Bind(wx.EVT_BUTTON, self.OnAddButton)
        self.tags.Bind(wx.EVT_CHECKLISTBOX, self.OnTagToggle)
        
        #define layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        ## sizer.Add(self.tb, 0, wx.ALL, 3)
        sizer.Add(self.defs, 1, wx.ALL|wx.EXPAND, 3)
        
        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer2.Add(self.tagtc, 1, wx.ALL|wx.EXPAND, 3)
        sizer2.Add(self.tagbtn, 0, wx.ALL|wx.EXPAND, 3)
        
        sizer.Add(sizer2, 0, wx.EXPAND)
        sizer.Add(self.tags, 1, wx.ALL|wx.EXPAND, 3)
        
        self.SetSizer(sizer)
        
    def Show(self):
        ## self.tb.SetValue(options)
        wx.Panel.Show(self)
    
    def OnCheck(self, e):
        ## global options
        ## options = self.tb.GetValue()
        pass
    
    def OnDefnClicked(self, e):
        itemn = e.GetIndex()
        defn = self.defs.data[itemn][0]
        self.selected = defn, self.definitions[defn]
        self._check(self.selected[1][1])
        self.stc.GotoLineS(self.selected[1][0])
    
    def _check(self, names):
        n = dict.fromkeys(names)
        for i in xrange(self.tags.GetCount()):
            if self.tags.GetString(i) in n:
                self.tags.Check(i, 1)
            else:
                self.tags.Check(i, 0)
    
    def _get_checks(self):
        r = []
        for i in xrange(self.tags.GetCount()):
            if self.tags.IsChecked(i):
                r.append(self.tags.GetString(i))
        return r
    
    def newTags(self, tags):
        self.Freeze()
        #tags[name] -> {line:defn, line:defn, ...}
        
        #want to get defn -> (line, [name, name, ...])
        
        dfns = {}
        listc = []
        
        for name, dct in tags.iteritems():
            for line, defn in dct.iteritems():
                if defn not in dfns:
                    dfns[defn] = (line, [])
                    listc.append((line, defn))
                if name:
                    dfns[defn][1].append(name)
        
        listc.sort()
        listc = [(j,) for i,j in listc]
        self.defs.setData(listc, copy=0)
        
        for i in tags:
            self._add_possible_tag(i)
        
        self.definitions = dfns
        if self.selected[0] in dfns:
            self.selected = self.selected[0], dfns[self.selected[0]]
            self._check(self.selected[1][1])
            self.defs.Select(listc.index((self.selected[0],)), 1)
        else:
            self.selected = None, (None, [])
            self._check(())
        
        self.Thaw()
        
    def _add_possible_tag(self, tag):
        if not tag:
            return
        for i in xrange(self.tags.GetCount()):
            s = self.tags.GetString(i)
            if tag < s:
                self.tags.Insert(tag, i)
                break
            elif tag == s:
                break
        else:
            self.tags.Append(tag)
    
    def OnAddButton(self, e):
        x = self.tagtc.GetValue().lower()
        self.tagtc.SetValue('')
        x = rexp.sub(' ', x).replace(' ', '')
        if not x:
            return
        self._add_possible_tag(x)
    
    def OnTagToggle(self, e):
        if self.selected[0] is None:
            return
        tags = self._get_checks()
        if not tags:
            new_tag = '\n'
        else:
            #get language prefix
            new_tag = ' # tags: %s\n'%(', '.join(tags),)
        lines = self.stc.lines
        line = self.selected[1][0] - 1
        lead, sep, tail = partition(lines[line].rstrip('\r\n'), '# tags: ')
        lines[line] = lead.rstrip() + new_tag
