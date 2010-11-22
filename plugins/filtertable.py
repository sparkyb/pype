
import itertools
import math
import wx

import codetree
import exparse
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
    D = {}
    for i,j in codetree.D.items():
        k = wx.ListItemAttr()
        k.SetTextColour(j)
        D[i] = k
    
    default = D['de']
    
    del i, j, k

def lcsseq(x, y):
    #stores the full table, not necessary
    _enum = enumerate
    _max = max
    z = {}
    zg = z.get
    for i, xi in _enum(x):
        for j, yj in _enum(y):
            if xi == yj:
                k = zg((i-1,j-1), 0)+1
            else:
                k = zg((i-1,j), 0)
                l = zg((i,j-1), 0)
                if l > k:
                    k = l
            z[i,j] = k
    
    return z[i,j]

def lcsseq(x, y):
    #only stores most recent 2 lines
    #more than sufficient for our uses
    #significantly faster than the above
    #not necessary
    _enum = enumerate
    if len(y) > len(x):
        x,y = y,x
    if len(y) == 0:
        return 0
    z1 = len(y)*[0]
    z2 = z1[:]
    z1.append(0) #for == case and j==0
    for i, xi in _enum(x):
        z2[0] = z2[-1] = 0 #for != case and j==0
        for j, yj in _enum(y):
            if xi == yj:
                z2[j] = z1[j-1]+1
            else:
                k = z1[j]
                l = z2[j-1]
                if l > k:
                    k = l
                z2[j] = k
        z1[:-1] = z2[:] #for == case and j==0
    return z1[-2]

def _lcsseq(x,y):
    if len(y) > len(x):
        return 0
    ## xf = x.find
    posn = 0
    for c in y:
        posn = x.find(c, posn) + 1
        if posn == 0:
            return 0
    return len(y)

def lcsseq(x,y):
    #we really only want to know if _all_ of the characters of the shorter 
    #string are in the longer string in order
    #significantly faster than either of the above at O(n+m), compared to
    #O(n*m)
    if len(y) > len(x):
        x,y = y,x
    return _lcsseq(x,y)

def _sseq_score(x,y):
    # Only call this when you know that y is a subsequence of x.
    # Will return a "score" for the quality of the subsequence match.
    # Contiguous substring matches induce 0 score.
    ml = math.log10
    posn = x.find(y[0])
    score = 0
    for c in y:
        oposn = posn
        posn = x.find(c, posn) + 1
        try:
            score += ml(posn-oposn)
        except:
            print score, posn, oposn, c, x
            raise
    return score

