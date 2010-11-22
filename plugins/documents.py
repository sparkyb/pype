
'''
This software is licensed under the GPL (GNU General Public License) version 2
as it appears here: http://www.gnu.org/copyleft/gpl.html
It is also included with this archive as `gpl.txt <gpl.txt>`_.
'''


from collections import deque
import itertools
import os
import string
import threading
import time
import wx
import wx.stc
import wx.lib.mixins.listctrl as listmix
import __main__

import filtertable

attr1 = wx.ListItemAttr()
attr1.SetBackgroundColour(wx.Colour(0xee, 0xff, 0xee))

attr2 = wx.ListItemAttr()
attr2.SetBackgroundColour(wx.Colour(0xee, 0xee, 0xff))

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
            i = self.root.control.GetPageCount()
        if i != cp:
            self.root.control.MoveTabPage(cp, i, selindex)

WHICHNB = 2

if WHICHNB == 0:
    BaseNotebook = wx.Notebook
    _style = wx.NB_TOP
    pch = wx.EVT_NOTEBOOK_PAGE_CHANGED
elif WHICHNB == 1:
    import wx.lib.flatnotebook as fnb
    BaseNotebook = fnb.FlatNotebook
    _style = fnb.FNB_NODRAG|fnb.FNB_DROPDOWN_TABS_LIST|fnb.FNB_NO_NAV_BUTTONS|fnb.FNB_NO_X_BUTTON|fnb.FNB_FF2
    pch = fnb.EVT_FLATNOTEBOOK_PAGE_CHANGED
elif WHICHNB == 2:
    from wx import aui
    BaseNotebook = aui.AuiNotebook
    _style = aui.AUI_NB_SCROLL_BUTTONS|aui.AUI_NB_TOP|aui.AUI_NB_CLOSE_ON_ACTIVE_TAB|aui.AUI_NB_TAB_MOVE
    pch = aui.EVT_AUINOTEBOOK_PAGE_CHANGED

class MyNB(BaseNotebook):
    def __init__(self, root, id, parent):
        BaseNotebook.__init__(self, parent, id, style=_style)
        self.root = root
        if WHICHNB != 2:
            if __main__.USE_DOC_ICONS:
                self.AssignImageList(__main__.IMGLIST2)
        else:
            self.imagelist = __main__.IMGLIST3

        #for some reason, the notebook needs the next line...the text control
        #doesn't.
        self.Bind(wx.EVT_KEY_DOWN, self.root.OnKeyPressed)
        self.Bind(pch, self.OnPageChanged)
        self.Bind(wx.EVT_SET_FOCUS, self.GotFocus)

        self.SetDropTarget(__main__.FileDropTarget(self.root))
        self.calling = 0
        self.other_focus = 0
        self.fr = None
        self.cs = 0
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.OnClose)
        self.Bind(aui.EVT_AUINOTEBOOK_BEGIN_DRAG, self.OnBeginDrag)
        self.Bind(aui.EVT_AUINOTEBOOK_DRAG_DONE, self.OnDragDone)

    def OnClose(self, evt):
        evt.Veto()
        self.root.OnClose(None)

    def __iter__(self):
        count = self.GetPageCount()
        cur = 0
        while cur < count:
            r = self.GetPage(cur).GetWindow1()
            yield r
            cur += 1

    @property
    def items(self):
        return [os.path.join(i.dirname, i.filename) for i in self if i.dirname]

    def __contains__(self, name):
        dn, fn = os.path.split(name)
        return self.root.isOpen(fn, dn)

    def GotFocus(self, evt):
        evt.Skip()
        if self.GetPageCount():
            self.GetPage(self.GetSelection()).GetWindow1().SetFocus()

    def GNBI(self, i):
        if WHICHNB == 2:
            return self.imagelist[i]
        return i

    def GetCurrentPage(self):
        x = self.GetSelection()
        if x >= 0:
            return self.GetPage(x)
        return None

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
                #if win.GetWrapMode() == wx.STC_WRAP_NONE:
                #    self.parent.SetStatusText("", 1)
                #else:
                #    self.parent.SetStatusText("WRAP",1)
                self.root.OnDocumentChange(win, None)
                ## win.docstate.Show()

                _, flags = __main__.CARET_OPTION_TO_ID[__main__.caret_option]
                win.SetXCaretPolicy(flags, __main__.caret_slop*__main__.caret_multiplier)
                win.SetYCaretPolicy(flags, __main__.caret_slop)
                win.SetCaretWidth(__main__.CARET_WIDTH)
                if not win.loaded:
                    win.loadfile()

            self.root.timer.Start(10, wx.TIMER_ONE_SHOT)
            if event:
                event.Skip()
            if self.other_focus:
                wx.CallAfter(win.SetFocus)
                self.other_focus = 0
            else:
                self.root.dragger.justdragged = time.time()
            self._seen()
            ## print "pagechanged", new, old
        finally:
            self.calling = 0
