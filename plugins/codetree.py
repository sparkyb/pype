import wx
import sys
import os
import time

icons = 1
colors = 1
colored_icons = 1
newroot = sys.platform != 'win32'

blue = wx.Colour(0, 0, 200)
red = wx.Colour(200, 0, 0)
green = wx.Colour(0, 200, 0)
orange = wx.Colour(200, 100, 0)

D = {'cl':blue,
     'de':red,
     'cd':green,
     '\\l':red,
     '\\s':blue,
     '#b':orange,
     '#d':green,
     '\\se':blue,
     '\\su':green}

#------------------------------------ ... ------------------------------------
# Node and getTree thanks to the foldExplorer from Stani.
# Some modifications have been made, among them are language-specific
# mechanisms for only pulling out function and class definitions.

class Node(object):
    __slots__ = 'parent level start end text styles children'.split()
    def __init__(self,level,start,end,text,parent=None,styles=[]):
        """Folding node as data for tree item."""
        self.parent     = parent
        self.level      = level
        self.start      = start
        self.end        = end
        self.text       = text
        self.styles     = styles #can be useful for icon detection
        self.children   = []

def getTree(self):
    #self must be an stc instance
    n = self.GetLineCount()+1
    prevNode = root  = Node(level=-1,start=0,end=n,text='root',parent=None)
    for line in xrange(n-1):
        foldBits = self.GetFoldLevel(line)
        if not foldBits&stc.STC_FOLDLEVELHEADERFLAG:
            continue
        #folding point
        level = foldBits&stc.STC_FOLDLEVELNUMBERMASK
        while level <= prevNode.level:
            prevNode.end = line
            prevNode = prevNode.parent
            
        text = self.GetLine(line).strip()
        if self.lexer in ('cpp', 'java',):
            if text.startswith('{'):
                text = self.GetLine(max(line-1, 0)).strip()
                if text.startswith('{'):
                    continue
            if text.split()[0] in ('if', 'else', 'while', 'for', 'do'):
                continue
        elif self.lexer == 'python':
            #it's terribly convenient that Python has only two ways of
            #starting a definition
            if text.split()[0] not in ('def', 'class'):
                continue
        elif self.lexer == 'pyrex':
            if text.split()[0] not in ('def', 'class', 'cdef'):
                continue
                
        node = Node(level=level,start=line,end=n,text=text)
            
        #give birth to child (only one level deep)
        node.parent = prevNode
        prevNode.children.append(node)
        prevNode = node
    prevNode.end = line
    return root

#------------------------------------ ... ------------------------------------


