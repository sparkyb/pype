
import wx

import codetree
import todo
import filtertable

class docstate:
    def __init__(self, root, stc):
        self.root = root
        self.stc = stc
        
        self.tree1 = codetree.hierCodeTreePanel(root, root.leftt, 1)
        self.tree2 = codetree.hierCodeTreePanel(root, root.rightt, 0)
        self.todo = todo.VirtualTodo(root.todot, root)
        self.filter = filtertable.DefinitionList(root.filterl, root, stc)
        
        self.items = (self.tree1, self.tree2, self.todo, self.filter)
        
        self.isshown = -1
        self.Add()
        
    def Hide(self):
        for i in self.items:
            i.Hide()
            i.parent.Layout()
        self.isshown = 0
    
    def Show(self):
        for i in self.items:
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
    
    def Update(self, hierarchy, todo):
        self.tree1.new_hierarchy(hierarchy)
        self.tree2.new_hierarchy(hierarchy)
        self.todo.NewItemList(todo)
        self.filter.new_hierarchy(hierarchy)

def _choicebook(parent, id):
    cp = wx.Panel(parent, id)
    cp.sizer = wx.BoxSizer(wx.VERTICAL)
    cp.SetSizer(cp.sizer)
    return cp