#
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
        if hasattr(self.root.docpanel, 'recentlyclosed'):
            for i in __main__.DOCUMENT_LIST_OPTION_TO_ID2.itervalues():
                self.root.menubar.Check(i, 0)
        for i in __main__.MACRO_CLICK_OPTIONS.iterkeys():
            self.root.menubar.Check(i, 0)
        for i in __main__.SYNTAX_CHECK_DELAY_ID_TO_NUM:
            self.root.menubar.Check(i, 0)
        for i in __main__.REFRESH_DELAY_ID_TO_NUM:
            self.root.menubar.Check(i, 0)


        #Check for non-documents
        self.root.menubar.Check(__main__.lexers3[__main__.DEFAULTLEXER], 1)
        self.root.menubar.Check(__main__.TB_RMAPPING[__main__.TOOLBAR][1], 1)
        self.root.menubar.Check(__main__.CARET_OPTION_TO_ID[__main__.caret_option][0], 1)
        self.root.menubar.Check(__main__.TITLE_OPTION_TO_ID[__main__.title_option][0], 1)
        self.root.menubar.Check(__main__.DOCUMENT_LIST_OPTION_TO_ID[__main__.document_options], 1)
        if hasattr(self.root.docpanel, 'recentlyclosed'):
            self.root.menubar.Check(__main__.DOCUMENT_LIST_OPTION_TO_ID2[__main__.document_options2], 1)
        self.root.menubar.Check(__main__.MACRO_CLICK_TO_ID[__main__.macro_doubleclick], 1)
        self.root.menubar.Check(__main__.SYNTAX_CHECK_DELAY_NUM_TO_ID[__main__.HOW_OFTEN1], 1)
        self.root.menubar.Check(__main__.REFRESH_DELAY_NUM_TO_ID[__main__.HOW_OFTEN2], 1)

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
        self.root.menubar.Check(__main__.FETCH_M, win.fetch_methods)
        self.root.menubar.Enable(__main__.FETCH_M, win.showautocomp)
        self.root.menubar.Check(__main__.WRAPL, win.GetWrapMode() != wx.stc.STC_WRAP_NONE)
        self.root.menubar.Check(__main__.SLOPPY, win.sloppy)
        self.root.menubar.Check(__main__.SMARTPASTE, win.smartpaste)
        self.root.menubar.Check(__main__.S_WHITE, win.GetViewWhiteSpace())
        self.root.menubar.Check(__main__.S_LEND, win.GetViewEOL())
        ## self.root.menubar.Check(SORTBY, win.tree.tree.SORTTREE)
        self.root.menubar.Check(__main__.SAVE_CURSOR, win.save_cursor)
        self.root.menubar.Check(__main__.HIGHLIGHT_LINE, win.GetCaretLineVisible())
        self.root.menubar.SetHelpString(__main__.IDR, "Indent region %i spaces"%win.GetIndent())
        self.root.menubar.SetHelpString(__main__.DDR, "Dedent region %i spaces"%win.GetIndent())
        self.root.macropage.update_button(win)

