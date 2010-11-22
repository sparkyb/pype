#-------------- User changable settings are in configuration.py --------------
"""
Todo:
Set up configurations for all of the supported lexers that wxStyledTxtCtrl
supports, which are:
wxSTC_LEX_BATCH, wxSTC_LEX_CPP, wxSTC_LEX_ERRORLIST, wxSTC_LEX_HTML,
wxSTC_LEX_LATEX, wxSTC_LEX_MAKEFILE, wxSTC_LEX_NULL, wxSTC_LEX_PERL,
wxSTC_LEX_PROPERTIES, wxSTC_LEX_PYTHON, wxSTC_LEX_SQL, wxSTC_LEX_VB,
wxSTC_LEX_XCODE and wxSTC_LEX_XML.

Currently used:
wxSTC_LEX_CPP, wxSTC_LEX_HTML, wxSTC_LEX_PYTHON, wxSTC_LEX_XML

"""

#------------------------------ System Imports -------------------------------
import os
import sys
from wxPython.wx import *
from wxPython.stc import *
import keyword, traceback
import cStringIO
from wxPython.lib.dialogs import wxScrolledMessageDialog
import exceptions
#--------------------------- configuration import ----------------------------
from configuration import *
#--------- The two most useful links for constructing this editor... ---------
# http://personalpages.tds.net/~edream/out2.htm
# http://www.pyframe.com/wxdocs/stc/selnpos.html

#---------------------------- Event Declarations -----------------------------
if 1:
    VERSION = "1.1"

    class cancelled(exceptions.Exception):
        pass

    showpress = 0
    #if so I can collapse the declarations
    ID_NEW=wxNewId()
    ID_OPEN=wxNewId()
    ID_SAVE=wxNewId()
    ID_SAVEAS=wxNewId()
    ID_SAVEALL=wxNewId()
    ID_CLOSE=wxNewId()
    ID_EXIT=wxNewId()
    
    #edit nums
    UD = wxNewId()
    RD = wxNewId()
    SA = wxNewId()
    CU = wxNewId()
    CO = wxNewId()
    PA = wxNewId()
    IR = wxNewId()
    DR = wxNewId()
    FI = wxNewId()
    RE = wxNewId()
    IC = wxNewId()
    
    #style_nums
    PY_S = wxNewId()
    HT_S = wxNewId()
    CC_S = wxNewId()
    XM_S = wxNewId()
    TX_S = wxNewId()
    lexers = dict(zip([PY_S, HT_S, CC_S, XM_S, TX_S], ['python', 'html', 'cpp', 'xml', 'text']))
    ZI = wxNewId()
    ZO = wxNewId()
    
    #tab_nums
    PT = wxNewId()
    NT = wxNewId()
    MTL = wxNewId()
    MTR = wxNewId()

    #bookmark_nums
    BM1 = wxNewId()
    BM2 = wxNewId()
    BM3 = wxNewId()
    BM4 = wxNewId()
    BM5 = wxNewId()
    BM6 = wxNewId()
    BM7 = wxNewId()
    BM8 = wxNewId()
    BM9 = wxNewId()
    VIEW_BM = wxNewId()
    ADD_BM = wxNewId()
    DEL_BM = wxNewId()
    SAVE_BM = wxNewId()

    pathmarks = dict(zip(range(49,58), 9*[0]))
    pathmarks.update(paths)
    bmId2Pathmarks = dict(zip([BM1,BM2,BM3,BM4,BM5,BM6,BM7,BM8,BM9],
                              [pathmarks[i] for i in range(49,58)]))
    del i

    #help_nums
    ABOUT = wxNewId()
    HELP = wxNewId()
    
    #for some default font styles
    
    cn = 'Courier New'
    if wxPlatform == '__WXMSW__':
        faces = { 'times': cn, 'mono' : cn, 'helv' : cn, 'other': cn, 'size' : 10, 'size2': 9}
    else:
        faces = { 'times': 'Courier', 'mono' : 'Courier', 'helv' : 'Courier', 'other': 'Courier', 'size' : 10, 'size2': 10 }
    
#-------- Very Useful dictionary definition for the keypress stuff... --------
#---------- That is, it's an O(1) operation to find out if the key -----------
#---------------------- pressed makes the file 'dirty' -----------------------
    a = [316,319,318,317,366,313,312,314,315,324,310,367,306,308,311,309,27]+\
        range(342, 352) #to deal with the f1, f2, ...f10 keys
    notdirty = dict(zip(a,len(a)*[0]))
    a = [86, 88, 89, 90]
    dirty_edit = dict(zip(a,len(a)*[1]))
    del a
#-------------------- Useful for the find/replace stuff. ---------------------
    map = {
        wxEVT_COMMAND_FIND : "FIND",
        wxEVT_COMMAND_FIND_NEXT : "FIND_NEXT",
        wxEVT_COMMAND_FIND_REPLACE : "REPLACE",
        wxEVT_COMMAND_FIND_REPLACE_ALL : "REPLACE_ALL",
        }

    
#---------------------- Frame that contains everything -----------------------
class MainWindow(wxFrame):
    def __init__(self,parent,id,title):
        wxFrame.__init__(self,parent,id, title, size = ( 800, 600 ),
                         style=wxDEFAULT_FRAME_STYLE|wxNO_FULL_REPAINT_ON_RESIZE)
        self.control = MyNB(self, -1)
        self.CreateStatusBar() # A Statusbar in the bottom of the window
        # Setting up the menu.

#--------------------------------- File Menu ---------------------------------
        filemenu= wxMenu()
        name = ["&New     CTRL-N",
                "&Open   CTRL-O",
                "&Save    CTRL-S",
                "Save &As",
                "Sa&ve All",
                "&Close   CTRL-W",
                "E&xit      ALT-F4"]
        help = ["New file",
                "Open a file",
                "Save a file",
                "Save a file as...",
                "Save all open files...",
                "Close the file in this tab",
                "Terminate the program"]
        functs = [self.OnNew,
                  self.OnOpen,
                  self.OnSave,
                  self.OnSaveAs,
                  self.OnSaveAll,
                  self.OnClose,
                  self.OnExit]
        lkp = dict(zip([ID_NEW,ID_OPEN,ID_SAVE,ID_SAVEAS,ID_SAVEALL,ID_CLOSE,ID_EXIT], zip(name, help, functs)))
        self.updateMenu(filemenu, [ID_NEW,ID_OPEN,ID_SAVE,ID_SAVEAS,ID_SAVEALL,0,ID_CLOSE,0,ID_EXIT], lkp)

        EVT_CLOSE(self, self.OnExit)

