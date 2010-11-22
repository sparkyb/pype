"""
This is a test version of an alternate find in files ui.
"""

# Initial version for PyPE
# Based on work from Josiah Carlson and others.
# License GPL
# Further work by parameter@sourceforge (Dave Schuyler).

from wx import ImageFromStream, BitmapFromImage, Yield
from wx.stc import StyledTextCtrl
import cStringIO

import wx
import wx.lib.mixins.listctrl as listmix
import wx.lib.scrolledpanel as scrolled
import os
import re
import fnmatch
import posixpath
import time
import tokenize
import cStringIO
import compiler

newlines = re.compile(r'((\r\n)|(\r)|(\n))')
quotedPattern=re.compile(
    r'''((?:"(?:[^\\"]*(?:\\.[^\\"]*)*)["])|(?:'(?:[^\\']*(?:\\.[^\\']*)*)[']))''')
commentedPattern=re.compile(r"[^#]*#(.*)$")

def fixnewlines(string):
    return newlines.sub('\n', string)

def namematches(name, include, exclude):
    for extn in include:
        if fnmatch.fnmatch(name, extn):
            for i in exclude:
                if fnmatch.fnmatch(name, i):
                    return 0
            else:
                return 1
    return 0

columns = (
    (0, "", 0, 0),
    (1, "Path", 200, 0),
    (2, "Filename", 100, 0),
    (3, "L#", 40, wx.LIST_FORMAT_RIGHT),
    (4, "Item", 550, 0))

OP = tokenize.OP
NAME = tokenize.NAME
NTOK = tokenize.N_TOKENS
NEWL = tokenize.NEWLINE
include_re = re.compile('^#include\s+"([^"\\n\\r ]+)".*?$', re.MULTILINE)
PY = 0
C = 1

enable_options = ['Directories', 'Tags in Directories']

def find_imports(txt):
    if 'import' in txt:
        #probably a python file
        #this part runs around 450k/second on my 2.8 ghz P4, fast enough.
        imports = []
        parname = ''
        curname = ''
        ok = 0
        x = 0
        for typ, token, st, en, lin in tokenize.generate_tokens(cStringIO.StringIO(txt).readline):
            x += 1
            if x >= 100:
                x = 0
                Yield()
            if typ == NAME:
                if token == 'from':
                    parname = ''
                    curname = ''
                    ok = 1
                elif token == 'import':
                    parname = curname
                    curname = ''
                    ok = 1
                elif ok:
                    curname += token
            elif typ == OP:
                if token == '.':
                    curname += '.'
                elif token in '*,':
                    if parname and curname:
                        imports.append(parname + '.' + curname)
                    elif token == '*' and parname:
                        imports.append(parname)
                    elif curname:
                        imports.append(curname)
                    curname = ''
            elif typ == NEWL or typ >= NTOK:
                if parname and curname:
                    imports.append(parname + '.' + curname)
                elif curname:
                    imports.append(curname)
                parname = ''
                curname = ''
                ok = 0
        return PY, [i for i in imports if len(i) != i.count('.')]
    elif '#include' in txt:
        #probably a c/c++ file
        return C, [i for i in include_re.findall(txt)]
    return -1, []

#-----------------------------------------------------------------------------