class filtertable(todo.vTodo, mylistmix.ListSelect):
    def OnGetItemText(self, item, col):
        context = self.context
        if USE_NEW:
            it = self.data[item]
            if col == 1:
                if context == 'short':
                    return str(it.short)
                elif context == 'long':
                    return str(it.long)
                else:
                    return str(it.defn)
            else:
                return str(it.lines)
        elif col == 1:
            if context == 'short':
                return '%s'%(self.data[item][3],)
            elif context == 'long':
                return '%s'%(self.data[item][4],)
            else:
                return '%s'%(self.data[item][0],)
        else:
            return '%s'%(self.data[item][5],)
    def OnGetItemAttr(self, item):
        if USE_NEW:
            return D.get(self.data[item].defn[:2], default)
        return D.get(self.data[item][0][:2], default)
    def SortItems(self, *args, **kwargs):
        # Override listctrl mixin
        col=self._col
        ascending = self._colSortFlag[col]
        
        if USE_NEW:
            if self.data and col:
                try:
                    col = self.data[0].__slots__.index(context)
                except:
                    pass
            print "col", col
        else:
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
        if col != 0:
            cmpf = lambda a,b: _cmp(a[col].lower(),b[col].lower())
        else:
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
    if lang not in ('python', 'cpp') and not lang.endswith('ml'):
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
            
            if lang == 'python':
                pre, shortname1 = name.split(None, 1)
                shortname = partition(partition(shortname1, ':')[0], '(')[0]
                key = '%s%s%s'%('.'.join(nstk), '.'[:bool(nstk)], shortname)
            
            elif lang == 'cpp':
                key, shortname = name, line_no[2]
            
            elif lang.endswith('ml'):
                key, shortname = name, line_no[2]
            
            if lastn and not name.startswith('--'):
                counts.setdefault(lastn, []).append(line_no[1]-lastl)
            
            if not name.startswith('--'):
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
        self.sco = wx.CheckBox(self, -1, "Scored")
        
        s2 = wx.BoxSizer(wx.HORIZONTAL)
        s2.Add(self.cs, 0, wx.EXPAND|wx.ALL, 3)
        s2.Add(wx.StaticText(self, -1, ""), 1, wx.EXPAND|wx.ALL, 0)
        s2.Add(self.lcs, 0, wx.EXPAND|wx.ALL, 3)
        s2.Add(wx.StaticText(self, -1, ""), 1, wx.EXPAND|wx.ALL, 0)
        s2.Add(self.sco, 0, wx.EXPAND|wx.ALL, 3)
        
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
                if len(options) >= 5:
                    self.sco.SetValue(options[4])
                wx.CallAfter(self.update)
            finally:
                self.getting = 0
    
    def setoptions(self):
        if self.getting:
            return
        global options
        options = self.cs.GetValue(), self.lcs.GetValue(), self.context.GetValue(), self.how.GetValue(), self.sco.GetValue()
    
    def new_hierarchy(self, hier):
        #parse the hierarchy, set the data
        lang = self.stc.style()
        if lang not in ('python', 'tex', 'cpp') and not lang.endswith('ml'):
            return

        if USE_NEW:
            self.names = hier
            self.update()
            return

        counts = get_line_counts(hier, lang)
        names = []
        stk = [hier[::-1]]
        nstk = []
        nstk2 = []
        
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
                
                elif lang == 'cpp':
                    shortname = line_no[2]
                    shortname2 = name
                    x = '.'.join(nstk+[shortname])
                    y = name.find(line_no[2])
                    names.append((name, line_no, x,
                                  "%s %s%s%s"%(name[:y].strip(), '.'.join(nstk), '.'[:bool(nstk)], name[y:].strip()),
                                  ' '.join(nstk2+[name]),
                                  (counts.get(name) or [0]).pop(0)))
                elif lang.endswith('ml'):
                    names.append((name, line_no, name, name, name, 1))
                
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
        if e:
            e.Skip()
    
    def update(self):
        context = self.cmdlist.context = self.context.GetValue()
        if USE_NEW:
            index = 2
            if context == 'short':
                index = 9
            elif context == 'long':
                index = 10
        else:
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
            names = [i for i in self.names if i[index]]
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
            
            if sseq and self.sco.GetValue():
                def key(i, xx=txt, score=_sseq_score, prematch=(how=='any'), index=index):
                    # Average score/match works pretty well here, especially
                    # when we induce a len(input) score for mismatches.
                    matches = 0
                    sc = 0
                    iil = i[index].lower()
                    for x in xx:
                        if (not prematch) or (prematch and _lcs(x, iil) == len(x)):
                            matches += 1
                            sc += score(iil, x)
                        else:
                            sc += len(iil)
                    return sc / matches
                names.sort(key=key)
        
        self.cmdlist.setData(names, copy=0)
    
    def OnItemActivated(self, event):
        win = self.stc
        cl = self.cmdlist
        cs = cl.GetFirstSelected()
        if cs == -1:
            cl.Select(0)
            cs = 0
        if USE_NEW:
            sel = self.cmdlist.data[cs].lineno
        else:
            sel = self.cmdlist.data[cs][1][1]
        if sel < win.GetLineCount():
            sel -= 1
            win.lines.selectedlinesi = sel, sel+1
            win.EnsureVisible(sel)
            win.ScrollToColumn(0)
            win.SetFocus()
    
    def Show(self):
        self.getoptions()
        wx.Panel.Show(self)

class MultiFilter(object):
    def __init__(self, root):
        self.root = root
        self.datamap = {}
    def __iter__(self):
        order = [(i.dirname, i.filename, getattr(i, 'NEWDOCUMENT', None)) for i in self.root.control]
        for finfo in order:
            for i, d in enumerate(self.datamap.get(finfo, [])):
                if not i:
                    continue
                d.fileinfo = finfo
                yield d
    def __setitem__(self, stc, value):
        self.datamap[stc.dirname, stc.filename, getattr(stc, 'NEWDOCUMENT', None)] = value
    def __delitem__(self, stc):
        self.datamap.pop((stc.dirname, stc.filename, getattr(stc, 'NEWDOCUMENT', None)), None)

class GlobalFilter(DefinitionList):
    def __init__(self, parent, root):
        self.root = root
        DefinitionList.__init__(self, parent, root, None)
        self.names = MultiFilter(root)
        wx.CallAfter(self.getoptions)
    def new_hierarchy(self, stc, value):
        self.names[stc] = value
        self.getoptions()
    def close_hierarchy(self, stc):
        del self.names[stc]
        self.getoptions()
    def OnItemActivated(self, event):
        ## win = self.stc
        cl = self.cmdlist
        cs = cl.GetFirstSelected()
        if cs == -1:
            cl.Select(0)
            cs = 0
        finfo = self.cmdlist.data[cs].fileinfo
        sel = self.cmdlist.data[cs].lineno
        for i, win in enumerate(self.root.control):
            if (win.dirname, win.filename, getattr(win, 'NEWDOCUMENT', None)) == finfo:
                 break
        else:
            return
        self.root.control.SetSelection(i)
        if sel < win.GetLineCount():
            sel -= 1
            win.lines.selectedlinesi = sel, sel+1
            win.EnsureVisible(sel)
            win.ScrollToColumn(0)
            win.SetFocus()