#--------------------------------- Edit Menu ---------------------------------

        #more lines, but easier to understand.
        editmenu= wxMenu()
        name = ["Undo                CTRL-Z",
                "Redo                CTRL-Y",
                "Select All          CTRL-A",
                "Cut                   CTRL-X",
                "Copy                CTRL-C",
                "Paste                CTRL-V",
                "Indent Region  CTRL-]",
                "Dedent Region CTRL-[",
                "Find                  CTRL-F",
                "Replace            CTRL-R",
                "Insert Comment   CTRL-I"]
        help = ["Undo last modifications",
                "Redo last modifications",
                "Select all text",
                "Cut selected text",
                "Copy selected text",
                "Paste selected text",
                "Indent region %i spaces"%indent,
                "Dedent region %i spaces"%indent,
                "Find text in a file",
                "Replace text in a file",
                "Insert a centered comment"]
        functs = [self.OnUndo,
                  self.OnRedo,
                  self.OnSelectAll,
                  self.OnCut,
                  self.OnCopy,
                  self.OnPaste,
                  self.OnIndent,
                  self.OnDedent,
                  self.OnShowFind,
                  self.OnShowFindReplace,
                  self.OnInsertComment]
        lkp = dict(zip([UD, RD, SA, CU, CO, PA, IR, DR, FI, RE, IC], zip(name, help, functs)))
        self.updateMenu(editmenu, [UD, RD, 0, SA, CU, CO, PA, 0, IR, DR, 0, FI, RE, 0, 0, IC], lkp)

        EVT_COMMAND_FIND(self, -1, self.OnFind)
        EVT_COMMAND_FIND_NEXT(self, -1, self.OnFind)
        EVT_COMMAND_FIND_REPLACE(self, -1, self.OnFind)
        EVT_COMMAND_FIND_REPLACE_ALL(self, -1, self.OnFind)
        EVT_COMMAND_FIND_CLOSE(self, -1, self.OnFindClose)

#-------------------------------- Format Menu --------------------------------
        stylemenu= wxMenu()
        
        name = ["Python",
                "HTML",
                "XML",
                "C/C++",
                "Text",
                "Zoom In      CTRL-<plus>",
                "Zoom Out   CTRL-<minus>"]
        help = ["Highlight for Python syntax",
                "Highlight for HTML syntax",
                "Highlight for XML syntax",
                "Highlight for C/C++ syntax",
                "No Syntax Highlighting",
                "Make everything bigger",
                "Make everything smaller"]
        functs = 5*[self.OnStyleChange]+2*[self.OnZoom]
        lkp = dict(zip([PY_S,HT_S,XM_S,CC_S,TX_S,ZI,ZO], zip(name, help, functs)))
        self.updateMenu(stylemenu, [PY_S,HT_S,XM_S,CC_S,TX_S,0,ZI,ZO], lkp)

#--------------------------------- Tab Menu ----------------------------------
        tabmenu= wxMenu()
        
        name = ["Previous Tab      CTRL-,",
                "Next Tab            CTRL-.",
                "Move tab left      CTRL-ALT-,",
                "Move tab right    CTRL-ALT-."]
        help = ["View the tab to the left of the one you are currently",
                "View the tab to the right of the one you are currently",
                "Swap the current tab with the one on the left",
                "Swap the current tab with the one on the right"]
        functs = [self.OnLeft,
                  self.OnRight,
                  self.MoveLeft,
                  self.MoveRight]
        lkp = dict(zip([PT, NT, MTL, MTR], zip(name, help, functs)))
        self.updateMenu(tabmenu, [PT, NT, 0, MTL, MTR], lkp)

#------------------------------- path bookmarks ------------------------------
        pathmarkmenu = wxMenu()
        name = ["View pathmarks", "Edit pathmarks  CTRL-B", "Remove pathmark", "Save pathmarks"] +\
               ["%i                       CTRL-%i"%(i,i) for i in xrange(1,10)]
        help = ["Edit your bookmarked paths", "Add a path to your bookmarks", "Remove a bookmarked path", "Save pathmarks to disk"] +\
               ["Change the current working directory to the one listed in pathmark %i"%i for i in xrange(1,10)]
        functs = [self.ViewBookmarks, self.AddBookmark, self.RemoveBookmark, self.SaveBookmarks] + 9*[self.OnBookmark]
        lkp = dict(zip([VIEW_BM,ADD_BM,DEL_BM,SAVE_BM,BM1,BM2,BM3,BM4,BM5,BM6,BM7,BM8,BM9], zip(name, help, functs)))
        #print lkp
        self.updateMenu(pathmarkmenu, [VIEW_BM,ADD_BM,DEL_BM,SAVE_BM,0,BM1,BM2,BM3,BM4,BM5,BM6,BM7,BM8,BM9], lkp)

#--------------------------------- Help Menu ---------------------------------
        helpmenu= wxMenu()
        name = ["About...",
                "Help    F1"]
        help = ["About this piece of software",
                "View the help"]
        functs = [self.OnAbout,
                  self.OnHelp]
        lkp = dict(zip([ABOUT, HELP], zip(name, help, functs)))
        self.updateMenu(helpmenu, [ABOUT, 0, HELP], lkp)

#------------------------- Insert menus into Menubar -------------------------
        menuBar = wxMenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        menuBar.Append(editmenu, "&Edit")
        menuBar.Append(stylemenu,"F&ormat")
        menuBar.Append(tabmenu, "&View")
        menuBar.Append(pathmarkmenu, "Bookmarked &Paths")
        menuBar.Append(helpmenu, "&Help")
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.


#-------------------------- Couple state variables ---------------------------
        self.Show(true)
        self.dirname = '.'
        self.closing = 0
        self.openfiles = {}
        self.dpm = 0

#---------------- A nice lookup table for control keypresses -----------------
#-------------- it saves the trouble of a many if calls during ----------------
#---------------- control+keypress combos, which can't hurt ------------------

        self.ctrlpress=dict([
            (70, self.OnShowFind),      #find string with ctrl-f
            (82, self.OnShowFindReplace),#find and replace string with ctrl-r
            (73, self.OnInsertComment), #shifts current line down one, inserting a line-long comment
            (78, self.OnNew),           #create a new document with ctrl-n
            (79, self.OnOpen),          #open an old document with ctrl-o
            (87, self.OnClose),         #close the currently open document with ctrl-w
            (83, self.OnSave),          #save the currently open document with ctrl-s
            (93, self.OnIndent),        #indent the current line or selection of lines (indent) spaces with ctrl-]
            (91, self.OnDedent),        #dedent the current line or selection of lines (indent) spaces with ctrl-[
            (44, self.OnLeft),          #go to the tab to the left with ctrl-, (same key as <)
            (46, self.OnRight),         #go to the tab to the right with ctrl-. (same key as >)
            (66, self.AddBookmark)      #open the 'edit pathmark' dialog
        ])
