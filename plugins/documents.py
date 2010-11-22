
import os
import wx
import wx.stc
import wx.lib.mixins.listctrl as listmix
import __main__

OB1 = 0
class FileDropTarget(wx.FileDropTarget):
    def __init__(self, parent, root):
        wx.FileDropTarget.__init__(self)
        self.parent = parent
        self.root = root
    def OnDropFiles(self, x, y, filenames):
        if len(filenames) != 1:
            #append documents
            for filename in filenames:
                dn, fn = os.path.split(filename)
                filename = self.root.getAbsolute(fn, dn)
                unt = (filename[:10] == '<' and filename[-1:] == '>')
                if unt or self.root.isAbsOpen(filename):
                    #relocate to the end
                    i = self.root.getPositionAbsolute(filename, unt)
                    selected = self.root.control.GetSelection()
                    if i != -1:
                        p = self.root.control.GetPage(i)
                        t = self.root.control.GetPageText(i)
                        self.root.control.RemovePage(i)
                        self.root.control.AddPage(p, t, selected==i)
                else:
                    dn, fn = os.path.split(self.root.getAlmostAbsolute(fn, dn))
                    self.root.newTab(dn, fn)
            return
        
        selindex = self.root.control.GetSelection()
        
        i, _ = self.parent.HitTest((x,y))
        ## print "dropped at position", i, filenames[0]
        
        filename = filenames[0]
        unt = (filename[:1] == '<' and filename[-1:] == '>')
        if not unt:
            dn, fn = os.path.split(filename)
            filename = self.root.getAlmostAbsolute(fn, dn)
            dn, fn = os.path.split(filename)
        new = 0
        if not unt and not self.root.isOpen(fn, dn):
            new = 1
            cp = self.root.control.GetPageCount()
            self.root.newTab(dn, fn, switch=1)
            return
        elif unt:
            for cp, j in enumerate(self.root.control):
                if j.getshort() == filename:
                    break
        else:
            for cp, j in enumerate(self.root.control):
                if j.getlong() == filename:
                    break
        
        ## print "originated at position", cp
        
        if OB1:
            i -= 1
        if i == -1-OB1:
            i = len(l)
        if i != cp:
            #remove from original location, insert at destination
            ## print "getting information for page", cp
            p = self.root.control.GetPage(cp)
            t = self.root.control.GetPageText(cp)
            try:
                self.root.starting = 1
                ## print "removing page", cp
                self.root.control.RemovePage(cp)
                if i >= self.root.control.GetPageCount():
                    self.root.control.AddPage(p, t)
                    ## print "appending page", i, self.root.control.GetPageCount()
                else:
                    ## print "inserting page at", i
                    self.root.control.InsertPage(i, p, t)
                if cp == selindex:
                    ## print "selecting page"
                    self.root.control.SetSelection(min(i, self.root.control.GetPageCount()-1))
            finally:
                self.root.starting = 0


