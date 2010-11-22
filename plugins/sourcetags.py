
'''
This software is licensed under the GPL (GNU General Public License) version 2
as it appears here: http://www.gnu.org/copyleft/gpl.html
It is also included with this archive as `gpl.txt <gpl.txt>`_.
'''


import wx
import todo

columns = ((0, "definiton", 100, 0),)

class SourceTags(wx.Panel):
    def __init__(self, parent, stc):
        wx.Panel.__init__(self, parent)
        self.parent = parent
        self.stc = stc
        
        #child control definition
        self.taglist = wx.CheckListBox(self, -1, style=wx.LB_SINGLE)
        self.results = todo.vTodo(self, columns)
        
        #event binding definition
        self.taglist.Bind(wx.EVT_CHECKLISTBOX, self.OnCheckToggle, self.taglist)
        self.results.Bind(wx.EVT_LIST_ITEM_SELECTED, self.FindDefinition, self.results)
        self.results.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.FindDefinition, self.results)
        
        #layout definition
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.taglist, 1, wx.ALL|wx.EXPAND, 3)
        sizer.Add(self.results, 1, wx.ALL|wx.EXPAND, 3)
        self.SetSizer(sizer)
        
        #data
        self.tags = {}
        self.last_tags = []
        #tags[name] -> {line:defn, line:defn, ...}
        #last_tags -> [name, name, name, ...]
        
    
    def _sortfcn(self, a, b):
        #reversed ordering of number of tags
        return cmp(len(self.tags[b]), len(self.tags[a]))
    
    def OnCheckToggle(self, event):
        tags = []
        for i in xrange(self.taglist.GetCount()):
            if self.taglist.IsChecked(i):
                tags.append(self.taglist.GetString(i))
        
        tags.sort(self._sortfcn)
        self.last_tags = tags[:]
        
        if tags:
            results = self.tags[tags.pop()]
            while tags:
                _results = {}
                next = self.tags[tags.pop()]
                for i,j in results.iteritems():
                    if i in next:
                        _results[i] = j
                results = _results
        else:
            results = self.tags['']
        
        data = [(j,i) for i,j in results.iteritems()]
        self.results.setData(data, copy=0)
        self.results.SortItems()
    
    def FindDefinition(self, event):
        win = self.stc
        selected = self.results.GetFirstSelected()
        if selected == -1:
            return
        sel = self.results.data[selected][1]
        win.GotoLineS(sel)
    
    def newTags(self, tags):
        self.Freeze()
        for i in xrange(self.taglist.GetCount()-1, -1, -1):
            self.taglist.Delete(i)
        self.tags = tags
        self.last_tags = [i for i in self.last_tags if i in tags]
        checkable = tags.keys()
        checkable.sort()
        for j in checkable:
            if not j:
                continue
            posn = self.taglist.Append(j)
            if j in self.last_tags:
                self.taglist.Check(posn, 1)
        self.OnCheckToggle(None)
        self.Thaw()