class TreeCtrl(wx.TreeCtrl):
    def __init__(self, parent, st):
        wx.TreeCtrl.__init__(self, parent, -1, style=wx.TR_DEFAULT_STYLE|wx.TR_HAS_BUTTONS|wx.TR_HIDE_ROOT)
        self.parent = parent
        if icons:
            isz = (16,16)
            il = wx.ImageList(isz[0], isz[1])
            self.images = [wx.ArtProvider_GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, isz),
                        wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN, wx.ART_OTHER, isz),
                        wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz)]
            
            for icf in ('icons/green.png', 'icons/yellow.png', 'icons/red.png'):
                icf = os.path.join(_pype.runpath, icf)
                self.images.append(wx.BitmapFromImage(wx.Image(icf)))
            
            for i in self.images:
                il.Add(i)
            self.SetImageList(il)
            self.il = il
        self.SORTTREE = st

        self.root = self.AddRoot("Unseen Root")

    def OnCompareItems(self, item1, item2):
        d1 = self.GetItemData(item1).GetData()
        d2 = self.GetItemData(item2).GetData()
        ## print "got data", d1.name, d2.name
        return self.parent.cmpf(d1, d2)
    
    def SortAll(self):
        stk = [self.root]
        while stk:
            cur = stk.pop()
            if self.GetChildrenCount(cur):
                self.SortChildren(cur)
                stk.extend(self._get_children(cur))
    
    def _get_children(self, node):
        chi = []
        z = self.GetChildrenCount(node) - 1
        if z == -1:
            return chi
        try:    #2.6 and previous
            ch, cookie = self.GetFirstChild(node, 0)
        except: #2.7 and later
            ch, cookie = self.GetFirstChild(node)
        if ch.IsOk():
            chi.append(ch)
        while z > 0:
            ch, cookie = self.GetNextChild(node, cookie)
            if ch.IsOk():
                chi.append(ch)
            z -= 1
        return chi
    
    def get_tree(self):
        content = []
        stk = [(ch, ()) for ch in self._get_children(self.root)]
        stk.reverse()
        while stk:
            cur, h = stk.pop()
            x = h + (self.GetItemText(cur),)
            content.append((x, cur))
            if self.GetChildrenCount(cur):
                chi = self._get_children(cur)
                chi.reverse()
                for ch in chi:
                    stk.append((ch, x))
        
        return content
    
    def _save(self):
        expanded = []
        selected = None
        fvi = None
        y = self.GetFirstVisibleItem()
        
        stk = [(ch, ()) for ch in self._get_children(self.root)]
        
        while stk:
            cur, h = stk.pop()
            x = h + (self.GetItemText(cur),)
            if self.IsSelected(cur):
                selected = x
            if cur == y:
                fvi = x
            if self.GetChildrenCount(cur) and self.IsExpanded(cur):
                expanded.append(x)
                for ch in self._get_children(cur):
                    stk.append((ch, x))
        
        return dict.fromkeys(expanded), selected, fvi
    
    def _restore(self, expanded, selected, fvi):
        stk = [(ch, ()) for ch in self._get_children(self.root)]
        y = None
        
        while stk:
            cur, h = stk.pop()
            x = h + (self.GetItemText(cur),)
            if x == fvi:
                y = cur
            if selected == x:
                if not y:
                    y = cur
                self.SelectItem(cur)
            if self.GetChildrenCount(cur):
                if x in expanded:
                    self.Expand(cur)
                for ch in self._get_children(cur):
                    stk.append((ch, x))
        if y:
            wx.CallAfter(self.ScrollTo, y)

def new_tree(hier, cmpf):
    
    h = hier[:]
    h.sort(cmpf)
    h.reverse()
    stk = [(i, ()) for i in h]
    
    content = []
    while stk:
        a = stk.pop()
        try:
            b, x = a
            [name, line_no, leading, children] = b
        except:
            print len(b)
            raise
        x = x + (name,)
        content.append((x, name, line_no, bool(children)))
        
        if children:
            children = children[:]
            children.sort(cmpf)
            children.reverse()
            for ch in children:
                stk.append((ch, x))
    
    return content

def set_color_and_icon(tree, item, name, short, children):
    if colors:
        if name[:3] in D:
            tree.SetItemTextColour(item, D[name[:3]])
        else:
            tree.SetItemTextColour(item, D.get(name[:2], blue))
    if children:
        if icons:
            tree.SetItemImage(item, 0, wx.TreeItemIcon_Normal)
            tree.SetItemImage(item, 1, wx.TreeItemIcon_Expanded)
    elif icons:
        color = 2
        if colored_icons:
            green = short.startswith('__') and short.endswith('__')
            green = green or not short.startswith('_')
            red = (not green) and short.startswith('__')
            
            if green:
                color = 3
            elif red:
                color = 5
            else:
                color = 4
        
        tree.SetItemImage(item, color, wx.TreeItemIcon_Normal)
        tree.SetItemImage(item, color, wx.TreeItemIcon_Selected)
    