class FoundTable(wx.ListCtrl, listmix.ColumnSorterMixin):#, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, columns = columns):
        wx.ListCtrl.__init__(
            self, parent, -1,
            style=wx.LC_REPORT|wx.LC_VIRTUAL|wx.LC_HRULES|wx.LC_VRULES)
        self.parent = parent
        
        self.imageList = wx.ImageList(16, 16)
        self.sm_up = self.imageList.Add(getSmallUpArrowBitmap())
        self.sm_dn = self.imageList.Add(getSmallDnArrowBitmap())
        self.SetImageList(self.imageList, wx.IMAGE_LIST_SMALL)


        for i in columns:
            if 0:
                info = wx.ListItem()
                info.SetMask(
                    wx.LIST_MASK_TEXT|wx.LIST_MASK_IMAGE|wx.LIST_MASK_FORMAT)
                info.SetImage(-1)
                info.SetText(i[1])
                info.SetAlign(i[3])
                self.InsertColumnInfo(i[0], info)
            else:
                self.InsertColumn(i[0], i[1], i[3])
            self.SetColumnWidth(i[0], i[2])

        self.data=[]
        self.cache=[]
        listmix.ColumnSorterMixin.__init__(self, len(columns))

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        #self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemDeselected)
        self.pattern = None

    def setData(self, arrayOfTuples, copy=1):
        if copy:
            self.data=arrayOfTuples[:]
        else:
            self.data=arrayOfTuples
        self.cache = [os.path.split(i[0]) for i in self.data]
        self.SetItemCount(len(arrayOfTuples))
        self.Refresh()

    def Clear(self):
        self.data=[]
        self.cache=[]
        self.SetItemCount(0)
        self.DeleteAllItems()
        self.Refresh()
    
    def AppendEntry(self, tuple):
        """
        ((filename, line, line contents, extra), *)
        """
        self.data.append(tuple)
        self.cache.append(os.path.split(tuple[0]))
        self.SetItemCount(len(self.data))
    
    def ExtendEntries(self, array):
        self.data.extend(array)
        self.cache.extend([os.path.split(i[0]) for i in array])
        self.SetItemCount(len(self.data))

    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetListCtrl(self):
        return self
    
    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetSortImages(self):
        return (self.sm_dn, self.sm_up)
    
    def GetColumnSorter(self):
        # Override listctrl mixin default to do nothing.
        pass
    
    def SortItems(self, *args, **kwargs):
        # Override listctrl mixin
        col=self._col
        ascending = self._colSortFlag[col]
        col -= 1
        
        if col in (0,1):
            ops = os.path.split
            fcn = lambda a:ops(a[0])[col]
        else:
            fcn = lambda a:a[col-1]
        
        def cmpf(a,b):
            return cmp(fcn(a), fcn(b))
            
        if ascending:
            self.data.sort(cmpf)
            self.cache = [os.path.split(i[0]) for i in self.data]
        else:
            self.data.reverse()
            self.cache.reverse()
        
        self.Refresh()

    def OnItemSelected(self, event):
        self.currentItem = event.m_itemIndex

    def OnItemActivated(self, event):
        self.currentItem = event.m_itemIndex
        path = self.GetItem(self.currentItem, 1).GetText()
        file = self.GetItem(self.currentItem, 2).GetText()
        line = self.GetItem(self.currentItem, 3).GetText()
        data = self.GetItem(self.currentItem, 4).GetText()
        self.parent.OpenFound(os.path.join(path, file), int(line), self.pattern, ('\\n' in data) and len(data.encode('utf-8')))

    def OnGetItemText(self, item, col):
        if col == 0:
            return ''
        if col in (1,2):
            return self.cache[item][col-1]
        return "%s" % (self.data[item][col-2],)

#-----------------------------------------------------------------------------

class FoundText(wx.ListBox):
    def __init__(self, parent):
        wx.ListBox.__init__(
            self, parent, -1,
            style=wx.LB_SINGLE|wx.LB_NEEDED_SB)
        self.parent = parent
        wx.EVT_LISTBOX_DCLICK(parent, self.GetId(), self.OnItemActivated)
        self.last = ''
        self.pattern = None

    def setData(self, arrayOfTuples):
        self.Clear()
        self.ExtendEntries(arrayOfTuples)
    
    def AppendEntry(self, tuple):
        #tuple is (filename, line, line contents, extra)
        if tuple[0] != self.last:
            #set text color
            self.Append(tuple[0])
            self.last = tuple[0]
        self.Append("  %s: %s"%tuple[1:3])
    
    def ExtendEntries(self, array):
        a = []
        for tuple in array:
            if tuple[0] != self.last:
                #set text color
                a.append(tuple[0])
                self.last = tuple[0]
            a.append("  %s: %s"%tuple[1:3])
        
        self.InsertItems(a, self.GetCount())

    def OnItemActivated(self, event):
        selected = self.GetSelection()
        if selected < 0:
            return
        cur = selected
        while (cur > 0) and (self.GetString(cur)[0] == ' '):
            cur -= 1
        file = self.GetString(cur)
        line = 1
        a = self.GetString(selected) 
        if a[0] == ' ':
            line = int(a.split(':', 1)[0])
        self.parent.OpenFound(file, int(line), self.pattern, ('\\n' in a) and len(a.encode('utf-8')))

#---------------------------------------------------------------------------

