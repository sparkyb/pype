
import wx

import codetree
import todo
import filtertable
import sourcetags
import tagger

possible = ('tree1', 'tree2', 'todo', 'filter')#, 'sourcetags', 'tagger')
enabled = dict.fromkeys(possible)

HIER, TODO, TAGS = 0, 1, 2

methods = {HIER:'new_hierarchy', TODO:'NewItemList', TAGS:'newTags'}
whicharg = {'tree1':HIER, 'tree2':HIER, 'todo':TODO, 'filter':HIER,
            ## 'sourcetags':TAGS, 'tagger':TAGS
            }

class docstate:
    def __init__(self, root, stc):
        self.root = root
        self.stc = stc
        
        self.tree1 = codetree.hierCodeTreePanel(root, root.leftt, 1)
        self.tree2 = codetree.hierCodeTreePanel(root, root.rightt, 0)
        self.todo = todo.VirtualTodo(root.todot, root)
        self.filter = filtertable.DefinitionList(root.filterl, root, stc)
        ## self.sourcetags = sourcetags.SourceTags(root.taglist, stc)
        ## self.tagger = tagger.TagManager(root.tagmanage, stc)
        
        self.items = (self.tree1, self.tree2, self.todo, self.filter)
        ## self.items = (self.tree1, self.tree2, self.todo, self.filter, self.sourcetags, self.tagger)
        
        self.isshown = -1
        self.Add()
    
    def Hide(self):
        for i in self.items:
            i.Hide()
            i.parent.Layout()
        self.isshown = 0
    
    def Show(self):
        for j in possible:
            if j not in enabled:
                continue
            i = getattr(self, j)
            i.Show()
            i.parent.Layout()
        self.isshown = 1
    
    def Add(self):
        for i in self.items:
            i.parent.sizer.Add(i, 1, wx.EXPAND)
        self.Hide()
    
    def Destroy(self):
        self.Hide()
        for i in self.items:
            ip = i.parent
            i.parent.sizer.Detach(i)
            i.Destroy()
            ip.Layout()
        del self.stc.docstate
    
    def IsShown(self):
        return self.isshown
    
    def Update(self, hierarchy, todo, tags):
        htt = hierarchy, todo, tags
        for i in possible:
            if i in enabled:
                which = whicharg[i]
                method = methods[which]
                getattr(getattr(self, i), method)(htt[which])

def _choicebook(parent, id):
    cp = wx.Panel(parent, id)
    cp.sizer = wx.BoxSizer(wx.VERTICAL)
    cp.SetSizer(cp.sizer)
    cp.parent = parent
    return cp
