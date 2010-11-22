
import wx
from findinfiles import FoundTable
import mylistmix
import todo
import __main__

columns = (
    (0, "Lines", 50, wx.LIST_FORMAT_RIGHT),
    (1, "Definition", 20, 0),
    )

context = 'no context'
options = None


#colors
if 1:
    blue = wx.Colour(0, 0, 200)
    red = wx.Colour(200, 0, 0)
    green = wx.Colour(0, 200, 0)
    D = {'cl':blue,
         'de':red,
         'cd':green,
         '\\l':red,
         '\\s':blue}
    
    for i,j in D.items():
        k = wx.ListItemAttr()
        k.SetTextColour(j)
        D[i] = k
    
    default = D['de']
    
    del i, j, k, blue, red, green

def lcsseq(x, y):
    _enum = enumerate
    _max = max
    z = {}
    zg = z.get
    for i, xi in _enum(x):
        for j, yj in _enum(y):
            k = zg((i-1,j), 0)
            l = zg((i,j-1), 0)
            if l > k:
                k = l
            if xi == yj:
                l = zg((i-1,j-1), 0)+1
                if l > k:
                    k = l
            z[i,j] = k
    
    return z[i,j]

class filtertable(todo.vTodo, mylistmix.ListSelect):
    def OnGetItemText(self, item, col):
        if col == 1:
            if context == 'short':
                return '%s'%(self.data[item][3],)
            elif context == 'long':
                return '%s'%(self.data[item][4],)
            else:
                return '%s'%(self.data[item][0],)
        else:
            return '%s'%(self.data[item][5],)
    def OnGetItemAttr(self, item):
        return D.get(self.data[item][0][:2], default)
    def SortItems(self, *args, **kwargs):
        # Override listctrl mixin
        col=self._col
        ascending = self._colSortFlag[col]
        
        if col == 0:
            col = 5
        else:
            if context == 'short':
                col = 3
            elif context == 'long':
                col = 4
            else:
                col = 0
        
        _cmp = cmp
        cmpf = lambda a,b: _cmp(a[col],b[col])
        
        if ascending:
            self.data.sort(cmpf)
        else:
            self.data.reverse()
        
        self.Refresh()

def partition(str, sep):
    if sep not in str:
        return str, '', ''
    x = str.find(sep)
    return str[:x], sep, str[x+len(sep):]

def rstr1(str, rch):
    if rch and str.endswith(rch):
        return str[:-len(rch)]
    return str

def get_line_counts(h, lang):
    if lang != 'python':
        return {}
    #need implementation for C/C++, but only after parser for C/C++ is done
    
    counts = {}
    stk = [h[::-1]]
    nstk = []
    lastl = 0
    lastn = ''
    while stk:
        cur = stk.pop()
        if cur is None:
            _ = nstk.pop()
            continue
        
        while cur:
            name, line_no, leading, children = cur.pop()
            pre, shortname1 = name.split(None, 1)
            shortname = partition(partition(shortname1, ':')[0], '(')[0]
            key = '%s%s%s'%('.'.join(nstk), '.'[:bool(nstk)], shortname)
            
            if lastn:
                counts.setdefault(lastn, []).append(line_no[1]-lastl)
            
            lastn = key
            lastl = line_no[1]
            
            if children:
                stk.append(cur)
                nstk.append(shortname)
                stk.append(None)
                cur = children[::-1]
    
    if lastn:
        try:
            counts.setdefault(lastn, []).append(
                __main__.root.control.GetCurrentPage().GetWindow1().GetLineCount()+1-lastl)
        except:
            pass
    
    return counts
    