class FoundTree(wx.TreeCtrl):
    def __init__(self, parent):
        wx.TreeCtrl.__init__(self, parent,
                             style=wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT | wx.TR_NO_LINES)
        self.parent = parent

        isz = (16,16)
        il = wx.ImageList(isz[0], isz[1])
        self.img0 = fldridx     = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER, isz))
        self.img1 = fldropenidx = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN,   wx.ART_OTHER, isz))
        i = wx.EmptyImage(*isz)
        i.SetData(isz[0]*isz[1]*3*'\xff')
        self.img2 = fileidx     = il.Add(wx.BitmapFromImage(i))

        self.SetImageList(il)
        self.il = il

        self.root = self.AddRoot("The hidden root item")
        self.SetItemImage(self.root, fldridx, wx.TreeItemIcon_Normal)
        self.SetItemImage(self.root, fldropenidx, wx.TreeItemIcon_Expanded)

        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate, self)
        
        self.last = ''
        self.lasti = None
        self.pattern = None
    
    def setData(self, arrayOfTuples):
        self.Clear()
        self.ExtendEntries(arrayOfTuples)
    
    def Clear(self):
        self.DeleteAllItems()
    
    def AppendEntry(self, tuple):
        if tuple[0] != self.last:
            self.last = tuple[0]
            self.lasti = self.AppendItem(self.root, self.last)
            self.SetItemImage(self.lasti, self.img0, wx.TreeItemIcon_Normal)
            self.SetItemImage(self.lasti, self.img1, wx.TreeItemIcon_Expanded)
            self.Expand(self.lasti)
            #set color of item
        it = self.AppendItem(self.lasti, " %s: %s"%(tuple[1:3]))
        self.SetItemImage(it, self.img2, wx.TreeItemIcon_Normal)
    
    def ExtendEntries(self, arrayOfTuples):
        for i in arrayOfTuples:
            self.AppendEntry(i)

    def OnActivate(self, event):
        item = event.GetItem()
        parent = self.GetItemParent(item)
        
        if parent == self.root:
            event.Skip()
            return
        file = self.GetItemText(parent)
        data = self.GetItemText(item)
        line = int(data.split(':')[0].strip())
        self.parent.OpenFound(file, line, self.pattern, ('\\n' in data) and len(data.encode('utf-8')))

#-----------------------------------------------------------------------------

viewoptions = {'table': FoundTable,
               'tree' : FoundTree,
               'text' : FoundText}