#----------------- This deals with the tab swapping support. -----------------
    def RemovePage(self, index):
        BaseNotebook.RemovePage(self, index)
        self.root.dragger._RemoveItem(index)
        self._seen()

    def DeletePage(self, index):
        self.root.dragger._RemoveItem(index)
        page = self.GetPage(index)
        stc = page.GetWindow1()
        stc.docstate.Hide()
        stc.docstate.Destroy()
        BaseNotebook.DeletePage(self, index)
        self._seen()

    def AddPage(self, page, text, switch=1):
        which = __main__.GDI(text)
        BaseNotebook.AddPage(self, page, text, 0, self.GNBI(which))
        self.root.dragger._AddItem(text)
        if switch or self.GetPageCount() == 1:
            self.root.OnDocumentChange(page.GetWindow1())
            ## self.root.dragger._SelectItem(max(self.GetPageCount()-1, 0))
            self._seen()
        ## if switch:
            ## wx.CallAfter(self.SetSelection, self.GetPageCount()-1)

    def InsertPage(self, posn, page, text, switch=1):
        which = __main__.GDI(text)
        BaseNotebook.InsertPage(self, posn, page, text, 0, self.GNBI(which))
        self.root.dragger._InsertItem(posn, text)
        if self.GetSelection() == posn or switch:
            self.root.OnDocumentChange(page.GetWindow1())
        self._seen()
        ## if switch:
            ## wx.CallAfter(self.SetSelection, posn)

    def MoveTabPage(self, cp, i, selindex=None):
        #remove from original location, insert at destination
        ## print "getting information for page", cp
        if selindex is None:
            selindex = cp
        p = self.GetPage(cp)
        t = self.GetPageText(cp)
        try:
            self.Freeze()
            self.root.dragger.Freeze()
            self.other_focus = 1
            self.root.dragger.justdragged = time.time()
            self.root.starting = 1
            ## print "removing page", cp
            self.RemovePage(cp)
            if i >= self.GetPageCount():
                self.AddPage(p, t)
                ## print "appending page", i, self.GetPageCount()
            else:
                ## print "inserting page at", i
                self.InsertPage(i, p, t)
            if cp == selindex:
                ## print "selecting page"
                page = min(i, self.GetPageCount()-1)
                _callme = lambda page: (self.SetSelection(page),
                                   self.GetPage(page).GetWindow1().SetFocus(),
                                   self.root.dragger._SelectItem(page)
                                   )
        
                wx.CallAfter(_callme, page)
        finally:
            self.root.starting = 0
            self.root.dragger.Thaw()
            self.Thaw()

    def OnBeginDrag(self, evt):
        self.fr = evt.OldSelection
        evt.Skip()

    def OnDragDone(self, evt):
        i = evt.Selection
        cp = self.fr
        self.fr = None
        if cp is None:
            return
        self.MoveTabPage(cp, i)
        evt.Skip()

    def SetPageText(self, posn, text):
        self.root.dragger._RenameItem(posn, text)
        BaseNotebook.SetPageText(self, posn, text)
        self._seen()

    def SetPageImage(self, which, img):
        if WHICHNB == 2:
            self.SetPageBitmap(which, self.GNBI(img))
        else:
            BaseNotebook.SetPageImage(self, which, img)

    def _seen(self):
        if not self.cs:
            self.cs = 1
            wx.CallAfter(self._seen_)

    def _seen_(self):
        self.cs = 0
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

class setupmix:
    def setupcolumns(self, do=None):
        for i in xrange(self.GetColumnCount()-1, -1, -1):
            self.DeleteColumn(i)

        if do is None:
            if isinstance(self, MyLC):
                do = __main__.document_options
            else:
                do = __main__.document_options2
        if do&4:
            self.InsertColumn(0, "", width=20)
            self.InsertColumn(self.GetColumnCount(), "Path", format=wx.LIST_FORMAT_RIGHT)
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

        self.Bind(wx.EVT_SIZE, self._thisResize)

    def _thisResize(self, e):
        if e.GetSize()[1] < 32:
            return
        e.Skip()