#- deals with bookmarks on paths...what I like to call 'pathmarks', tee hee --
        self.ctrlpress.update(dict(zip(pathmarks.keys(), 10*[self.OnBookmark])))

    def updateMenu(self, menu, menu_items, lookup):
        for i in menu_items:
            if i:
                menu.Append(i, lookup[i][0], lookup[i][1])
                EVT_MENU(self, i, lookup[i][2])
            else:
                menu.AppendSeparator()

    '''def selected(self, e):                   # for a removed dirctrl thing...
        a = self.dirctrl.GetFilePath()          # leaving here, maybe for later
        if a:
            abs = os.path.normcase(os.path.normpath(a))
            if self.isAbsOpen(abs):
                self.selectAbsolute(abs)
            else:
                self.makeAbsOpen(abs)
                tdn, tfn = self.splitAbsolute(abs)
                self.newTab(tdn,tfn,1)
        else:
            e.Skip()

    def OnShowSplit(self, e):
        self.top_split.SetSashPosition(100)'''

    def dialog(self, message, title, styl=wxOK):
        d= wxMessageDialog(self,message,title,styl)
        retr = d.ShowModal()
        d.Destroy()
        return retr
    def OnDrop(self, event):
        fnames = event.GetFiles()
        for i in fnames:
            if self.isAbsOpen(i):
                self.selectAbsolute(i)
            else:
                self.makeAbsOpen(i)
                d,f = os.path.split(i)
                self.newTab(d,f, len(fnames)==1)

#---------------------------- File Menu Commands -----------------------------
    def selectAbsolute(self, path):
        if self.isAbsOpen(path):
            dn, fn = self.splitAbsolute(path)
            for i in xrange(self.control.GetPageCount()):
                win = self.control.GetPage(i)
                if (win.filename == fn) and (win.dirname == dn):
                    self.control.SetSelection(i)
                    return

    def isOpen(self, fn, dn):
        return dn and fn and (self.getAbsolute(fn, dn) in self.openfiles)
    def isAbsOpen(self, path):
        return path in self.openfiles

    def makeOpen(self, fn, dn):
        if fn and dn:
            a = self.getAbsolute(fn, dn)
            self.openfiles[a] = self.splitAbsolute(a)
    def makeAbsOpen(self, path):
        if path:
            self.openfiles[path] = self.splitAbsolute(path)
    def closeOpen(self, fn, dn):
        if fn and dn:
            del self.openfiles[self.getAbsolute(fn, dn)]

    def getAbsolute(self, fn, dn):
        return os.path.normcase(os.path.normpath(os.path.join(dn, fn)))
    def splitAbsolute(self, path):
        return os.path.split(path)

    def OnNew(self,e):
        self.newTab('', ' ', 1)
        self.control.GetPage(self.control.GetSelection()).opened = 1
        self.SetStatusText("Created a new file")

    def OnSave(self,e):
        wnum, win = self.getNumWin(e)

        if win.dirname:
            try:
                ofn = os.path.join(win.dirname, win.filename)
                fil = open(ofn, 'wb')
                txt = win.GetText()
                #print repr(eol), repr(win.format), txt.count('\r\n'), txt.count('\n'), txt.count('\r'), txt.count('\r\r')
                fil.write(txt)
                fil.close()
                self.SetStatusText("Correctly saved %s"%ofn)
                win.MakeClean()
            except:
                k = cStringIO.StringIO()
                traceback.print_exc(file=k)
                k.seek(0)
                self.dialog("Save Failed because:\n%s"%k.read(),"Save Failed")
                raise cancelled
        else:
            self.OnSaveAs(e)

    def OnSaveAs(self,e):
        wnum, win = self.getNumWin(e)
        
        dlg = wxFileDialog(self, "Save file as...", os.getcwd(), "", wildcard, wxOPEN)
        rslt = dlg.ShowModal()
        if rslt == wxID_OK:
            fn=dlg.GetFilename()
            dn=dlg.GetDirectory()
            if self.isOpen(fn, dn):
                self.dialog("Another file with that name and path is already open.\nSave aborted to prevent data corruption.", "Save Aborted!")
                raise cancelled
            if self.isOpen(win.filename, win.dirname):
                self.closeOpen(win.filename, win.dirname)
            win.filename = fn
            win.dirname = dn
            self.makeOpen(fn, dn)
            self.OnSave(e)
            win.MakeClean()
        else:
            raise cancelled

    def OnSaveAll(self, e):
        sel = self.control.GetSelection()
        cnt = self.control.GetPageCount()
        for i in range(cnt):
            self.control.SetSelection(i)
            try:
                self.OnSave(e)
            except cancelled:
                pass
        if cnt:
            self.control.SetSelection(sel)
    
    def OnOpen(self,e):
        dlg = wxFileDialog(self, "Choose a/some file(s)...", os.getcwd(), "", wildcard, wxOPEN| wxMULTIPLE)
        if dlg.ShowModal() == wxID_OK:
            dn = dlg.GetDirectory()
            filenames = dlg.GetFilenames()
            for fn in filenames:
                rfn = self.getAbsolute(fn, dn)
                #if the file is already open, switch to that file
                if self.isAbsOpen(rfn):
                    self.selectAbsolute(rfn)
                else:
                    self.makeAbsOpen(rfn)
                    tdn, tfn = self.splitAbsolute(rfn)
                    self.newTab(tdn,tfn, len(filenames)==1)
                    self.SetStatusText("Opened %s"%rfn)
        dlg.Destroy()

    def newTab(self, dir, fn, switch=0):
        nwin = PythonSTC(self.control, -1)
        nwin.filename = fn
        nwin.dirname = dir
        nwin.changeStyle(stylefile, self.style(fn))
        if dir:
            f=open(os.path.join(nwin.dirname,nwin.filename),'rb')
            txt = f.read()
            f.close()
            nwin.format = detectLineEndings(txt)
            nwin.SetText(txt)
        else:
            nwin.format = eol
            nwin.SetText('')
        #print repr(nwin.format)
        self.control.AddPage(nwin, nwin.filename, switch)
        
    def OnClose(self, e):
        wnum, win = self.getNumWin(e)
        if win.dirty:
            dlg = wxMessageDialog(self, "%s was modified after last save.\nSave changes before closing?"%win.filename, 'Save changes?', wxYES_NO|wxCANCEL)
            a = dlg.ShowModal()
            if a == wxID_CANCEL:
                raise cancelled
            elif a == wxID_NO:
                pass
            else:
                self.OnSave(e)
        if self.isOpen(win.filename, win.dirname):
            self.closeOpen(win.filename, win.dirname)
            self.SetStatusText("Closed %s"%self.getAbsolute(win.filename, win.dirname))
        else:
            self.SetStatusText("Closed unnamed file")
        self.control.DeletePage(wnum)
                    
    def OnExit(self,e):
        if self.closing:
            return e.Skip()
        self.closing = 1
        while self.control.GetPageCount():
            try:
                self.OnClose(e)
            except cancelled:
                self.closing = 0
                try:    return e.Veto()
                except: return e.Skip()
        if self.dpm:
            rslt = self.dialog("Save Changes to Pathmarks?", "Pathmarks modified", wxYES_NO)
            if rslt == wxID_YES:
                self.SaveBookmarks(e)
        return self.Close(true)