class FindInFiles(wx.Panel):
    def __init__(self, parent, root):
        wx.Panel.__init__(self, parent, -1)
        
        self.found = []
        self.parent = parent
        self.root = root

        self.running = 0
        self.stopping = 0
        self.starting = 0

        winids = []

        controlsWindow = wx.SashLayoutWindow(
            self, -1, wx.DefaultPosition, (200, 30),
            wx.NO_BORDER|wx.SW_3D)
        controlsWindow.SetOrientation(wx.LAYOUT_VERTICAL)
        controlsWindow.SetAlignment(wx.LAYOUT_LEFT)
        controlsWindow.SetSashVisible(wx.SASH_RIGHT, True)
        self.controlsWindow = controlsWindow
        winids.append(controlsWindow.GetId())

        fc = self.readPreferences()
        self.scope = fc['scope']

        self.viewResultsAs = fc['view']
        
        self.resultsWindow = viewoptions.get(fc['view'], FoundText)(self)
            
        winids.append(self.resultsWindow.GetId())

        self.Bind(
            wx.EVT_SASH_DRAGGED_RANGE, self.OnSashDrag,
            id=min(winids), id2=max(winids)
            )

        self.Bind(wx.EVT_SIZE, self.OnSize)

        self.scrolledPanel = scrolled.ScrolledPanel(controlsWindow, -1,
            style=wx.TAB_TRAVERSAL|wx.SUNKEN_BORDER)
        SLF = self.scrolledPanel

        def static(text, style=wx.ALIGN_LEFT):
            return wx.StaticText(SLF, -1, text, style=style)

        def checkb(text, val=0, style=wx.NO_BORDER):
            a = wx.CheckBox(SLF, -1, text, style=style)
            a.SetValue(val)
            return a

        def combobox(ch, d=''):
            a = wx.ComboBox(SLF, -1, choices=ch, style=wx.CB_DROPDOWN,
                size=(100, 1))
            if ch: a.SetSelection(0)
            elif d: a.SetValue(d)
            return a

        def button(name, fcn):
            id = wx.NewId()
            a = wx.Button(SLF, id, name)
            wx.EVT_BUTTON(SLF, id, fcn)
            return a

        #------------------------------

        gbs = self.gbs = wx.GridBagSizer(5, 5)

        outsideBorder=5
        lastColumn=4
        editBoxSpan=(1, lastColumn-1)
        allSpan=(1, lastColumn+1)
        row=0

        gbs.Add(static("Search for:"), (row,0),
                flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.TOP,
                border=outsideBorder)
        self.search = combobox(fc['search'])
        gbs.Add(self.search, (row,1), editBoxSpan,
                flag=wx.EXPAND|wx.TOP,
                border=outsideBorder)
        self.b=button("Start Search", self.OnFindButtonClick)
        self.b.SetDefault()
        gbs.Add(self.b, (row,lastColumn),
            flag=wx.ALIGN_LEFT|wx.RIGHT|wx.TOP,
            border=outsideBorder)

        row+=1
        gbs.Add(static("Within:"), (row,0),
            flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT,
            border=outsideBorder)
        scopes = [
            'Selected Text',
            'Current File',
            'Current File with Includes',
            '',
            'Open Files',
            #'Project',   #perhaps if/when PyPE has projects
            #'Workspace', #perhaps for PyPE 2.1
            'Directories',
            'Tags in Directories',
            #'',
            #'Dictionary', #yikes, requires shipping a dictionary or the internet requirements.
            #'Internet',   #yikes, requires shipping urllib, a parser, etc.
            ]
        self.scopeChoice = wx.Choice(self.scrolledPanel, -1,
            choices = scopes)
        try:
            self.scopeChoice.SetSelection(scopes.index(fc['scope']))
        except:
            self.scopeChoice.SetSelection('Directories')
        self.Bind(wx.EVT_CHOICE, self.OnScopeChoice, self.scopeChoice)
        gbs.Add(self.scopeChoice, (row,1), editBoxSpan,
                flag=wx.EXPAND)

        opt_sizer = wx.BoxSizer(wx.VERTICAL)
        self.cs = checkb("Case sensitive", fc['case'])
        self.re = checkb("Regular Expression", fc['regex'])
        self.multiline = checkb("Multiline", fc['multiline'])
        opt_sizer.Add(self.cs, flag=wx.ALIGN_LEFT|wx.TOP, border=2)
        opt_sizer.Add(self.re, flag=wx.ALIGN_LEFT|wx.TOP, border=2)
        opt_sizer.Add(self.multiline, flag=wx.ALIGN_LEFT|wx.TOP, border=2)
        opt_sizer.Layout()
        row+=1
        gbs.Add(opt_sizer, (row,1), (1,2),
            wx.RIGHT, outsideBorder)

        opt_sizer2 = wx.BoxSizer(wx.VERTICAL)
        self.ww = checkb("Whole Word", fc['whole_word'])
        self.quoted = checkb("Quoted", fc['quoted'])
        self.commented = checkb("Commented", fc['commented'])
        opt_sizer2.Add(self.ww, flag=wx.ALIGN_LEFT|wx.TOP, border=2)
        opt_sizer2.Add(self.quoted, flag=wx.ALIGN_LEFT|wx.TOP, border=2)
        opt_sizer2.Add(self.commented, flag=wx.ALIGN_LEFT|wx.TOP, border=2)
        opt_sizer2.Layout()
        #row+=1
        gbs.Add(opt_sizer2, (row,3), (1,2),
            wx.RIGHT, outsideBorder)

        row+=1
        self.line = wx.StaticLine(
            self.scrolledPanel, -1, style=wx.LI_HORIZONTAL)
        gbs.Add(self.line, (row,0), allSpan,
            wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 10)

        row+=1
        gbs.Add(
            static("Separate multiple directories and criteria with ; (semicolons)"),
            (row,1), (1,lastColumn), flag=wx.ALIGN_LEFT)

        row+=1
        gbs.Add(static("Directories:"), (row,0),
            flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT,
            border=outsideBorder)
        self.sdirs = combobox(fc['dirs'])
        gbs.Add(self.sdirs, (row,1), editBoxSpan, flag=wx.EXPAND)
        self.add_path = button("Add Path", self.OnDirButtonClick)
        gbs.Add(self.add_path, (row,lastColumn),
            flag=wx.ALIGN_LEFT|wx.RIGHT,
            border=outsideBorder)

        row+=1
        gbs.Add(static("Include:"), (row,0),
                flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT,
                border=outsideBorder)
        self.include = combobox(fc['include'])
        gbs.Add(self.include, (row,1), editBoxSpan,
                flag=wx.EXPAND)

        row+=1
        gbs.Add(static("Exclude:"), (row,0),
                flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT,
                border=outsideBorder)
        self.exclude = combobox(fc['exclude'])
        gbs.Add(self.exclude, (row,1), editBoxSpan,
                flag=wx.EXPAND)

        row+=1
        self.ss = checkb("Search Subdirectories", fc['search_sub_dirs'])
        gbs.Add(self.ss, (row,1), (1,lastColumn),
            flag=wx.ALIGN_LEFT|wx.BOTTOM,
            border=outsideBorder)

        row+=1
        self.line = wx.StaticLine(
            self.scrolledPanel, -1, style=wx.LI_HORIZONTAL)
        gbs.Add(self.line, (row,0), allSpan,
            wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 10)

        row+=1
        gbs.Add(static("View Results As:"), (row,0),
            flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT,
            border=outsideBorder)
        #views=['table', 'text', 'tree']
        views=['table', 'text', 'tree']
        self.viewChoice = wx.Choice(self.scrolledPanel, -1,
            choices = views)
        self.viewChoice.SetSelection(views.index(fc['view']))
        self.Bind(wx.EVT_CHOICE, self.OnViewChoice, self.viewChoice)
        gbs.Add(self.viewChoice, (row,1), editBoxSpan,
                flag=wx.EXPAND|wx.TOP,
                border=outsideBorder)
        
        self.enable_controls = [self.sdirs, self.add_path, self.ss]
        self.checkscope()
        #------------------------------

        #gbs.AddGrowableRow(0)
        gbs.AddGrowableCol(1)

        self.scrolledPanel.SetSizerAndFit(gbs)
        self.scrolledPanel.SetAutoLayout(True)
        self.scrolledPanel.SetupScrolling()

        cwSizer = wx.BoxSizer(wx.HORIZONTAL)
        cwSizer.Add(self.scrolledPanel, 1, wx.EXPAND)
        self.controlsWindow.SetSizerAndFit(cwSizer)
        self.controlsWindow.SetAutoLayout(True)
        self.controlsWindow.Layout()
        #HACK:
        minSize=[i+40 for i in self.controlsWindow.GetMinSize()]
        self.controlsWindow.SetDefaultSize(minSize)
        parent.SetClientSize(self.GetSize())

        #------------------------------

        self.SetAutoLayout(True)
        tid = wx.NewId()
        self.timer = wx.Timer(self, tid)
        wx.EVT_TIMER(self, tid, self.OnFindButtonClick)

    #-------------------------------------------------------------------------

    def getfn(self, win):
        if win.dirname and win.filename:
            return os.path.join(win.dirname, win.filename)
        else:
            return '<untitled %i>'%win.NEWDOCUMENT
    
    def OnScopeChoice(self, event):
        scope=event.GetString()
        ## print 'scope', scope
        if self.scope != scope:
            self.scope=scope
            self.savePreferences()
        
        self.checkscope()
    
    def checkscope(self):
        enable = self.scopeChoice.GetStringSelection() in enable_options
        for i in self.enable_controls:
            i.Enable(enable)

    def OnViewChoice(self, event):
        view=event.GetString()
        if self.viewResultsAs != view:
            self.viewResultsAs=view
            self.savePreferences()
            #toss old results window
            x = self.resultsWindow.pattern 
            self.resultsWindow.Destroy()
            #create new results window
            self.resultsWindow = viewoptions.get(view, FoundText)(self)
            self.resultsWindow.pattern = x
            self.Bind(wx.EVT_SASH_DRAGGED_RANGE, self.OnSashDrag, self.resultsWindow)
            #populate new results window
            self.resultsWindow.setData(self.found)
            self.OnSize(event)

    def OnSashDrag(self, event):
        if event.GetDragStatus() == wx.SASH_STATUS_OUT_OF_RANGE:
            self.log.write('drag is out of range')
            return

        eobj = event.GetEventObject()

        if eobj is self.controlsWindow:
            self.controlsWindow.SetDefaultSize((event.GetDragRect().width, 1000))
        elif eobj is self.resultsWindow:
            self.resultsWindow.SetDefaultSize((event.GetDragRect().width, 1000))

        wx.LayoutAlgorithm().LayoutWindow(self, self.resultsWindow)
        #self.controlsWindow.Layout()
        self.resultsWindow.Refresh()

    def OnSize(self, event):
        wx.LayoutAlgorithm().LayoutWindow(self, self.resultsWindow)

    def OnClear(self, e):
        print "OnClear"
        self.results.Clear()

    def OnExit(self, e):
        print "OnExit"

    def OpenFound(self, file, line, pattern, multiline):
        if file[:1] == '<':
            #untitled files
            a = self.root.getPositionAbsolute(file, 1)
            if a == -1:
                return
            self.root.control.SetSelection(a)
        else:
            self.root.OnDrop([file], 1)
        a = self.root.control.GetSelection()
        if a > -1:
            line -= 1
            stc = self.root.control.GetPage(a).GetWindow1()
            start = 0
            end = stc.GetLineEndPosition(line)
            if line != 0:
                start = stc.GetLineEndPosition(line-1)+len(stc.format)
            
            #handle overflow
            eml = min(end+multiline, stc.GetLength())
            
            if multiline:
                t = fixnewlines(stc.GetTextRange(start, eml))
            else:
                t = stc.GetLine(line)
            grp = pattern(t)
            if grp != None:
                end =   grp.end()   + start
                start = grp.start() + start
                if stc.format == '\r\n':
                    #handle line ending fixing
                    end += grp.group().count('\n')
            stc.SetSelection(start, end)
            stc.SetFocus()

    def OnDirButtonClick(self, e):
        dlg = wx.DirDialog(self, "Choose a directory", style=wx.DD_DEFAULT_STYLE)
        a = dlg.ShowModal()
        if a == wx.ID_OK:
            a = self.sdirs.GetValue()
            if a:
                self.sdirs.SetValue(a+';'+dlg.GetPath())
            else:
                self.sdirs.SetValue(dlg.GetPath())
        dlg.Destroy()

        self.savePreferences()

    def OnFindButtonClick(self, e):
        global spaces_per_tab
        if self.stopping:
            #already stopping
            return
        elif self.running:
            #running, we want to try to stop
            self.stopping = 1
            self.b.SetLabel("Start Search")
            return

        if e.GetId() == self.b.GetId():
            if self.starting:
                #previously was waiting to start due to an
                #external yield, abort waiting and cancel
                #search
                self.starting = 0
                self.b.SetLabel("Start Search")
                return
        elif not self.starting:
            #I was a waiting timer event, but I don't
            #need to start anymore
            return

        spaces_per_tab = self.root.getglobal('spaces_per_tab')
        #try to start
        self.starting = 1
        self.b.SetLabel("Stop Search")

        try:
            wx.Yield()
        except:
            print "excepted", 1
            #would have tried to start while in another function's
            #wxYield() call.  Will wait 100ms and try again
            self.timer.Start(100, wx.TIMER_ONE_SHOT)
            return

        self.savePreferences()

        #am currently the topmost call, so will continue.
        self.starting = 0
        self.running = 1
        wx.Yield()

        pattern = self.search.GetValue()
        paths = self.sdirs.GetValue().split(';')
        include = self.include.GetValue().split(';')
        exclude = self.exclude.GetValue().split(';')
        caseSensitive = self.cs.IsChecked()
        wholeWord = self.ww.IsChecked()
        self.checkComment = self.commented.IsChecked()
        self.checkQuoted = self.quoted.IsChecked()
        multiline = self.multiline.IsChecked()
        subd = self.ss.IsChecked()

        #python strings
        if pattern and pattern[-1] in ['"', "'"]:
            try:
                pattern = [i for i in compiler.parse(str(pattern)).getChildren()[:1] if isinstance(i, basestring)][0]
            except Exception, e:
                pass
        
        multiline = multiline or '\n' in pattern
        
        if not self.re.IsChecked():
            pattern = re.escape(pattern)
        
        if wholeWord:
            pattern = "\\b%s\\b"%(pattern,)
        
        if caseSensitive:
            pattern = re.compile(pattern)
        else:
            pattern = re.compile(pattern, re.IGNORECASE)

        self.pattern = pattern
        self.resultsWindow.Clear()
        self.resultsWindow.pattern = pattern.search

        if multiline:
            searchFile = self.searchFileMultiline
        else:
            searchFile = self.searchFileEachLine
        self.found = found = []
        fileCount = 0
        hitFileCount = 0
        ss = "Found %i instances in %i files out of %i files %s%s."
        
        ch = self.scope.lower().replace(' ', '_')
        fcn = self.directories
        if hasattr(self, ch):
            fcn = getattr(self, ch)
        
        if ch not in ('tags_in_directories', 'directories'):
            paths = ('',)
        startTime=time.time()
        for path in paths:
            wx.Yield()
            if not self.running:
                break
            for filename, data in fcn(path, subd, include, exclude):
                self.root.SetStatusText(ss%(len(found), hitFileCount, fileCount, "so far ", '"'+filename+'"'), log=0)
                fileCount+=1
                wx.Yield()
                if self.stopping:
                    break
                r = searchFile(filename, data)
                if len(r):
                    hitFileCount+=1
                found += r
                self.resultsWindow.ExtendEntries(r)
        if self.stopping:
            self.stopping = 0
            self.root.SetStatusText('Find in files cancelled.')
            # stopped by a button press
        else:
            self.running = 0
            self.root.SetStatusText(ss%(len(found), hitFileCount, fileCount,
                "checked (in %.2f seconds)"%(time.time()-startTime,), ""))
        self.b.SetLabel("Start Search")
        self.stopping = 0
        self.running = 0
        self.starting = 0
        self.found = found