class MyNB(wx.Notebook):
    def __init__(self, root, id, parent):
        #the left-tab, while being nice, turns the text sideways, ick.
        wx.Notebook.__init__(self, parent, id, style=wx.NB_TOP)

        self.root = root
        if __main__.USE_DOC_ICONS:
            self.AssignImageList(__main__.IMGLIST2)

        #for some reason, the notebook needs the next line...the text control
        #doesn't.
        self.Bind(wx.EVT_KEY_DOWN, self.root.OnKeyPressed)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
        self.SetDropTarget(__main__.FileDropTarget(self.root))
        self.calling = 0

    def __iter__(self):
        count = self.GetPageCount()
        cur = 0
        while cur < count:
            r = self.GetPage(cur).GetWindow1()
            yield r
            cur += 1

    def OnPageChanged(self, event):
        if self.calling:
            return

        try:
            self.calling = 1

            old = event.GetOldSelection()
            new = event.GetSelection()
            if old > -1:
                owin = self.GetPage(old).GetWindow1()
                ## owin.docstate.Hide()
            if new > -1:
                self.root.dragger._SelectItem(new)
                win = self.GetPage(new).GetWindow1()
                #fix for dealing with current paths.
                
                if win.dirname:
                    try:
                        __main__.current_path = win.dirname
                    except:
                        traceback.print_exc()
                        pass
                wx.CallAfter(self.updateChecks, win)
                #width = self.GetClientSize()[0]
                #split = win.parent
                #if win.GetWrapMode() == wxSTC_WRAP_NONE:
                #    self.parent.SetStatusText("", 1)
                #else:
                #    self.parent.SetStatusText("WRAP",1)
                self.root.OnDocumentChange(win, None)
                ## win.docstate.Show()

                _, flags = __main__.CARET_OPTION_TO_ID[__main__.caret_option]
                win.SetXCaretPolicy(flags, __main__.caret_slop*__main__.caret_multiplier)
                win.SetYCaretPolicy(flags, __main__.caret_slop)
                win.SetCaretWidth(__main__.CARET_WIDTH)

            self.root.timer.Start(10, wx.TIMER_ONE_SHOT)
            if event:
                event.Skip()
            wx.CallAfter(win.SetFocus)
            wx.CallAfter(self._seen)
        finally:
            self.calling = 0
    
    def updateChecks(self, win):
        #Clear for non-documents
        for i in __main__.ASSOC:
            self.root.menubar.Check(i[1], 0)
        for i in __main__.TB_RMAPPING.itervalues():
            self.root.menubar.Check(i[1], 0)
        for i in __main__.CARET_OPTION_TO_ID.itervalues():
            self.root.menubar.Check(i[0], 0)
        for i in __main__.TITLE_OPTION_TO_ID.itervalues():
            self.root.menubar.Check(i[0], 0)
        for i in __main__.DOCUMENT_LIST_OPTION_TO_ID.itervalues():
            self.root.menubar.Check(i, 0)
        for i in __main__.MACRO_CLICK_OPTIONS.iterkeys():
            self.root.menubar.Check(i, 0)
        
        #Check for non-documents
        self.root.menubar.Check(__main__.lexers3[__main__.DEFAULTLEXER], 1)
        self.root.menubar.Check(__main__.TB_RMAPPING[__main__.TOOLBAR][1], 1)
        self.root.menubar.Check(__main__.CARET_OPTION_TO_ID[__main__.caret_option][0], 1)
        self.root.menubar.Check(__main__.TITLE_OPTION_TO_ID[__main__.title_option][0], 1)
        self.root.menubar.Check(__main__.DOCUMENT_LIST_OPTION_TO_ID[__main__.document_options], 1)
        self.root.menubar.Check(__main__.MACRO_CLICK_TO_ID[__main__.macro_doubleclick], 1)

        if not win:
            return
        
        win.SetCaretLineBack(__main__.COLOUR)
        
        if __main__.UNICODE:
            self.root.SetStatusText(win.enc, 2)
            
            for i in __main__.ENCODINGS.itervalues():
                self.root.menubar.Check(i, 0)
            self.root.menubar.Check(__main__.ENCODINGS[win.enc], 1)

        #clear out all of the marks
        for i in __main__.lexers2.itervalues():
            self.root.menubar.Check(i, 0)
        for i in __main__.LE_RMAPPING.itervalues():
            self.root.menubar.Check(i[1], 0)
        for i in __main__.LL_RMAPPING.itervalues():
            self.root.menubar.Check(i[1], 0)

        #set all of the marks
        self.root.menubar.Check(__main__.lexers2[win.lexer], 1)
        self.root.menubar.Check(__main__.LE_RMAPPING[win.GetEOLMode()][1], 1)
        self.root.menubar.Check(__main__.LL_RMAPPING[win.GetEdgeMode()][1], 1)

        for m,cid in ((0, __main__.NUM), (1, __main__.MARGIN)):
            self.root.menubar.Check(cid, bool(win.GetMarginWidth(m)))
        self.root.menubar.Check(__main__.INDENTGUIDE, win.GetIndentationGuides())
        self.root.menubar.Check(__main__.USETABS, win.GetUseTabs())
        self.root.menubar.Check(__main__.AUTO, win.showautocomp)
        self.root.menubar.Check(__main__.WRAPL, win.GetWrapMode() != wx.stc.STC_WRAP_NONE)
        self.root.menubar.Check(__main__.SLOPPY, win.sloppy)
        self.root.menubar.Check(__main__.SMARTPASTE, win.smartpaste)
        self.root.menubar.Check(__main__.S_WHITE, win.GetViewWhiteSpace())
        ## self.root.menubar.Check(SORTBY, win.tree.tree.SORTTREE)
        self.root.menubar.Check(__main__.SAVE_CURSOR, win.save_cursor)
        self.root.menubar.Check(__main__.HIGHLIGHT_LINE, win.GetCaretLineVisible())
        self.root.menubar.SetHelpString(__main__.IDR, "Indent region %i spaces"%win.GetIndent())
        self.root.menubar.SetHelpString(__main__.DDR, "Dedent region %i spaces"%win.GetIndent())
        self.root.macropage.update_button(win)