#---------------------------- Edit Menu Commands -----------------------------
    def OneCmd(self, funct_name,evt):
        wnum, win = self.getNumWin(evt)
        getattr(win, funct_name)()

    def OnUndo(self, e):
        self.OneCmd('Undo',e)
    def OnRedo(self, e):
        self.OneCmd('Redo',e)
    def OnSelectAll(self, e):
        self.OneCmd('SelectAll',e)
    def OnCut(self, e):
        self.OneCmd('Cut',e)
    def OnCopy(self, e):
        self.OneCmd('Copy',e)
    def OnPaste(self, e):
        self.OneCmd('Paste',e)
    def Dent(self, win, incr):
        win.MakeDirty()
        x,y = win.GetSelection()
        if x==y:
            lnstart = win.GetCurrentLine()
            lnend = lnstart
        else:
            lnstart = win.LineFromPosition(x)
            lnend = win.LineFromPosition(y-1)
        win.BeginUndoAction()
        for ln in xrange(lnstart, lnend+1):
            count = win.GetLineIndentation(ln)
            #print "indenting line", ln, count
            win.SetLineIndentation(ln, max(count+incr,0))
        win.EndUndoAction()
    def OnIndent(self, e):
        wnum, win = self.getNumWin(e)
        self.Dent(win, indent)
    def OnDedent(self, e):
        wnum, win = self.getNumWin(e)
        self.Dent(win, -indent)
    def OnInsertComment(self, e):
        wnum, win = self.getNumWin(e)
        dlg = wxTextEntryDialog(self, '', 'Enter a comment.', '')
        resp = dlg.ShowModal()
        valu = dlg.GetValue()
        dlg.Destroy()
        if resp == wxID_OK:
            k = len(valu)
            a = col_line-3-k
            b = a*'-'
            st = '%s%s %s %s%s'%('#', b[:a/2], valu, b[a/2:], win.format)
            lin = win.GetCurrentLine()
            if lin>0:
                win.InsertText(win.GetLineEndPosition(lin-1)+len(win.format), st)
            else:
                win.InsertText(0, st)
            win.MakeDirty()
        else:
            event.Skip()
#--------------------- Find and replace dialogs and code ---------------------
    def getNumWin(self, e):
        num = self.control.GetSelection()
        if num >= 0:
            return num, self.control.GetPage(num)
        e.Skip()
        raise cancelled

    def OnShowFind(self, evt):
        wcount = self.control.GetPageCount()
        if not wcount:
            return evt.Skip()
        for wnum in xrange(wcount):
            win = self.control.GetPage(wnum)
            win.gcp = win.GetCurrentPos()
            win.last = 0
        data = wxFindReplaceData()
        dlg = wxFindReplaceDialog(self, data, "Find")
        dlg.data = data
        return dlg.Show(True)

    def OnShowFindReplace(self, evt):
        wcount = self.control.GetPageCount()
        if not wcount:
            return evt.Skip()
        for wnum in xrange(wcount):
            win = self.control.GetPage(wnum)
            win.gcp = win.GetCurrentPos()
            win.last = 0
        data = wxFindReplaceData()
        dlg = wxFindReplaceDialog(self, data, "Find & Replace", wxFR_REPLACEDIALOG)
        dlg.data = data
        return dlg.Show(True)

    def OnFind(self, evt):
        wnum, win = self.getNumWin(evt)
        et = evt.GetEventType()
        if not map.has_key(et):
            return evt.Skip()

        findTxt = evt.GetFindString()

        #the next couple lines deal with python strings in find
        if findTxt and (findTxt[0] in ['"', "'"]):
            try:    findTxt = eval(findTxt)
            except: pass

        #the next couple lines deal with python strings in replace
        if et == wxEVT_COMMAND_FIND_REPLACE or et == wxEVT_COMMAND_FIND_REPLACE_ALL:
            replaceTxt = evt.GetReplaceString()
            if replaceTxt and (replaceTxt[0] in ['"', "'"]):
                try:    replaceTxt = eval(replaceTxt)
                except: pass
        else:
            replaceTxt = ""

        #next line makes ininite loops not happen *smile*
        incr = len(replaceTxt)
        #next line moves cursor for replacements
        diff = incr-len(findTxt)
        if et == wxEVT_COMMAND_FIND_REPLACE_ALL:
            totl = 0
            while 1:
                win.last = win.FindText(win.last, win.GetTextLength(), findTxt, evt.GetFlags())
                if win.last > -1:
                    totl += 1
                    win.SetSelection(win.last, win.last+len(findTxt))
                    win.ReplaceSelection(replaceTxt)
                    win.last += incr
                    if win.last < win.gcp:
                        win.gcp += diff
                    win.MakeDirty()
                else:
                    win.SetSelection(win.gcp, win.gcp)
                    win.ScrollToColumn(0)
                    self.EnsureCaretVisible()
                    return self.dialog("%i replacements made."%totl, "Finished replacing")
        elif et == wxEVT_COMMAND_FIND_REPLACE:
            win.last = win.FindText(win.last, win.GetTextLength(), findTxt, evt.GetFlags())
            if win.last > -1:
                win.SetSelection(win.last, win.last+len(findTxt))
                win.ReplaceSelection(replaceTxt)
                win.last += incr
                if win.last < win.gcp:
                    win.gcp += diff
                win.MakeDirty()
        elif et == wxEVT_COMMAND_FIND:
            win.last = win.FindText(win.last, win.GetTextLength(), findTxt, evt.GetFlags())
            if win.last > -1:
                win.SetSelection(win.last, win.last+len(findTxt))
        else:# et == wxEVT_COMMAND_FIND_NEXT:
            win.last += len(findTxt)
            if win.last >= win.GetTextLength():
                win.last = 0
                return evt.Skip()
            win.last = win.FindText(win.last, win.GetTextLength(), findTxt, evt.GetFlags())
            if win.last > -1:
                win.SetSelection(win.last, win.last+len(findTxt))
        win.EnsureVisible(win.GetCurrentLine())
        win.EnsureCaretVisible()
        if win.last == -1:
            self.dialog("Reached the end of the document.", "")
        return None

    def OnFindClose(self, evt):
        #self.log.write("wxFindReplaceDialog closing...\n")
        evt.GetDialog().Destroy()
        wnum, win = self.getNumWin(evt)
        if win.last == -1:
            win.SetSelection(win.gcp, win.gcp)
            win.ScrollToColumn(0)
        