#--------------------------- scopes for searching ----------------------------

    def current_file(self, *args):
        try:
            _, win = self.root.getNumWin()
            yield self.getfn(win), fixnewlines(StyledTextCtrl.GetText(win))
        except cancelled:
            pass
    
    def current_file_with_includes(self, path, subdirs, include, exclude):
        try:
            _, win = self.root.getNumWin()
            t = fixnewlines(StyledTextCtrl.GetText(win))
            yield self.getfn(win), t
            
            typ, lst = find_imports(t)
            if typ == C:
                for pth in lst:
                    a = os.path.join(win.dirname, pth)
                    if os.path.isfile(a):
                        if namematches(a.split('/')[-1], include, exclude):
                            try:
                                x = self.root.GetPositionAbsolute(a)
                                if x != -1:
                                    t = StyledTextCtrl.GetText(self.root.GetPage(x).GetWindow1())
                                else:
                                    t = open(a, 'rb').read()
                                t = fixnewlines(t)
                            except:
                                continue
                    yield a, t
            elif typ == PY:
                tried = {}
                extns = ['.py', '.pyw', os.path.sep+'__init__.py', os.path.sep+'__init__.pyw']
                for pth in lst:
                    found = 0
                    pth = pth.split('.')
                    while not found and pth:
                        for extn in extns:
                            a = win.dirname + os.path.sep + os.path.sep.join(pth) + extn
                            if a in tried:
                                found = 1
                                break
                            tried[a] = None
                            if os.path.isfile(a):
                                if namematches(a.split('/')[-1], include, exclude):
                                    try:
                                        x = self.root.GetPositionAbsolute(a)
                                        if x != -1:
                                            t = StyledTextCtrl.GetText(self.root.GetPage(x).GetWindow1())
                                        else:
                                            t = open(a, 'rb').read()
                                        t = fixnewlines(t)
                                        found = 1
                                        tried[a] = 1
                                        break
                                    except Exception, why:
                                        continue
                        if not found and pth:
                            _ = pth.pop()
                    if found and pth and tried[a]:
                        yield a,t
                        tried[a] = None
        except cancelled:
            pass
    
    def selected_text(self, *args):
        try:
            _, win = self.root.getNumWin()
            #add some prefix lines so that the line offset is correct
            data = (win.LineFromPosition(win.GetSelection()[0])*'\n' + 
                    fixnewlines(win.GetTextRange(*win.GetSelection())))
            yield self.getfn(win), data
        except cancelled:
            pass
    
    def open_files(self, path, subdirs, include, exclude):
        for win in self.root.control:
            if namematches(win.filename, include, exclude):
                yield self.getfn(win), fixnewlines(StyledTextCtrl.GetText(win))
        
    def directories(self, path, subdirs, include, exclude):
        try:
            lst = os.listdir(path)
        except Exception, e:
            print e
            self.root.SetStatusText("Directory \"%s\" not found."%(path,))
            return
        d = []
        for filen in lst:
            a = os.path.join(path, filen)
            if os.path.isfile(a):
                if namematches(filen, include, exclude):
                    yield a, open(a, 'rU').read()
            elif subdirs and os.path.isdir(a):
                d.append(a)
        if subdirs:
            for p in d:
                for f in self.directories(p, subdirs, include, exclude):
                    yield f
    
    def tags_in_directories(self, *args):
        for fn, content in self.directories(*args):
            for line in content.split('\n'):
                if line and line.count('\t') != 2:
                    break
            else:
                yield fn, content