class hierCodeTreePanel(wx.Panel):
    def __init__(self, root, parent, st):
        # Use the WANTS_CHARS style so the panel doesn't eat the Return key.
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)
        self.parent = parent

        self.root = root

        tID = wx.NewId()

        self.tree = TreeCtrl(self, st)
        if st:
            #name
            if USE_NEW:
                self.cmpf = lambda d1, d2: cmp(d1.name.lower(), d2.name.lower())
            else:
                self.cmpf = lambda d1, d2: cmp(d1,d2)
            
        else:
            #line
            if USE_NEW:
                self.cmpf = lambda d1, d2: cmp(d1.lineno, d2.lineno)
            else:
                self.cmpf = lambda d1, d2: cmp(d1[1],d2[1])
        self.data = {}
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(sizer)
        
        #self.tree.Expand(self.root)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate)
    
    def new_hierarchy(self, hier):
        self.Freeze()
        ## t = time.time()
        stk = [self.tree.root]
        old = {}
        for name, ite in self.tree.get_tree():
            while len(stk) > len(name):
                _ = stk.pop()
            if name in old:
                old[name].append((ite, stk[-1]))
            else:
                old[name] = [(ite, stk[-1])]
            stk.append(ite)

        if not USE_NEW:
            done = {():self.tree.root}
            for name, nam, data, ch in new_tree(hier, self.cmpf):
                if name in old:
                    ent = old[name]
                    item_no, par = ent.pop(0)
                    if not ent:
                        del old[name]
                    done[name[:-1]] = par
                    done[name] = item_no
                    self.tree.SetPyData(item_no, data)
                else:
                    #if we get to this item, its parent *must* be in the tree
                    par = done[name[:-1]]
                    item_no = self.tree.AppendItem(par, nam)
                    done[name] = item_no
                    ## print "added:", name
                    self.tree.SetPyData(item_no, data)
                set_color_and_icon(self.tree, item_no, name[-1], data[2], ch)
            
        else:
            self.data.clear()
            done = {():self.tree.root}
            hasch = set()
            stk = []
            for data in hier:
                # generate the name
                try:
                    if data.depth <= 0:
                        continue
                except:
                    print data
                    raise
                while stk and data.depth <= stk[-1].depth:
                    _ = stk.pop()
                stk.append(data)
                name = tuple(i.defn for i in stk)
                nt = name[:-1]
                # toss into the tree
                if name in old:
                    ent = old[name]
                    item_no, par = ent.pop(0)
                    if not ent:
                        del old[name]
                    done[nt] = par
                    done[name] = item_no
                    hasch.add(par)
                else:
                    #if we get to this item, its parent *must* be in the tree
                    par = done[nt]
                    hasch.add(par)
                    item_no = self.tree.AppendItem(par, data.defn)
                    done[name] = item_no
                self.tree.SetPyData(item_no, data)
            for item_no in done.itervalues():
                data = self.tree.GetItemData(item_no).GetData()
                if not data:
                    continue
                set_color_and_icon(self.tree, item_no, data.defn, data.name, item_no in hasch)
        
        old = old.items()
        old.sort(reverse=True)
        
        for x in old:
            name = x[0]
            for item, parent in x[1]:
                self.tree.Delete(item)
                #shouldn't need to update colors, etc, should be done in the previous loop
                ## if len(name) >= 2 and self.tree.GetChildrenCount(parent) < 1:
                    ## set_color_and_icon(self.tree, parent, name[-2], self.GetItemData(parent).GetData(), 0)
        
        self.tree.SortAll()
        ## print "tree rebuild:", time.time()-t
        self.Thaw()

    def OnLeftDClick(self, event):
        #pity this doesn't do what it should.
        num, win = self.root.getNumWin(event)
        win.SetFocus()

    def OnActivate(self, event):
        num, win = self.root.getNumWin(event)
        dat = self.tree.GetItemData(event.GetItem()).GetData()
        if dat == None:
            return event.Skip()
        if USE_NEW:
            ln = dat[0]-1
        else:
            ln = dat[1]-1
        #print ln
        #print dir(win)
        win.lines.selectedlinesi = ln, ln+1
        win.EnsureVisible(ln)
        win.ScrollToColumn(0)
        win.SetFocus()