#------------------ Format Menu Commands and Style Support -------------------
    def OnStyleChange(self,e):
        wnum, win = self.getNumWin(e)
        nwin = PythonSTC(self.control, -1)
        nwin.format = win.format
        #print dir(nwin)
        nwin.changeStyle(stylefile, lexers[e.GetId()])
        nwin.SetText(win.GetText()[:])
        nwin.filename, nwin.dirname = win.filename, win.dirname
        nwin.GotoPos(win.GetCurrentPos())
        nwin.dirty = win.dirty
        nwin.ScrollToColumn(0)
        self.control.InsertPage(wnum, nwin, self.control.GetPageText(wnum))
        self.control.SetPageText(wnum, win.dirty*'* '+win.filename)
        self.control.DeletePage(wnum+1)
        self.control.SetSelection(wnum)
    def style(self, fn):
        ext = fn.split('.')[-1].lower()
        return extns.get(ext, 'python')
    def OnZoom(self, e):
        wnum, win = self.getNumWin(e)
        if e.GetId() == ZI:incr = 1
        else:              incr = -1
        win.SetZoom(win.GetZoom()+incr)
        
#----------------------------- Tab Menu Commands -----------------------------
    def next(self, incr,e):
        pagecount = self.control.GetPageCount()
        wnum, win = self.getNumWin(e)
        wnum = (wnum+incr)%pagecount
        self.control.SetSelection(wnum)
    def OnLeft(self, e):
        self.next(-1,e)
    def OnRight(self, e):
        self.next(1,e)
    def MoveLeft(self, e):
        wnum = self.control.GetSelection()
        pagecount = self.control.GetPageCount()
        if (wnum >= 0) and (pagecount>1):
            l, r = (wnum-1)%pagecount, wnum
            self.control.swapPages(l, r, 1)
            self.control.SetSelection(l)
        else:
            e.Skip()
    def MoveRight(self, e):
        wnum = self.control.GetSelection()
        pagecount = self.control.GetPageCount()
        if (wnum >= 0) and (pagecount>1):
            l, r = (wnum+1)%pagecount, wnum
            self.control.swapPages(l, r, 0)
            self.control.SetSelection(l)
        else:
            e.Skip()

#------------------------- Bookmarked Path Commands --------------------------
    def OnBookmark(self, e, st=type('')):
        try:
            key = e.GetKeyCode()
            pth = pathmarks.get(key)
        except:
            pth = bmId2Pathmarks[e.GetId()]
        if (type(pth) is st) and os.path.isdir(pth):
            os.chdir(pth)
            self.SetStatusText("Changed path to %s"%pth)

    def ViewBookmarks(self, e, titl="Bookmarked Paths", styl=wxOK, st=type('')):
        kys = pathmarks.keys()
        kys.sort()
        out = []
        for i in kys:
            if type(pathmarks[i]) is st:
                out.append("%i            %s    "%(i-48, pathmarks[i]))
            else:
                out.append("%i            <unused>    "%(i-48))

        dlg = wxSingleChoiceDialog(self, "Pathmark       Path",titl, out, styl|wxDD_DEFAULT_STYLE)
        if dlg.ShowModal() == wxID_OK:
            return dlg.GetStringSelection()
        return None
        
    def AddBookmark(self, e):
        pth = ' '
        while pth != None:
            pth = self.ViewBookmarks(e, "Select a pathmark to update", wxOK|wxCANCEL)
            if pth:
                opth = pathmarks[int(pth[0])+48]
                if opth == 0: opth = os.getcwd()
                dlg = wxDirDialog(self, "Choose a path", opth, style=wxDD_DEFAULT_STYLE|wxDD_NEW_DIR_BUTTON)
                if dlg.ShowModal() == wxID_OK:
                    pathmarks[int(pth[0])+48] = dlg.GetPath()
                    self.dpm = 1
                    self.SetStatusText("Pathmark modification successful")
                else:
                    self.SetStatusText("Pathmark modification aborted")
        self.SetStatusText("Finished updating pathmarks")

    def RemoveBookmark(self, e):
        pth = ' '
        while pth != None:
            pth = self.ViewBookmarks(e, "Delete pathmark (cancel to finish)", wxOK|wxCANCEL)
            if pth:
                self.dpm = 1
                pathmarks[int(pth[0])+48] = 0

    def SaveBookmarks(self, e):
        sav = "paths = %s\n"%repr(pathmarks)
        pm = open(os.path.join(runpath, "pathmarks.py"), 'w')
        pm.write(sav)
        pm.close()
        self.dpm = 0
        self.SetStatusText("Pathmarks saved.")

#---------------------------- Help Menu Commands -----------------------------
    def OnAbout(self, e):
        txt = """
        You're wondering what this editor is all about, right?  Easy, this edior was
        written to scratch an itch.  I (Josiah Carlson), was looking for an editor
        that had the features I wanted, I couldn't find one.  So I wrote one.  And
        here it is.
        
        PyPE %s (Python Programmers Editor)
        http://come.to/josiah
        PyPE is copyright 2003 Josiah Carlson.
        
        This software is licensed under the GPL (GNU General Public License) as it
        appears here: http://www.gnu.org/copyleft/gpl.html  It is also included with
        this software as gpl.txt.
        
        If you do not also receive a copy of gpl.txt with your version of this
        software, please inform the me of the violation at the web page near the top
        of this document."""%VERSION
        self.dialog(txt.replace('        ', ''), "About...")
    def OnHelp(self, e):
        a = open(os.path.join(runpath, 'readme.txt'), 'rb')
        txt = a.read()
        a.close()
        dlg = wxScrolledMessageDialog(self, txt, "Help!")
        dlg.ShowModal()
        dlg.Destroy()