#----------------------------- searching methods -----------------------------
    def searchFileMultiline(self, fileName, data):
        found = []
        cp = 0
        lc = 0
        for match in self.pattern.finditer(data):
            lc += data.count('\n', cp, match.start())
            cp = match.start()
            found.append((fileName, lc + 1, match.group().replace('\n', '\\n'), ''))
        wx.Yield()
        return found

    def searchFileEachLine(self, fileName, data):
        lines = data.split('\n')
        found = []
        search=self.pattern.search
        pth = os.path.split(fileName)[0] #for tags support
        for number, line in enumerate(lines):
            itemOrig=line
            if self.checkComment:
                match=commentedPattern.search(line)
                if match is None:
                    continue
                line=match.group(1)
            if self.checkQuoted:
                matches=quotedPattern.finditer(line)
                if matches is None:
                    continue
                for match in matches:
                    line=match.group()[1:-1]
                    if search(line) is not None:
                        # (filename, line, line contents, extra)
                        found.append((fileName, int(number) + 1, itemOrig.strip(), ''))
            else:
                if search(line) is not None:
                    # (filename, line, line contents, extra)
                    if self.scope == 'Tags':
                        try:
                            tag, fn, xtra = line.split('\t')
                            lineno = int(xtra.split(';')[0])
                            found.append((os.path.join(pth, fn), lineno, itemOrig.strip(), ';'.join(xtra.split(';')[1:])))
                        except:
                            found.append((fileName, int(number) + 1, itemOrig.strip(), ''))
                    else:
                        found.append((fileName, int(number) + 1, itemOrig.strip(), ''))
            wx.Yield()
        return found