class DefinitionList(wx.Panel):
    def __init__(self, parent, root, stc):
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)
        self.root = root
        self.parent = parent
        self.stc = stc
        self.names = []
        sizer = wx.BoxSizer(wx.VERTICAL)
            
        self.filter = wx.TextCtrl(self, -1, "", style=wx.TE_PROCESS_ENTER|wx.WANTS_CHARS)
        sizer.Add(self.filter, 0, wx.EXPAND|wx.ALL, 3)
        
        self.cs = wx.CheckBox(self, -1, "Case Sensitive")
        self.lcs = wx.CheckBox(self, -1, "Subsequence")
        
        s2 = wx.BoxSizer(wx.HORIZONTAL)
        s2.Add(self.cs, 0, wx.EXPAND|wx.ALL, 3)
        s2.Add(self.lcs, 0, wx.EXPAND|wx.ALL, 3)
        
        sizer.Add(s2, 0, wx.EXPAND)
        
        s2 = wx.BoxSizer(wx.HORIZONTAL)
        self.context = wx.ComboBox(self, -1, "no context", choices=["no context", "long", "short"], style=wx.CB_READONLY)
        s2.Add(self.context, 1, wx.EXPAND|wx.ALL, 3)
        
        self.how = wx.ComboBox(self, -1, "exact", choices=["exact", "any", "all"], style=wx.CB_READONLY)
        s2.Add(self.how, 1, wx.EXPAND|wx.ALL, 3)

        sizer.Add(s2, 0, wx.EXPAND)

        self.cmdlist = filtertable(self, columns)
        mylistmix.ListSelect.__init__(self.cmdlist, self.filter)
        sizer.Add(self.cmdlist, 1, wx.EXPAND|wx.ALL, 3)
        
        self.SetSizer(sizer)
        
        self.Bind(wx.EVT_TEXT, self.OnText)
        self.filter.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)
        self.Bind(wx.EVT_CHECKBOX, self.OnText)
        self.Bind(wx.EVT_COMBOBOX, self.OnText)
        self.cmdlist.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        self.getoptions()
        self.getting = 0
    
    def getoptions(self):
        if options:
            self.getting = 1
            try:
                self.cs.SetValue(options[0])
                self.lcs.SetValue(options[1])
                self.context.SetValue(options[2])
                self.how.SetValue(options[3])
                wx.CallAfter(self.update)
            finally:
                self.getting = 0
    
    def setoptions(self):
        if self.getting:
            return
        global options
        options = self.cs.GetValue(), self.lcs.GetValue(), self.context.GetValue(), self.how.GetValue()
    
    def new_hierarchy(self, hier):
        #parse the hierarchy, set the data
        lang = self.stc.style()
        if lang not in ('python', 'tex'):
            return
        names = []
        stk = [hier[::-1]]
        nstk = []
        nstk2 = []
        
        counts = get_line_counts(hier, lang)
        while stk:
            cur = stk.pop()
            if cur is None:
                _ = nstk.pop()
                _ = nstk2.pop()
                continue
            
            while cur:
                name, line_no, leading, children = cur.pop()
                
                if lang == 'python':
                    pre, shortname1 = name.split(None, 1)
                    shortname = partition(partition(shortname1, ':')[0], '(')[0]
                    shortname2 = partition(partition(name, ':')[0], '(')[0]
                    key = '%s%s%s'%('.'.join(nstk), '.'[:bool(nstk)], shortname)
                    
                    names.append((name, line_no, '.'.join(nstk+[shortname]),
                                  '%s %s%s%s'%(pre, '.'.join(nstk), '.'[:bool(nstk)],shortname1),
                                  ': '.join(nstk2+[name]),
                                  (counts.get(key) or [0]).pop(0)
                                  ))
                
                elif lang == 'tex':
                    shortname2 = name
                    head, _, shortname = partition(rstr1(name, '}'), '{')
                    x = '.'.join(nstk+[shortname])
                    names.append((name, line_no, x,
                                  '%s{%s}'%(head, x),
                                  ' '.join(nstk2+[name]),
                                  0
                                  ))
                
                else:
                    #need implementation for C/C++, but only after parser for C/C++ is done
                    continue
                
                if children:
                    stk.append(cur)
                    nstk.append(shortname)
                    nstk2.append(shortname2)
                    stk.append(None)
                    cur = children[::-1]
        self.names = names
        self.update()
    
    def OnEnter(self, e):
        cl = self.cmdlist
        cs = cl.GetFirstSelected()
        if cs == -1:
            cl.Select(0)
        self.OnItemActivated(e)
    
    def OnText(self, e):
        if not self.getting:
            self.setoptions()
            self.update()
        e.Skip()
    
    def update(self):
        global context
        context = self.context.GetValue()
        index = 0
        if context == 'short':
            index = 3
        elif context == 'long':
            index = 4
        
        sseq = self.lcs.GetValue()
        _lcs = lcsseq
        txt = self.filter.GetValue()
        
        lower = not self.cs.GetValue()
        if lower:
            txt = txt.lower()
        
        if not txt.strip():
            names = self.names
        else:
            names = []
            how = self.how.GetValue()
            if how != 'exact':
                txt = txt.split()
            else:
                txt = (txt,)
            
            any = how in ('any', 'exact')
            all = not any

            for i in self.names:
                it = i[index]
                if lower:
                    it = it.lower()
                for j in txt:
                    if j not in it:
                        if sseq:
                            if _lcs(j, it)!=len(j):
                                if all:
                                    break
                            elif any:
                                names.append(i)
                                break
                        elif all:
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
        win = self.stc
        cl = self.cmdlist
        cs = cl.GetFirstSelected()
        if cs == -1:
            cl.Select(0)
            cs = 0
        sel = self.cmdlist.data[cs][1][1]
        if sel < win.GetLineCount():
            sel -= 1
            linepos = win.GetLineEndPosition(sel)
            win.EnsureVisible(sel)
            win.SetSelection(linepos-len(win.GetLine(sel))+len(win.format), linepos)
            win.ScrollToColumn(0)
            win.SetFocus()
    
    def Show(self):
        self.getoptions()
        wx.Panel.Show(self)
        