#-------------------------- Hot Key support madness --------------------------
    def OnKeyPressed(self, event, notdirty=notdirty):
        if showpress: print "keypressed", event.KeyCode()
        key = event.KeyCode()
        wnum = self.control.GetSelection()
        pagecount = self.control.GetPageCount()
        if wnum > -1:
            win = self.control.GetPage(wnum)
            if win.CallTipActive():
                win.CallTipCancel()

        if event.ControlDown() and event.AltDown():
            #commands for both control and alt pressed

            #shift current tab left with ctrl-alt-, (same key as <)
            if key == 44:
                self.MoveLeft(event)
            #shift current tab right with ctrl-alt-. (same key as >)
            elif key == 46:
                self.MoveRight(event)
            else:
                event.Skip()

        elif event.ControlDown():
            #commands for just control pressed
            cmd = self.ctrlpress.get(key, 0)
            if cmd:
                #only works for self.function(event) commands
                cmd(event)
            elif pagecount >= 1:
                #makes document dirty on cut, paste, undo, redo
                if dirty_edit.get(key, 0):
                    win.MakeDirty(event)

                #get the current keyword list with ctrl-<space>
                elif key == 32:
#------------- Left in comments for future completion additions --------------
                    #pos = win.GetCurrentPos()
                    # Tips
                    #if event.ShiftDown():
                    #    self.CallTipSetBackground("yellow")
                    #    self.CallTipShow(pos, 'lots of of text: blah, blah, blah\n\n'
                    #                     'show some suff, maybe parameters..\n\n'
                    #                     'fubar(param1, param2)')
                    # Code completion
                    #else:
                    #lst = []
                    #for x in range(50000):
                    #    lst.append('%05d' % x)
                    #st = " ".join(lst)
                    #print len(st)
                    #self.AutoCompShow(0, st)
        
                    kw = keyword.kwlist[:]
                    #kw.append("zzzzzz?2")
                    #kw.append("aaaaa?2")
                    #kw.append("__init__?3")
                    #kw.append("zzaaaaa?2")
                    #kw.append("zzbaaaa?2")
                    #kw.append("this_is_a_longer_value")
                    #kw.append("this_is_a_much_much_much_much_much_much_much_longer_value")
    
                    kw.sort()  # Python sorts are case sensitive
                    self.AutoCompSetIgnoreCase(False)  # so this needs to match
        
                    # Images are specified with a appended "?type"
                    for i in range(len(kw)):
                        if kw[i] in keyword.kwlist:
                            kw[i] = kw[i]# + "?1"
                        self.AutoCompShow(0, " ".join(kw))
                else:
                    event.Skip()
            else:
                event.Skip()
        elif event.AltDown():
            #events for just the alt key down
            event.Skip()
        else:
            #events for any key down
            try:
                #print "dirty!!!"
                #the next line is so that arrows, paging up and down and such don't make
                #the file 'dirty' - which is 'modified but not written to disk'
                if (not win.dirty) and notdirty.get(key,1):
                    win.MakeDirty()
                self.SetStatusText("")
            except: pass

            #when 'enter' is pressed, indentation needs to happen.
            #
            #will indent the current line to be equivalent to the line above
            #unless a ':' is at the end of the previous, then will indent
            #four more.
            if (key==13):
                if pagecount:
                    #get information about the current cursor position
                    ln = win.GetCurrentLine()
                    pos = win.GetCurrentPos()
                    col = win.GetColumn(pos)
                    
                    #get info about the current line's indentation
                    ind = win.GetLineIndentation(ln)
                    
                    if col <= ind:
                        win.ReplaceSelection(win.format+col*' ')
                    elif pos:
                        if (win.GetCharAt(pos-1) == 58):
                            ind += indent
                        win.ReplaceSelection(win.format+ind*' ')
                    else:
                        win.ReplaceSelection(win.format)
                    chrs = ''
                    for i in xrange(3):
                        chrs += chr(win.GetCharAt(pos+i))
                    #print repr(win.format), repr(chrs)
                    #win.SetLineIndentation(ln, ind)
                    return
                else:
                    return event.skip()
            elif key == 342:
                return self.OnHelp(event)
            else:
                return event.Skip()

#------------- Ahh, Styled Text Control, you make this possible. -------------
class PythonSTC(wxStyledTextCtrl):
    def __init__(self, parent, ID):
        wxStyledTextCtrl.__init__(self, parent, ID, style = wxNO_FULL_REPAINT_ON_RESIZE)
        self.parent = parent
        self.dirty = 0
        
        #for command comlpetion
        self.SetKeyWords(0, " ".join(keyword.kwlist))
        
        self.SetMargins(0,0)
        self.SetViewWhiteSpace(False)
        #self.SetBufferedDraw(False)
        #self.SetViewEOL(True)

        self.SetEdgeMode(wxSTC_EDGE_LINE)
        self.SetEdgeColumn(col_line)

        self.SetMarginType(0, wxSTC_MARGIN_NUMBER)
        self.SetMarginWidth(0, margin_width)
        #self.StyleSetSpec(wxSTC_STYLE_LINENUMBER, "size:%(size)d,face:%(mono)s" % faces)

        # Setup a margin to hold fold markers
        #I agree, what is this value?
        #self.SetFoldFlags(16)  ###  WHAT IS THIS VALUE?  WHAT ARE THE OTHER FLAGS?  DOES IT MATTER?
        