#---------------------------- preference handling ----------------------------

    def readPreferences(self):
        prefs = self.root.config.setdefault('FindInFilesPlugin', {})
        # Set the defaults individually so that adding options works
        # as expected.
        prefs.setdefault('prefs_version', 1)

        prefs.setdefault('search', [])
        prefs.setdefault('case', 0)
        prefs.setdefault('regex', 0)
        prefs.setdefault('multiline', 0)
        prefs.setdefault('whole_word', 0)
        prefs.setdefault('quoted', 0)
        prefs.setdefault('commented', 0)

        prefs.setdefault('scope', 'Current File')
        prefs.setdefault('dirs', [])
        prefs.setdefault('include', ['*.*'])
        prefs.setdefault('exclude', ['.*;*.bak;*.orig;~*;*.swp;CVS'])
        prefs.setdefault('search_sub_dirs', 1)

        prefs.setdefault('view', 'table')
        self.preferences = prefs
        return prefs

    def savePreferences(self):
        def getlist(c):
            cc = c.GetCount()
            e = [c.GetString(i) for i in xrange(cc)]
            a = c.GetValue()
            if a in e:
                e.remove(a)
            e = [a] + e
            e = e[:10]
            if len(e) > cc:
                c.Append(e[-1])
            for i in xrange(len(e)):
                c.SetString(i, e[i])
            c.SetSelection(0)
            return e

        prefs = {
            'prefs_version': 1,

            'scope': self.scopeChoice.GetStringSelection(),
            'search': getlist(self.search),
            'case': self.cs.IsChecked(),
            'regex': self.re.IsChecked(),
            'multiline': self.multiline.IsChecked(),
            'whole_word': self.ww.IsChecked(),
            'quoted': self.quoted.IsChecked(),
            'commented': self.commented.IsChecked(),

            'dirs': getlist(self.sdirs),
            'include': getlist(self.include),
            'exclude': getlist(self.exclude),
            'search_sub_dirs': self.ss.IsChecked(),

            'view': self.viewChoice.GetStringSelection(),
            }
        self.root.config['FindInFilesPlugin'] = prefs

    #-------------------------------------------------------------------------