class MyLC(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, setupmix):
    def __init__(self, parent, root):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT|wx.LC_VIRTUAL|wx.LC_SINGLE_SEL)#|wx.BORDER_NONE
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
        self.justdragged = 0

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
        index=event.GetIndex()
        if not self.justdragged or time.time()-self.justdragged > .25:
            l = lambda:(self.root.control.SetSelection(index),
                        self.root.control.GetPage(index).GetWindow1().SetFocus())
            wx.CallAfter(l)

    def OnBeginDrag(self, event):
        posn = event.GetIndex()
        if posn == -1:
            event.Skip()
            return

        a = self.root.control.GetPage(posn).GetWindow1()
        data = a.getlong()
        if not data:
            data = a.getshort()

        ## data = data.encode('ascii')
        d = wx.FileDataObject()
        d.AddFile(data)
        ## print d.GetFilenames()
        a = wx.DropSource(self)
        a.SetData(d)
        if a.DoDragDrop(wx.Drag_AllowMove|wx.Drag_CopyOnly):
            #we use a time so that users can (almost immediately) click on
            #another document to switch.
            self.justdragged = time.time()
            self.root.control.other_focus = 1

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
        wx.CallAfter(self.Select, index)

class RecentClosed(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, setupmix):
    def __init__(self, parent, root):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT|wx.LC_VIRTUAL)#|wx.BORDER_NONE
        listmix.ListCtrlAutoWidthMixin.__init__(self)

        self.setupcolumns()
        self.root = root

        self.items = []

        self.SetDropTarget(__main__.FileDropTarget(root))
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnActivate)
        wx.CallAfter(self.refresh)

    def GetSelectedList(self):
        lst = []
        x = self.GetFirstSelected()
        while x != -1:
            lst.append(x)
            x = self.GetNextSelected(x)
        lst = [-i-1 for i in lst]
        return lst

    def OnActivate(self, evt):
        lst = self.GetSelectedList()
        for i in lst:
            self.Select(-(i+1), 0)
        if len(lst):
            self.Select(-(lst[0]+1), 1)

        self.root.OnDrop([self.items[i] for i in lst])

    def OnGetItemText(self, index, col):
        if index >= len(self.items):
            return ''

        do = __main__.document_options2
        if do == 0:
            col = not col
        elif do == 2:
            col = 1

        index = -index-1

        if col == 0:
            return os.path.split(self.items[index])[1]
        return self.items[index]

    def refresh(self):
        self.items = self.root.lastused.keys()
        self.SetItemCount(len(self.items))
        self.Refresh()

class FakeRecentClosed(object):
    def __init__(self, parent):
        self.parent = parent
        self.items = __main__.root.control.items + __main__.root.lastused.keys()[::-1]
    def refresh(self):
        self.items = __main__.root.control.items + __main__.root.lastused.keys()[::-1]
        self.parent.table.refresh(self.parent.table.last_text)

die = None
last_checked = set([None])
last_extns = set([None])
def get_filenames(paths, extns, call_on_complete, refresh, token, startthread=1):
    global die, last_checked, last_extns
    if startthread:
        t = threading.Thread(target=get_filenames, args=(paths, extns, call_on_complete, refresh, token, 0))
        t.setDaemon(1)
        t.start()
        return

    # let's first dedupe and remove paths that have another path as their
    # prefix
    ptw = paths[:]
    i = 0
    while i < len(ptw):
        p = ptw[i]
        j = i+1
        while j < len(ptw):
            if p.startswith(ptw[j]):
                del ptw[j]
            elif ptw[j].startswith(p):
                ptw[i] = ptw[j]
                del ptw[j]
                break
            else:
                j += 1
        else:
            i += 1

    if set(last_checked) == set(ptw) and set(last_extns) == set(extns) and not refresh:
        return
    last_checked = set(ptw)
    last_extns = extns = set(extns)

    known_files = set()
    last = 0
    def key(i):
        p, c = os.path.split(i.lower())
        return c,p
    for path in ptw:
        for parent, dirnames, files in os.walk(path):
            if die != token:
                return
            # we're foing to ignore paths and files with dotted prefixes
            dirnames[:] = [i for i in dirnames if i[:1] != '.']
            known_files.update(os.path.join(parent,fil) for fil in files if fil[:1] != '.' and (('.' not in fil) or (fil.split('.')[-1].lower() in extns)))
            if refresh and len(known_files) - last >= 1000:
                wx.CallAfter(call_on_complete, sorted(known_files, key=key), refresh)
                last = len(known_files)
        if die != token:
            return
    # need to add recent documents to this list :)
    known_files = sorted(known_files, key=key)
    wx.CallAfter(call_on_complete, known_files, refresh, 1)