# Collapseable source code rocks.  It would have been great for writing this. 
        if collapse:
            self.SetProperty("fold", "1")
            #I don't know what this next line is...but I am afraid to remove it
            self.SetProperty("tab.timmy.whinge.level", "1")
            self.SetMarginType(2, wxSTC_MARGIN_SYMBOL)
            self.SetMarginMask(2, wxSTC_MASK_FOLDERS)
            self.SetMarginSensitive(2, True)
            self.SetMarginWidth(2, 12)
    
            if collapse_style: # simple folder marks, like the old version
                self.MarkerDefine(wxSTC_MARKNUM_FOLDER, wxSTC_MARK_BOXPLUS, "navy", "white")
                self.MarkerDefine(wxSTC_MARKNUM_FOLDEROPEN, wxSTC_MARK_BOXMINUS, "navy", "white")
                # Set these to an invisible mark
                self.MarkerDefine(wxSTC_MARKNUM_FOLDEROPENMID, wxSTC_MARK_BACKGROUND, "white", "black")
                self.MarkerDefine(wxSTC_MARKNUM_FOLDERMIDTAIL, wxSTC_MARK_BACKGROUND, "white", "black")
                self.MarkerDefine(wxSTC_MARKNUM_FOLDERSUB, wxSTC_MARK_BACKGROUND, "white", "black")
                self.MarkerDefine(wxSTC_MARKNUM_FOLDERTAIL, wxSTC_MARK_BACKGROUND, "white", "black")
    
            else: # more involved "outlining" folder marks
                self.MarkerDefine(wxSTC_MARKNUM_FOLDEREND,     wxSTC_MARK_BOXPLUSCONNECTED,  "white", "black")
                self.MarkerDefine(wxSTC_MARKNUM_FOLDEROPENMID, wxSTC_MARK_BOXMINUSCONNECTED, "white", "black")
                self.MarkerDefine(wxSTC_MARKNUM_FOLDERMIDTAIL, wxSTC_MARK_TCORNER,  "white", "black")
                self.MarkerDefine(wxSTC_MARKNUM_FOLDERTAIL,    wxSTC_MARK_LCORNER,  "white", "black")
                self.MarkerDefine(wxSTC_MARKNUM_FOLDERSUB,     wxSTC_MARK_VLINE,    "white", "black")
                self.MarkerDefine(wxSTC_MARKNUM_FOLDER,        wxSTC_MARK_BOXPLUS,  "white", "black")
                self.MarkerDefine(wxSTC_MARKNUM_FOLDEROPEN,    wxSTC_MARK_BOXMINUS, "white", "black")

        EVT_STC_UPDATEUI(self,    ID, self.OnUpdateUI)
        EVT_STC_MARGINCLICK(self, ID, self.OnMarginClick)
        EVT_KEY_DOWN(self, self.parent.parent.OnKeyPressed)

        # Make some styles,  The lexer defines what each style is used for, we
        # just have to define what each style looks like.  This set is adapted from
        # Scintilla sample property files.
        
        #And good wxPython users who have seen some demos know the above was copied
        #and pasted, along with alot of sample code, right out of the demo.  The
        #demo r0XX0rs.
        
        # Global default styles for all languages
        self.StyleSetSpec(wxSTC_STYLE_DEFAULT,     "fore:#000000,face:%(mono)s,back:#FFFFFF,size:%(size)d" % faces)
        self.StyleSetSpec(wxSTC_STYLE_LINENUMBER,  "back:#C0C0C0,face:Lucida Console,size:%(size2)d" % faces)
        self.StyleSetSpec(wxSTC_STYLE_CONTROLCHAR, "face:%(other)s" % faces)
        self.StyleSetSpec(wxSTC_STYLE_BRACELIGHT,  "fore:#003000,face:%(mono)s,back:#80E0E0"% faces)
        self.StyleSetSpec(wxSTC_STYLE_BRACEBAD,    "fore:#E0FFE0,face:%(mono)s,back:#FF0000"% faces)

        #various settings
        self.SetSelBackground(1, '#B0B0FF')
        self.SetIndent(indent)
        self.SetUseTabs(use_tabs)

        #again, some state variables
        self.filename = ''
        self.dirname = ''
        self.opened = 0

#-------------------- fix for SetText for the 'dirty bit' --------------------
    def SetText(self, txt):
        self.SetEOLMode(fmt_mode[self.format])
        wxStyledTextCtrl.SetText(self, txt)
        self.opened = 1

#----- Takes care of the little '*' modified next to the open file name ------
    def MakeDirty(self, e=None):
        if (not self.dirty) and self.opened:
            self.dirty = 1
            self.parent.SetPageText(self.parent.GetSelection(), '* '+self.filename)
            self.parent.Refresh(False)
            #self.parent.Refresh(True)
            self.Refresh(False)
            #self.Refresh(True)
        if e:
            e.Skip()
            
    def MakeClean(self, e=None):
        self.dirty = 0
        self.parent.SetPageText(self.parent.GetSelection(), self.filename)
        self.parent.Refresh(False)
        #self.parent.Refresh(True)
        self.Refresh(False)
        #self.Refresh(True)
        if e:
            e.Skip()

#--------- Ahh, the style change code...isn't it great?  Not really. ---------
    def changeStyle(self, stylefile, language):
        try:
            #from StyleSupport import initSTC
            from STCStyleEditor import initSTC
            initSTC(self, stylefile, language)

        except:
            #I personally think the use of StringIO for tracebacks is neat...that's why I did it.
            k = cStringIO.StringIO()
            traceback.print_exc(file=k)
            k.seek(0)
            self.parent.parent.dialog("Style change failed because:\n%s"%k.read(),"Assuming Python")
            
#----------------- Defaults, incase the other code was bad. ------------------
            self.SetLexer(wxSTC_LEX_PYTHON)
    
            # Python styles

            # White space
            self.StyleSetSpec(wxSTC_P_DEFAULT, "fore:#000000,face:%(helv)s,size:%(size)d" % faces)
            # Comment
            self.StyleSetSpec(wxSTC_P_COMMENTLINE, "fore:#007F00,face:%(mono)s,back:#E0FFE0,size:%(size)d" % faces)
            # Number
            self.StyleSetSpec(wxSTC_P_NUMBER, "fore:#007F7F,face:%(times)s,size:%(size)d" % faces)
            # String
            self.StyleSetSpec(wxSTC_P_STRING, "fore:#7F007F,face:%(times)s,size:%(size)d" % faces)
            # Single quoted string
            self.StyleSetSpec(wxSTC_P_CHARACTER, "fore:#7F007F,face:%(times)s,size:%(size)d" % faces)
            # Keyword
            self.StyleSetSpec(wxSTC_P_WORD, "fore:#F0B000,face:%(mono)s,size:%(size)d,bold" % faces)
            # Triple quotes
            self.StyleSetSpec(wxSTC_P_TRIPLE, "fore:#603000,face:%(times)s,back:#FFFFE0,size:%(size)d" % faces)
            # Triple double quotes
            self.StyleSetSpec(wxSTC_P_TRIPLEDOUBLE, "fore:#603000,face:%(times)s,back:#FFFFE0,size:%(size)d" % faces)
            # Class name definition
            self.StyleSetSpec(wxSTC_P_CLASSNAME, "fore:#0000FF,face:%(times)s,size:%(size)d,bold" % faces)
            # Function or method name definition
            self.StyleSetSpec(wxSTC_P_DEFNAME, "fore:#0000FF,face:%(times)s,size:%(size)d,bold" % faces)
            # Operators
            self.StyleSetSpec(wxSTC_P_OPERATOR, "face:%(times)s,size:%(size)d" % faces)
            # Identifiers
            self.StyleSetSpec(wxSTC_P_IDENTIFIER, "fore:#000000,face:%(helv)s,size:%(size)d" % faces)
            # Comment-blocks
            self.StyleSetSpec(wxSTC_P_COMMENTBLOCK, "fore:#7F7F7F,face:%(times)s,size:%(size)d" % faces)
            # End of line where string is not closed
            self.StyleSetSpec(wxSTC_P_STRINGEOL, "fore:#000000,face:%(mono)s,back:#E0C0E0,eol,size:%(size)d" % faces)
    
            self.SetCaretForeground("BLACK")
    
            # register some images for use in the AutoComplete box.
            #no...don't register some images.
            #self.RegisterImage(1, images.getSmilesBitmap())
            #self.RegisterImage(2, images.getFile1Bitmap())
            #self.RegisterImage(3, images.getCopyBitmap())