#------------------------------ small up arrow -------------------------------

def getSmallUpArrowData():
    return \
'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\
\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\x00\
\x00\x00<IDATx\x9ccddbf\xa0\x040Q\xa4{h\x18\xf0\xff\xdf\xdf\xffd\x1b\x00\xd3\
\x8c\xcf\x10\x9c\x06\xa0k\xc2e\x08m\xc2\x00\x97m\xd8\xc41\x0c \x14h\xe8\xf2\
\x8c\xa3)q\x10\x18\x00\x00R\xd8#\xec\x95{\xc4\x11\x00\x00\x00\x00IEND\xaeB`\
\x82' 

def getSmallUpArrowBitmap():
    return BitmapFromImage(getSmallUpArrowImage())

def getSmallUpArrowImage():
    stream = cStringIO.StringIO(getSmallUpArrowData())
    return ImageFromStream(stream)
#----------------------------- small down arrow ------------------------------

def getSmallDnArrowData():
    return \
"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\
\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\x00\
\x00\x00HIDATx\x9ccddbf\xa0\x040Q\xa4{\xd4\x00\x06\x06\x06\x06\x06\x16t\x81\
\xff\xff\xfe\xfe'\xa4\x89\x91\x89\x99\x11\xa7\x0b\x90%\ti\xc6j\x00>C\xb0\x89\
\xd3.\x10\xd1m\xc3\xe5*\xbc.\x80i\xc2\x17.\x8c\xa3y\x81\x01\x00\xa1\x0e\x04e\
\x1d\xc4;\xb7\x00\x00\x00\x00IEND\xaeB`\x82" 

def getSmallDnArrowBitmap():
    return BitmapFromImage(getSmallDnArrowImage())

def getSmallDnArrowImage():
    stream = cStringIO.StringIO(getSmallDnArrowData())
    return ImageFromStream(stream)