def gen_path_diff(p1, p2):
    # this function assumes that p1 and p2 are the same path except for some
    # single middle section
    # think paths of the form:
    # /src/svn/python/trunk/Lib/...
    # /src/svn/python/branches/release26-maint/Lib/...
    # the first one will return 'trunk' the second 'branches/release26-maint'
    ## p1 = os.path.split(p1)[0]
    ## p2 = os.path.split(p2)[0]
    lead = 0
    for i, (pp1, pp2) in enumerate(itertools.izip(p1, p2)):
        if pp1 == pp2:
            lead = i+1
        else:
            break
    trail = 0
    for i, (pp1, pp2) in enumerate(itertools.izip(p1[::-1], p2[::-1])):
        if pp1 == pp2:
            trail = i+1
        else:
            break
    sep = os.path.sep
    if lead + trail > len(p1):
        return ''
    leadf = p1.rfind(os.path.sep, 0, lead)
    trailf = p1.find(os.path.sep, len(p1)-trail)
    lead = (leadf != -1 and [leadf+1] or [lead])[0]
    trail = (trailf != -1 and [len(p1)-trailf] or [trail])[0]
    join = []
    if lead:
        join.append('..')
    join.append(p1[lead:len(p1)-trail])
    if trail:
        join.append('..')
    return os.path.sep.join(join)

class _vitems:
    def __init__(self, *args):
        self.parts = args
    def __len__(self):
        return sum(len(i) for i in self.parts)
    def __getitem__(self, key):
        if key > len(self):
            raise IndexError
        for part in self.parts:
            if key < len(part):
                return part[key]
            key -= len(part)

def vitems(part1, part2):
    part1 = list(part1)
    if not part1:
        return part2
    return _vitems(part1, part2)

COMPLICATED_AND_SLOW = 0

class WatchProject(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, setupmix):
    def __init__(self, parent, root):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT|wx.LC_VIRTUAL)
        listmix.ListCtrlAutoWidthMixin.__init__(self)
        self.AssignImageList(__main__.IMGLIST4, wx.IMAGE_LIST_SMALL)

        self.setupcolumns(5)
        self.root = root
        self.parent = parent

        self.items = []
        self.disp_items = []
        self.paths_to_watch = __main__.paths_to_watch
        self.extensions_to_watch = __main__.extensions_to_watch
        self.last_text = ''

        self.SetDropTarget(__main__.FileDropTarget(root))
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnActivate)
        wx.CallAfter(self.update_data, True)

    def add_path(self, path):
        self.paths_to_watch.append(path.rstrip(os.path.sep) + os.path.sep)
        self.update_data(True)

    def remove_paths(self, paths):
        paths = set(paths)
        self.paths_to_watch[:] = [p for p in self.paths_to_watch if p not in paths]
        self.update_data(True)

    def update_data(self, refresh=False):
        global die
        die = time.time()
        get_filenames(self.paths_to_watch, self.extensions_to_watch, self.got_new_data, refresh, die)

    def got_new_data(self, data, refresh=False, complete=False):
        self.items = data
        if refresh:
            self.refresh(self.last_text)
        if complete:
            __main__.root.SetStatusText("Finished adding %i files to Quick Browse."%len(data))
        else:
            print "Added %i files to Quick Browse"%len(data)

    def refresh(self, text):
        lcs = filtertable._lcsseq
        recent = self.parent.recentlyclosed.items
        self.last_text = text
        if not text:
            self.disp_items = vitems(recent, self.items)
        elif 0:
            items = itertools.chain(recent, self.items)
            text = os.path.sep.join(text.replace('\\', '/').replace('/', ' ').strip().split()).lower()
            self.disp_items = [k for k in (j for j in items if j) if lcs(k.lower(), text)]
        else:
            items = itertools.chain(recent, self.items)
            text = os.path.sep.join(text.replace('\\', '/').replace('/', ' ').strip().split()).lower()
            def key(i, x=text[::-1], score=filtertable._sseq_score):
                # we're going to prefer filename matches over path matches
                return score(i[::-1].lower(), x), i
            self.disp_items = sorted(set(k for k in (j for j in items if j) if lcs(k.lower(), text)), key=key)

        self.SetItemCount(len(self.disp_items))
        self.Refresh()

    def OnGetItemText(self, index, col):
        if col == 0:
            return ''
        col -= 1
        di = self.disp_items
        if index >= len(di):
            return ''

        cd, cf = os.path.split(di[index])
        if col == 1:
            return cf

        disp = ''
        if index > 0:
            # check previous path
            od, of = os.path.split(di[index-1])
            if cf == of:
                disp = gen_path_diff(cd, od)
        if (not disp) and (index+1) < len(di):
            # check next path
            od, of = os.path.split(di[index+1])
            if cf == of:
                disp = gen_path_diff(cd, od)
        disp = disp or cd
        return disp

    def GetSelectedList(self):
        lst = []
        x = self.GetFirstSelected()
        while x != -1:
            lst.append(x)
            x = self.GetNextSelected(x)
        return lst

    def OnActivate(self, evt):
        lst = self.GetSelectedList()
        di = self.disp_items
        self.root.OnDrop([di[i] for i in lst])

    def OnGetItemAttr(self, item):
        it = self.disp_items[item]
        if it in self.root.control:
            return attr2
        elif it in self.root.lastused:
            return attr1
        return None

    def OnGetItemImage(self, item):
        return __main__.GDI(os.path.split(self.disp_items[item])[1])