#------------ copied and pasted from the wxStyledTextCtrl_2 demo -------------
    def OnUpdateUI(self, evt):
        # check for matching braces
        braceAtCaret = -1
        braceOpposite = -1
        charBefore = None
        caretPos = self.GetCurrentPos()
        if caretPos > 0:
            charBefore = self.GetCharAt(caretPos - 1)
            styleBefore = self.GetStyleAt(caretPos - 1)

        # check before
        if charBefore and chr(charBefore) in "[]{}()" and styleBefore == wxSTC_P_OPERATOR:
            braceAtCaret = caretPos - 1

        # check after
        if braceAtCaret < 0:
            charAfter = self.GetCharAt(caretPos)
            styleAfter = self.GetStyleAt(caretPos)
            if charAfter and chr(charAfter) in "[]{}()" and styleAfter == wxSTC_P_OPERATOR:
                braceAtCaret = caretPos

        if braceAtCaret >= 0:
            braceOpposite = self.BraceMatch(braceAtCaret)

        if braceAtCaret != -1  and braceOpposite == -1:
            self.BraceBadLight(braceAtCaret)
        else:
            self.BraceHighlight(braceAtCaret, braceOpposite)
            #pt = self.PointFromPosition(braceOpposite)
            #self.Refresh(True, wxRect(pt.x, pt.y, 5,5))
            #print pt
            #self.Refresh(False)


    def OnMarginClick(self, evt):
        # fold and unfold as needed
        if evt.GetMargin() == 2:
            lineClicked = self.LineFromPosition(evt.GetPosition())
            if self.GetFoldLevel(lineClicked) & wxSTC_FOLDLEVELHEADERFLAG:
                if evt.GetShift():
                    self.SetFoldExpanded(lineClicked, True)
                    self.Expand(lineClicked, True, True, 1)
                elif evt.GetControl():
                    if self.GetFoldExpanded(lineClicked):
                        self.SetFoldExpanded(lineClicked, False)
                        self.Expand(lineClicked, False, True, 0)
                    else:
                        self.SetFoldExpanded(lineClicked, True)
                        self.Expand(lineClicked, True, True, 100)
                else:
                    self.ToggleFold(lineClicked)


    def FoldAll(self):
        lineCount = self.GetLineCount()
        expanding = True

        # find out if we are folding or unfolding
        for lineNum in range(lineCount):
            if self.GetFoldLevel(lineNum) & wxSTC_FOLDLEVELHEADERFLAG:
                expanding = not self.GetFoldExpanded(lineNum)
                break;

        lineNum = 0
        while lineNum < lineCount:
            level = self.GetFoldLevel(lineNum)
            if level & wxSTC_FOLDLEVELHEADERFLAG and \
               (level & wxSTC_FOLDLEVELNUMBERMASK) == wxSTC_FOLDLEVELBASE:

                if expanding:
                    self.SetFoldExpanded(lineNum, True)
                    lineNum = self.Expand(lineNum, True)
                    lineNum = lineNum - 1
                else:
                    lastChild = self.GetLastChild(lineNum, -1)
                    self.SetFoldExpanded(lineNum, False)
                    if lastChild > lineNum:
                        self.HideLines(lineNum+1, lastChild)

            lineNum = lineNum + 1

    def Expand(self, line, doExpand, force=False, visLevels=0, level=-1):
        lastChild = self.GetLastChild(line, level)
        line = line + 1
        while line <= lastChild:
            if force:
                if visLevels > 0:
                    self.ShowLines(line, line)
                else:
                    self.HideLines(line, line)
            else:
                if doExpand:
                    self.ShowLines(line, line)

            if level == -1:
                level = self.GetFoldLevel(line)

            if level & wxSTC_FOLDLEVELHEADERFLAG:
                if force:
                    if visLevels > 1:
                        self.SetFoldExpanded(line, True)
                    else:
                        self.SetFoldExpanded(line, False)
                    line = self.Expand(line, doExpand, force, visLevels-1)

                else:
                    if doExpand and self.GetFoldExpanded(line):
                        line = self.Expand(line, True, force, visLevels-1)
                    else:
                        line = self.Expand(line, False, force, visLevels-1)
            else:
                line = line + 1;

        return line
#-------------- end of copied code from wxStyledTextCtrl_2 demo --------------
#(really I copied alot more, but that part I didn't modify at all, I didn't
#want to understand it - it just worked.

#------------------------- Ahh, the tabbed notebook --------------------------
class MyNB(wxNotebook):
    def __init__(self, parent, id):
        #the left-tab, while being nice, turns the text sideways, ick.
        wxNotebook.__init__(self, parent, id, style=
                            wxNB_TOP
                            #wxNB_BOTTOM
                            #wxNB_LEFT
                            #wxNB_RIGHT
                            )
        self.parent = parent

        #for some reason, the notebook needs the next line...the text control
        #doesn't.
        EVT_KEY_DOWN(self, self.parent.OnKeyPressed)

        EVT_NOTEBOOK_PAGE_CHANGED(self, self.GetId(), self.OnPageChanged)

    def OnPageChanged(self, event):
        new = event.GetSelection()
        #fix for dealing with current paths.  They are wonderful.
        if new > -1:
            win = self.GetPage(new)
            if win.dirname:
                os.chdir(win.dirname)
        event.Skip()

#----------------- This deals with the tab swapping support. -----------------
    def swapPages(self, p1, p2, moveleft):
        mn = min(p1,p2)
        mx = max(p1,p2)
        if not (moveleft or (p1-p2==1)):
            mn, mx = mx, mn
        page = self.GetPage(mn)
        text = self.GetPageText(mn)[:]
        self.RemovePage(mn)
        self.InsertPage(mx, page, text, 1)
        self.parent.Refresh(False)
        self.Refresh(False)

#--------------------------- And the main...*sigh* ---------------------------
def main():
    app = wxPySimpleApp()
    app.frame = MainWindow(None, -1, "PyPE %s"%VERSION)
    app.frame.Show(1)
    app.MainLoop()

if __name__ == '__main__':
    main()