#----------------- This deals with the tab swapping support. -----------------
    def RemovePage(self, index):
        self.root.dragger._RemoveItem(index)
        wx.Notebook.RemovePage(self, index)
        wx.CallAfter(self._seen)

    def DeletePage(self, index):
        self.root.dragger._RemoveItem(index)
        page = self.GetPage(index)
        stc = page.GetWindow1()
        stc.docstate.Hide()
        stc.docstate.Destroy()
        wx.Notebook.DeletePage(self, index)
        wx.CallAfter(self._seen)

    def AddPage(self, page, text, switch=0):
        which = __main__.GDI(text)
        self.root.dragger._AddItem(text)
        wx.Notebook.AddPage(self, page, text, switch, which)
        if switch or self.GetPageCount() == 1:
            self.root.OnDocumentChange(page.GetWindow1())
            self.root.dragger._SelectItem(self.GetPageCount()-1)
            wx.CallAfter(self._seen)

    def InsertPage(self, posn, page, text, switch=0):
        which = __main__.GDI(text)
        self.root.dragger._InsertItem(posn, text)
        wx.Notebook.InsertPage(self, posn, page, text, switch, which)
        if self.GetSelection() == posn or switch:
            self.root.OnDocumentChange(page.GetWindow1())
        wx.CallAfter(self._seen)
        
    def SetPageText(self, posn, text):
        self.root.dragger._RenameItem(posn, text)
        wx.Notebook.SetPageText(self, posn, text)
        wx.CallAfter(self._seen)
    
    def _seen(self):
        sel = self.GetSelection()
        if sel == -1:
            return
        shown = None
        for j,i in enumerate(self):
            if i.docstate.IsShown() and j != sel:
                i.docstate.Hide()
            elif j == sel and not i.docstate.IsShown():
                i.docstate.Show()
            if i.docstate.IsShown():
                shown = i
        if shown:
            self.root.OnDocumentChange(shown)
        self.root.dragger._Refresh()
        self.root.dragger._SelectItem(sel)