def Button(*args, **kwargs):
    help = kwargs.pop('help', None)
    b = wx.Button(*args, **kwargs)
    if help:
        b.SetHelpText(help)
    return b

class DocumentPanel(wx.Panel):
    def __init__(self, parent, root):
        wx.Panel.__init__(self, parent, -1)

        self.root = root
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.documentlist = MyLC(self, root)
        sizer.Add(self.documentlist, 1, wx.EXPAND|wx.ALL, 2)

        self.filter = wx.TextCtrl(self, -1, "", style=wx.WANTS_CHARS)
        self.Bind(wx.EVT_TEXT, self.OnText)
        sizer.Add(self.filter, 0, wx.EXPAND|wx.ALL, 2)

        sz3 = wx.BoxSizer(wx.HORIZONTAL)

        b = Button(self, -1, "+", help="Add paths to watch", style=wx.BU_EXACTFIT)
        sz3.Add(b, 0, wx.ALL, 2)
        self.Bind(wx.EVT_BUTTON, self.OnPlus, b)

        b = Button(self, -1, "-", help="Remove paths to watch", style=wx.BU_EXACTFIT)
        sz3.Add(b, 0, wx.ALL, 2)
        self.Bind(wx.EVT_BUTTON, self.OnMinus, b)

        b = Button(self, -1, "R", help="Refresh file list", style=wx.BU_EXACTFIT)
        sz3.Add(b, 0, wx.ALL, 2)
        self.Bind(wx.EVT_BUTTON, self.OnRefresh, b)

        sz3.Add(wx.StaticText(self, -1, ""), 1, wx.EXPAND|wx.ALL, 2)

        b = Button(self, -1, "X", help="Remove file from history", style=wx.BU_EXACTFIT)
        sz3.Add(b, 0, wx.ALL, 2)
        self.Bind(wx.EVT_BUTTON, self.OnRemoveHistory, b)

        sz3.Add(wx.StaticText(self, -1, ""), 1, wx.EXPAND|wx.ALL, 2)

        b = Button(self, -1, "E+", help="Add extensions to watch", style=wx.BU_EXACTFIT)
        sz3.Add(b, 0, wx.ALL, 2)
        self.Bind(wx.EVT_BUTTON, self.OnAddExt, b)

        b = Button(self, -1, "E-", help="Remove extensions to watch", style=wx.BU_EXACTFIT)
        sz3.Add(b, 0, wx.ALL, 2)
        self.Bind(wx.EVT_BUTTON, self.OnRemExt, b)

        sizer.Add(sz3, 0, wx.EXPAND|wx.ALL, 2)


        self.table = WatchProject(self, root)
        sizer.Add(self.table, 1, wx.EXPAND|wx.ALL, 2)

        self.recentlyclosed = FakeRecentClosed(self)
        if __main__.show_recent:

            s2 = wx.BoxSizer(wx.HORIZONTAL)

            s2.Add(wx.StaticText(self, -1, "Recently Open:"), 0,
                    wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 6)

            btn = wx.Button(self, -1, "Remove")
            btn.SetToolTipString("Remove the selected recent document from the list")
            self.Bind(wx.EVT_BUTTON, self.OnButton, btn)

            s2.Add(wx.StaticText(self, -1, " "), 1, wx.EXPAND)

            s2.Add(btn)

            sizer.Add(s2, 0, wx.ALL|wx.EXPAND, 4)

            self.recentlyclosed = RecentClosed(self, root)
            sizer.Add(self.recentlyclosed, 1, wx.EXPAND|wx.ALL, 2)

        self.SetSizer(sizer)

    def OnText(self, evt):
        self.table.refresh(self.filter.GetValue())

    def OnPlus(self, evt):
        dlg = wx.DirDialog(self, "Choose a directory to add to the quick browse listing:", style=wx.DD_DEFAULT_STYLE, pos=(0,0))
        if dlg.ShowModal() == wx.ID_OK:
            self.table.add_path(dlg.GetPath())
        dlg.Destroy()

    def OnMinus(self, evt):
        dlg = wx.MultiChoiceDialog(self, "Select paths you would like to remove from the\nlist of paths you are currently monitoring.",
            "Remove Paths...", self.table.paths_to_watch, pos=(0,0))

        if (dlg.ShowModal() == wx.ID_OK):
            selections = dlg.GetSelections()
            strings = [self.table.paths_to_watch[x] for x in selections]
            self.table.remove_paths(strings)
        dlg.Destroy()

    def OnRefresh(self, evt):
        self.table.update_data(True)

    def OnAddExt(self, evt):
        dlg = wx.TextEntryDialog(
                self, 'Please add extensions you would like to watch',
                'Add extensions to watch', '', pos=(0,0))
        if dlg.ShowModal() == wx.ID_OK:
            self.table.extensions_to_watch[:] = list(
                set(dlg.GetValue().replace(';', ' ').replace('.', ' ').replace(',', ' ').split()) |
                set(self.table.extensions_to_watch))
            self.table.update_data(True)
        dlg.Destroy()

    def OnRemExt(self, evt):
        extensions = sorted(self.table.extensions_to_watch)
        dlg = wx.MultiChoiceDialog(self, "Select extensions you would like to remove from the\nlist of extensions you are currently monitoring.",
            "Remove Extensions...", extensions, pos=(0,0))
        if dlg.ShowModal() == wx.ID_OK:
            selections = dlg.GetSelections()
            self.table.extensions_to_watch[:] = [i for i in extensions if i not in set(extensions[x] for x in selections)]
            self.table.update_data(True)
        dlg.Destroy()

    def OnRemoveHistory(self, evt):
        for i in self.table.GetSelectedList():
            try:
                del self.root.lastused[self.table.disp_items[i]]
            except (KeyError, IndexError):
                pass
        self._refresh()

    def OnButton(self, evt):
        rc = self.recentlyclosed
        lst = rc.GetSelectedList()
        for i in lst:
            rc.Select(-(i+1), 0)
        if len(lst):
            rc.Select(-(lst[0]+1), 1)

        for i in lst:
            try:
                del self.root.lastused[rc.items[i]]
            except (KeyError, IndexError):
                pass
        self._refresh()

    def _refresh(self):
        if hasattr(self, 'recentlyclosed'):
            self.recentlyclosed.refresh()
        self.documentlist._Refresh()

    def _setcolumn(self):
        if hasattr(self, 'recentlyclosed'):
            self.recentlyclosed.setupcolumns()
        self.documentlist.setupcolumns()

def _MyLC(parent, root):
    dp = DocumentPanel(parent, root)
    dragger = dp.documentlist
    return dp, dragger

#