class MyLC(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, root):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT|wx.BORDER_NONE|wx.LC_VIRTUAL)
        listmix.ListCtrlAutoWidthMixin.__init__(self)
        ## self.setResizeColumn(1)
        self.root = root
        
        self.setupcolumns()
        
        self.SetDropTarget(FileDropTarget(self, root))
        
        if __main__.USE_DOC_ICONS:
            self.AssignImageList(__main__.IMGLIST1, wx.IMAGE_LIST_SMALL)
        
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.OnBeginDrag)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnSelectionChanged)
        self.data = []
    
    def setupcolumns(self):
        for i in xrange(self.GetColumnCount()-1, -1, -1):
            self.DeleteColumn(i)
        
        do = __main__.document_options
        if do&1:
            self.InsertColumn(self.GetColumnCount(), "Filename")
        if (do&2) or do == 0:
            self.InsertColumn(self.GetColumnCount(), "Whole Path")
        if do == 0:
            self.InsertColumn(self.GetColumnCount(), "Filename")
            
        #0 -> path, filename
        #1 -> filename
        #2 -> path
        #3 -> filename, path
        self.resizeColumn(32)
    
    def OnGetItemText(self, index, col):
        if index >= self.root.control.GetPageCount():
            return ''
        do = __main__.document_options
        if do == 0:
            col = not col
        elif do == 2:
            col = 1
        
        item = self.root.control.GetPage(index).GetWindow1()
        if col == 0:
            return item.getshort()
        return item.getlong()
    
    def OnGetItemImage(self, item):
        if item >= self.root.control.GetPageCount():
            return -1
        return __main__.GDI(self.root.control.GetPage(item).GetWindow1().getshort())
    
    def OnSelectionChanged(self, event):
        self.root.control.SetSelection(event.GetIndex())
        self.root.control.GetPage(event.GetIndex()).GetWindow1().SetFocus()
    
    def OnBeginDrag(self, event):
        posn = event.GetIndex()
        if posn == -1:
            event.Skip()
            return
        
        a = self.root.control.GetPage(posn).GetWindow1()
        data = a.getlong()
        if not data:
            data = a.getshort()
        
        data = data.encode('ascii')
        d = wx.FileDataObject()
        d.AddFile(data)
        ## print d.GetFilenames()
        a = wx.DropSource(self)
        a.SetData(d)
        a.DoDragDrop(wx.Drag_AllowMove|wx.Drag_CopyOnly)
    
    def _special_method(self, *args):
        self.SetItemCount(self.root.control.GetPageCount())
        self.Refresh()

    _RemoveItem = _AddItem = _InsertItem = \
    _RenameItem = _Refresh = _special_method
    
    def _SelectItem(self, index):
        x = self.GetFirstSelected()
        while x != -1:
            self.Select(x, 0)
            x = self.GetNextSelected(x)
        self.Select(index)
        


class _MyLC(wx.gizmos.TreeListCtrl):
    class FileDropTarget(wx.FileDropTarget):
        def __init__(self, parent, root):
            wx.FileDropTarget.__init__(self)
            self.parent = parent
            self.root = root
        def OnDropFiles(self, x, y, filenames):
            if len(filenames) != 1:
                #append documents
                for filename in filenames:
                    dn, fn = os.path.split(filename)
                    filename = self.root.getAbsolute(fn, dn)
                    unt = (filename[:10] == '<untitled ' and filename[-1:] == '>')
                    if unt or self.root.isAbsOpen(filename):
                        #relocate to the end
                        i = self.root.getPositionAbsolute(filename, unt)
                        selected = self.root.control.GetSelection()
                        if i != -1:
                            p = self.root.control.GetPage(i)
                            t = self.root.control.GetPageText(i)
                            self.root.control.RemovePage(i)
                            self.root.control.AddPage(p, t, selected==i)
                    else:
                        dn, fn = os.path.split(self.root.getAlmostAbsolute(fn, dn))
                        self.root.newTab(dn, fn)
                return

            try:
                selindex = [i[0] for i in self.parent.getAllRectangles()].index(self.parent.selected)
            except:
                selindex = -1


            l = self.parent.getAllRectangles()
            i = -1

            for p, (item, rect) in enumerate(l):
                if l is not None:
                    if y >= rect.y and y < rect.y+rect.height:
                        i = p

            filename = filenames[0]
            dn, fn = os.path.split(filename)
            unt = (filename[:10] == '<untitled ' and filename[-1:] == '>')
            if not unt:
                filename = self.root.getAlmostAbsolute(fn, dn)
                dn, fn = os.path.split(filename)
            new = 0
            if not unt and not self.root.isOpen(fn, dn):
                new = 1
                cp = self.root.control.GetPageCount()
                self.root.newTab(dn, fn, switch=1)
                return
            else:
                cp = self.root.getPositionAbsolute(self.root.getAbsolute(fn, dn), unt)
            
            i -= 1
            if i == -2:
                i = len(l)
            if i != cp:
                #remove from original location, insert at destination
                p = self.root.control.GetPage(cp)
                t = self.root.control.GetPageText(cp)
                try:
                    self.root.starting = 1
                    self.root.control.RemovePage(cp)
                    if i >= self.root.control.GetPageCount():
                        self.root.control.AddPage(p, t)
                    else:
                        self.root.control.InsertPage(i, p, t)
                    if cp == selindex:
                        self.root.control.SetSelection(min(i, self.root.control.GetPageCount()-1))
                finally:
                    self.root.starting = 0

    def __init__(self, parent, root):
        tID = wx.NewId()
        wx.gizmos.TreeListCtrl.__init__(self, parent, tID,
            style=wx.TR_HIDE_ROOT|wx.TR_NO_LINES|wx.TR_NO_BUTTONS)
        
        self.AddColumn("Filename")
        self.AddColumn("Whole Path")
        self.SetMainColumn(0)
        
        self.root = root
        self.rootnode = self.AddRoot("Unseen Root")
        self.SetDropTarget(self.FileDropTarget(self, root))
        if __main__.USE_DOC_ICONS:
            self.AssignImageList(__main__.IMGLIST1)

        ## EVT_TREE_ITEM_ACTIVATED(self, tID, self.OnTreeItemActivated)
        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnTreeBeginDrag)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeSelectionChanged)

    def getAllRectangles(self):
        return [(item, self.GetBoundingRect(item)) for item in self._GetChildren()]

    def OnTreeBeginDrag(self, event):
        item = event.GetItem()
        lst = self.getAllRectangles()
        posn = -1
        for i, (itemi, toss) in enumerate(lst):
            if item == itemi:
                posn = i
                break

        if posn == -1:
            ## print "BAH!"
            event.Skip()
            return
        
        a = self.root.control.GetPage(posn).GetWindow1()
        data = os.path.join(a.dirname, a.filename).encode('ascii')
        if data == ' ':
            data = '<untitled %i>'%a.NEWDOCUMENT
        d = wx.FileDataObject()
        d.AddFile(data)
        ## print d.GetFilenames()
        a = wxDropSource(self)
        a.SetData(d)
        a.DoDragDrop(wx.Drag_AllowMove|wx.Drag_CopyOnly)

    def OnTreeSelectionChanged(self, event):

        self.selected = item = event.GetItem()
        items = [i[0] for i in self.getAllRectangles()]
        try:
            indx = items.index(item)
            self.root.control.SetSelection(indx)
        except:
            pass

    def _RemoveItem(self, index):
        chlist = self.getAllRectangles()
        self.Delete(chlist[index][0])

    def _AddItem(self, label):
        which = __main__.GDI(label)
        self.AppendItem(self.rootnode, label, which)

    def _InsertItem(self, index, label):
        if index == self.GetChildrenCount(self.rootnode, False):
            self._AddItem(label)
        else:
            which = __main__.GDI(label)
            self.InsertItemBefore(self.rootnode, index, label, which)

    def _SelectItem(self, index):
        chlist = self.getAllRectangles()
        if index < len(chlist):
            self.SelectItem(chlist[index][0])
        
    def _RenameItem(self, index, label):
        self.SetItemText(self.getAllRectangles()[index][0], label)
    
    def _GetChildren(self):
        count = self.GetChildrenCount(self.rootnode)
        lst = []
        while len(lst) < count:
            if len(lst) == 0:
                (item, cookie) = self.GetFirstChild(self.rootnode)
            else:
                (item, cookie) = self.GetNextChild(self.rootnode, cookie)
            lst.append(item)
        return lst
        
    def _Refresh(self):
        for item, page in zip(self._GetChildren(), self.root.control):
            if page.dirname:
                self.SetItemText(item, os.path.join(page.dirname, page.filename), 1)

