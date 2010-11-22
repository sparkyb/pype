#!/usr/bin/python

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

Remaining:
wxSTC_LEX_BATCH, wxSTC_LEX_ERRORLIST, wxSTC_LEX_LATEX, wxSTC_LEX_MAKEFILE,
wxSTC_LEX_NULL, wxSTC_LEX_PERL, wxSTC_LEX_PROPERTIES, wxSTC_LEX_SQL,
wxSTC_LEX_VB, wxSTC_LEX_XCODE

"""

#------------------------------ System Imports -------------------------------
import os
import sys
from wxPython.wx import *
from wxPython.stc import *
from wxPython.lib.rcsizer import RowColSizer
import keyword, traceback, cStringIO, imp
from wxPython.lib.dialogs import wxScrolledMessageDialog
from wxPython.lib.filebrowsebutton import FileBrowseButton, DirBrowseButton

import pprint
import exceptions, time
#--------------------------- configuration import ----------------------------
from configuration import *
#--------- The two most useful links for constructing this editor... ---------
# http://personalpages.tds.net/~edream/out2.htm
# http://www.pyframe.com/wxdocs/stc/selnpos.html

#---------------------------- Event Declarations -----------------------------

if 1:
    #if so I can collapse the declarations
    VERSION = "1.5"
    VREQ = '2.4.1.2'

    import string
    STRINGPRINTABLE = string.printable[:]
    del string

    class cancelled(exceptions.Exception):
        pass
    ID_NEW=wxNewId()
    ID_OPEN=wxNewId()
    ID_SAVE=wxNewId()
    ID_SAVEAS=wxNewId()
    ID_SAVEALL=wxNewId()
    ID_RELOAD=wxNewId()
    ID_CLOSE=wxNewId()
    ID_OPENMODULE=wxNewId()
    ID_EXIT=wxNewId()
    
    #edit nums
    UD = wxNewId()
    RD = wxNewId()
    SA = wxNewId()
    CU = wxNewId()
    CU = wxNewId()
    CO = wxNewId()
    PA = wxNewId()
    IR = wxNewId()
    DR = wxNewId()
    FI = wxNewId()
    RE = wxNewId()
    IC = wxNewId()
    CS = wxNewId()
    US = wxNewId()
    
    #style_nums
    PY_S = wxNewId()
    HT_S = wxNewId()
    CC_S = wxNewId()
    XM_S = wxNewId()
    TX_S = wxNewId()
    lexers = dict(zip([PY_S, HT_S, CC_S, XM_S, TX_S], ['python', 'html', 'cpp', 'xml', 'text']))

    #view nums
    ZI = wxNewId()
    ZO = wxNewId()
    REFRESH = wxNewId()
    REFRESHSLOW = wxNewId()
    BROWSE = wxNewId()
    AUTO = wxNewId()
    
    #tab_nums
    PT = wxNewId()
    NT = wxNewId()
    MTL = wxNewId()
    MTR = wxNewId()
    PSNIP = wxNewId()
    NSNIP = wxNewId()
    ISNIP = wxNewId()
    SNIP = wxNewId()

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

    pm = [BM1,BM2,BM3,BM4,BM5,BM6,BM7,BM8,BM9]
    kp = range(49,58)
    #The range(49,58) represents the key codes for numbers 1...9 inclusve.
    pathmarks = dict(zip(kp, 9*[0]))
    bmId2Keypress = dict(zip(pm, kp))
    bmPm2Id = dict(zip(kp, pm))
    del pm;del kp

    #help_nums
    ABOUT = wxNewId()
    HELP = wxNewId()
    
    #listbox ID
    LB_ID = wxNewId()
    
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
    def __init__(self,parent,id,title,fnames):
        wxFrame.__init__(self,parent,id, title, size = ( 800, 600 ),
                         style=wxDEFAULT_FRAME_STYLE|wxNO_FULL_REPAINT_ON_RESIZE)

        #recent menu relocated to load configuration early on.
        recentmenu = wxMenu()
#--------------------------- cmt-001 - 08/06/2003 ----------------------------
#----------------- Adds opened file history to the File menu -----------------
        self.fileHistory = wxFileHistory()
        self.fileHistory.UseMenu(recentmenu)
        self.configPath = homedir
        self.loadHistory()
        EVT_MENU_RANGE(self, wxID_FILE1, wxID_FILE9, self.OnFileHistory)
#------------------------- end cmt-001 - 08/06/2003 --------------------------


        self.CreateStatusBar() # A Statusbar in the bottom of the window

        self.split = wxSplitterWindow(self, -1)
        
        self.control = MyNB(self, -1, self.split)
        self.snippet = CodeSnippet(self, -1, self.split, self.config['display2code'], self.config['displayorder'])
        
        self.split.SetMinimumPaneSize(1)
        self.split.SplitVertically(self.snippet, self.control, 1)

        EVT_CLOSE(self, self.OnExit)

        # Setting up the menu.

#--------------------------------- File Menu ---------------------------------
        filemenu= wxMenu()
        name = ["&New\tCtrl+N",
                "&Open\tCtrl+O",
                "Open &Module\tAlt+M",
                "&Save\tCtrl+S",
                "Save &As",
                "Sa&ve All",
                "&Reload",
                "&Close\tCtrl+W",
                "E&xit\tAlt+F4"]
        help = ["New file",
                "Open a file",
                "Open a module for editing using the same path search as import would",
                "Save a file",
                "Save a file as...",
                "Save all open files...",
                "Reload the current document from disk",
                "Close the file in this tab",
                "Terminate the program"]
        functs = [self.OnNew,
                  self.OnOpen,
                  self.OnOpenModule,
                  self.OnSave,
                  self.OnSaveAs,
                  self.OnSaveAll,
                  self.OnReload,
                  self.OnClose,
                  self.OnExit]
        lkp = dict(zip([ID_NEW,ID_OPEN,ID_OPENMODULE,ID_SAVE,ID_SAVEAS,ID_SAVEALL,ID_RELOAD,ID_CLOSE,ID_EXIT], zip(name, help, functs)))
        self.updateMenu(filemenu, [ID_NEW,ID_OPEN,ID_OPENMODULE,0,ID_SAVE,ID_SAVEAS,ID_SAVEALL,0,ID_RELOAD,ID_CLOSE,0,ID_EXIT], lkp)
        filemenu.InsertMenu(3, wxNewId(), "Open Recent", recentmenu)

#--------------------------------- Edit Menu ---------------------------------

        #more lines, but easier to understand.
        editmenu= wxMenu()
        name = ["Undo\tCtrl+Z",
                "Redo\tCtrl+Y",
                "Select All\tCtrl+A",
                "Cut\tCtrl+X",
                "Copy\tCtrl+C",
                "Paste\tCtrl+V",
                "Indent Region\tCtrl+]",
                "Dedent Region\tCtrl+[",
                "Find\tCtrl+F",
                "Replace\tCtrl+R",
                "Insert Snippet\tCtrl+return",
                "Insert Comment\tCtrl+I",
                "Comment Selection\tAlt+3",
                "Uncomment Selection\tAlt+4"]
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
                "Insert the currently selected snippet into the document",
                "Insert a centered comment",
                "Comment selected lines",
                "Uncomment selected lines"]
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
                  self.snippet.OnListBoxDClick,
                  self.OnInsertComment,
                  self.OnCommentSelection,
                  self.OnUncommentSelection]
        lkp = dict(zip([UD, RD, SA, CU, CO, PA, IR, DR, FI, RE, ISNIP, IC, CS, US], zip(name, help, functs)))
        self.updateMenu(editmenu, [UD, RD, 0, SA, CU, CO, PA, 0, IR, DR, 0, FI, RE, 0, 0, ISNIP, IC, CS, US], lkp)

        EVT_COMMAND_FIND(self, -1, self.OnFind)
        EVT_COMMAND_FIND_NEXT(self, -1, self.OnFind)
        EVT_COMMAND_FIND_REPLACE(self, -1, self.OnFind)
        EVT_COMMAND_FIND_REPLACE_ALL(self, -1, self.OnFind)
        EVT_COMMAND_FIND_CLOSE(self, -1, self.OnFindClose)

#-------------------------------- Style Menu ---------------------------------
        stylemenu= wxMenu()
        
        name = ["Python",
                "HTML",
                "XML",
                "C/C++",
                "Text"]
        help = ["Highlight for Python syntax",
                "Highlight for HTML syntax",
                "Highlight for XML syntax",
                "Highlight for C/C++ syntax",
                "No Syntax Highlighting"]
        functs = 5*[self.OnStyleChange]
        lkp = dict(zip([PY_S,HT_S,XM_S,CC_S,TX_S], zip(name, help, functs)))
        self.updateMenu(stylemenu, [PY_S,HT_S,XM_S,CC_S,TX_S], lkp)

#--------------------------------- View Menu ---------------------------------
        viewmenu= wxMenu()
        
        name = ["Zoom In\tCtrl+<plus>",
                "Zoom Out\tCtrl+<minus>",
                "Show/hide snippet bar\tCtrl+Shift+B",
                "Refresh (fast)\tF5",
                "Refresh (slow)\tShift+F5",
                "Show/hide tree\tCtrl+Shift+G"]
        help = ["Make everything bigger",
                "Make everything smaller",
                "Show/hide the global code snippet bar on the left",
                "Refresh the browsable source tree and autocomplete listing (sometimes inaccurate, but always fast)",
                "Refresh the browsable source tree, autocomplete listing, and the tooltips (always accurate, but sometimes slow)",
                "Show/hide the heirarchical source tree for the currently open document"]
        functs = 2*[self.OnZoom]+[self.OnSnippet, self.OnRefresh, self.OnRefreshSlow, self.OnTree]
        lkp = dict(zip([ZI,ZO,SNIP,REFRESH,REFRESHSLOW,BROWSE], zip(name, help, functs)))
        self.updateMenu(viewmenu, [ZI,ZO,0,SNIP,REFRESH,REFRESHSLOW,BROWSE], lkp)

        viewmenu.Append(AUTO, "Show Autocomplete",
                        "Show the autocomplete dropdown while typing",
                        wxITEM_CHECK)
        EVT_MENU(self, AUTO, self.OnAutoCompleteToggle)

#--------------------------------- Tab Menu ----------------------------------
        tabmenu= wxMenu()
        
        name = ["Previous Tab\tCtrl+,",
                "Next Tab\tCtrl+.",
                "Move tab left\tCtrl+Alt+,",
                "Move tab right\tCtrl+Alt+."]
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

#------------------------------- Snippet Menu --------------------------------
        snippetmenu= wxMenu()
        name = ["Previous snippet\tCtrl+Shift+,",
                "Next snippet\tCtrl+Shift+.",
                "Insert Snippet\tCtrl+return",
                "Show/hide snippet bar\tCtrl+Shift+B"]
        help = ["Select the previous code snippet",
                "Select the next code snippet",
                "Insert the currently selected snippet into the document",
                "Show/hide the global code snippet bar on the left"]
        functs = [self.snippet.OnSnippetP,
                  self.snippet.OnSnippetN,
                  self.snippet.OnListBoxDClick,
                  self.OnSnippet]
        lkp = dict(zip([PSNIP, NSNIP, ISNIP, SNIP], zip(name, help, functs)))
        self.updateMenu(snippetmenu, [PSNIP, NSNIP, ISNIP, SNIP], lkp)

#------------------------------- Pathmark Menu -------------------------------
        pathmarkmenu = wxMenu()
        name = ["View pathmarks", "Edit pathmarks\tCtrl+B", "Remove pathmark"]
        help = ["Edit your Pathmarks", "Add a path to your bookmarks", "Remove a bookmarked path"]
        functs = [self.ViewBookmarks, self.AddBookmark, self.RemoveBookmark]
        pmk = [BM1,BM2,BM3,BM4,BM5,BM6,BM7,BM8,BM9]
        tmp = [VIEW_BM,ADD_BM,DEL_BM]
        for i in xrange(49, 58):
            EVT_MENU(self, bmPm2Id[i], self.OnBookmark)
            if pathmarks.get(i, 0) != 0:
                name.append("Ctrl+%i\t%s"%(i-48, pathmarks[i]))
                help.append("Change the current working directory to %s"%pathmarks[i])
                functs.append(self.OnBookmark)
                tmp.append(pmk[i-49])
        lkp = dict(zip(tmp, zip(name, help, functs)))
        #print lkp
        self.updateMenu(pathmarkmenu, tmp[:3]+[0]+tmp[3:], lkp)

#--------------------------------- Help Menu ---------------------------------
        helpmenu= wxMenu()
        name = ["About...",
                "PyPE Help\tF1"]
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
        menuBar.Append(stylemenu,"S&tyle")
        menuBar.Append(viewmenu,"&View")
        menuBar.Append(tabmenu, "&Tabs")
        menuBar.Append(snippetmenu, "Sn&ippets")
        self.pm = pathmarkmenu
        menuBar.Append(pathmarkmenu, "&Pathmarks")
        self.shell = RunShell(self)
        menuBar.Append(self.shell, "&Shell")
        menuBar.Append(helpmenu, "&Help")
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
        self.menubar = menuBar

#-------------------------- Couple state variables ---------------------------
        self.Show(true)
        self.dirname = '.'
        self.closing = 0
        self.openfiles = {}
        self.dpm = 0
        self.menubar.Check(AUTO, self.config['showautocomp'])

#---------------- A nice lookup table for control keypresses -----------------
#-------------- it saves the trouble of a many if calls during ----------------
#---------------- control+keypress combos, which can't hurt ------------------

        self.ctrlpress=dict([
            #(13, self.snippet.OnListBoxDClick),#insert selected code snippet
            #(70, self.OnShowFind),      #find string with Ctrl+f
            #(82, self.OnShowFindReplace),#find and replace string with Ctrl+r
            #(73, self.OnInsertComment), #shifts current line down one, inserting a line-long comment
            #(78, self.OnNew),           #create a new document with Ctrl+n
            #(79, self.OnOpen),          #open an old document with Ctrl+o
            #(87, self.OnClose),         #close the currently open document with Ctrl+w
            #(83, self.OnSave),          #save the currently open document with Ctrl+s
            (93, self.OnIndent),        #indent the current line or selection of lines (indent) spaces with Ctrl+]
            (91, self.OnDedent),        #dedent the current line or selection of lines (indent) spaces with Ctrl+[
            (44, self.OnLeft),          #go to the tab to the left with Ctrl+, (same key as <)
            (46, self.OnRight)          #go to the tab to the right with Ctrl+. (same key as >)
            #(66, self.AddBookmark)      #open the 'edit pathmark' dialog
        ])
#------------------------------ Pathmark stuff -------------------------------
        self.ctrlpress.update(dict(zip(pathmarks.keys(), 10*[self.OnBookmark])))

#---------------------- Open files passed as arguments -----------------------
        for fname in fnames:
            if os.path.isfile(fname):
                fname = os.path.abspath(fname)
                dn,fn = os.path.split(fname)
                dn,fn = self.splitAbsolute(self.getAbsolute(fn, dn))
                try:
                    self.newTab(dn, fn, len(fnames)==1)
                    self.makeOpen(fn, dn)
                except:
                    pass

#------------------------ Drag and drop file support -------------------------
        self.SetDropTarget(FileDropTarget(self))

    def updateMenu(self, menu, menu_items, lookup):
        for i in menu_items:
            if i:
                menu.Append(i, lookup[i][0], lookup[i][1])
                EVT_MENU(self, i, lookup[i][2])
            else:
                menu.AppendSeparator()

    def dialog(self, message, title, styl=wxOK):
        d= wxMessageDialog(self,message,title,styl)
        retr = d.ShowModal()
        d.Destroy()
        return retr

    def exceptDialog(self, title="Error"):
        #I personally think the use of StringIO for tracebacks is neat...that's why I did it.
        k = cStringIO.StringIO()
        traceback.print_exc(file=k)
        k.seek(0)
        self.dialog(k.read(),title)

    def OnDrop(self, fnames):
        for i in fnames:
            i = os.path.normcase(os.path.normpath(i))
            if self.isAbsOpen(i):
                if len(fnames)==1:
                    self.selectAbsolute(i)
            else:
                self.makeAbsOpen(i)
                d,f = os.path.split(i)
                try:
                    self.newTab(d,f, len(fnames)==1)
                    self.SetStatusText("Opened %s"%i)
                except:
                    self.exceptDialog("File open failed")

#--------------------------- cmt-001 - 08/06/2003 ----------------------------
#-------------------------- File History Commands ----------------------------
    def loadHistory(self):
        if not os.path.exists(self.configPath):
            os.mkdir(self.configPath)
        path = os.path.join(self.configPath, 'history.txt')
        try:    self.config = self.readAndEvalFile(path)
        except: self.config = {}
        if 'history' in self.config:
            history = self.config['history']
            history.reverse()
            for h in history:
                self.fileHistory.AddFileToHistory(h)
        if 'lastpath' in self.config:
            self.lastpath = self.config['lastpath']
        for (nam, dflt) in [('showautocomp', 0),
                          ('paths', {}),
                          ('display2code', {}),
                          ('displayorder', []),
                          ('shellcommands', [])]:
            if not (nam in self.config):
                self.config[nam] = dflt
            globals()[nam] = self.config[nam]
        pathmarks.update(paths)
        #self.snippet.display2code = self.config['display2code']
        #self.snippet.displayorder = self.config['displayorder']
        #self.snippet.lb_refresh()
        
    def saveHistory(self):
        history = []
        for i in range(self.fileHistory.GetNoHistoryFiles()):
            history.append(self.fileHistory.GetHistoryFile(i))
        self.config['history'] = history
        a = []
        for i in self.shell.order:
            a.append(self.shell.menu[i])
        self.config['shellcommands'] = a
        self.config['paths'] = pathmarks
        self.config['display2code'] = self.snippet.display2code
        self.config['displayorder'] = self.snippet.displayorder
        self.config['lastpath'] = self.config.get('lp', os.getcwd())
        try:
            path = os.sep.join([self.configPath, 'history.txt'])
            f = open(path, "w")
            pprint.pprint(self.config, f)
            f.close()
        except:
            pass    # argh

    def readAndEvalFile(self, filename):
        f = open(filename)
        txt = f.read().replace('\r\n','\n')
        f.close()
        return eval(txt)
#------------------------- end cmt-001 - 08/06/2003 --------------------------

#---------------------------- File Menu Commands -----------------------------
    def selectAbsolute(self, path):
        if self.isAbsOpen(path):
            dn, fn = self.splitAbsolute(path)
            for i in xrange(self.control.GetPageCount()):
                win = self.control.GetPage(i).GetWindow1()
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
        return os.path.split(os.path.normcase(path))

    def OnNew(self,e):
        self.newTab('', ' ', 1)
        self.control.GetPage(self.control.GetSelection()).GetWindow1().opened = 1
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
                self.exceptDialog("Save Failed")
                raise cancelled
        else:
            self.OnSaveAs(e)

    def OnSaveAs(self,e):
        wnum, win = self.getNumWin(e)
        
        dlg = wxFileDialog(self, "Save file as...", os.getcwd(), "", "All files (*.*)|*.*", wxOPEN)
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
        for i in xrange(cnt):
            self.control.SetSelection(i)
            try:
                self.OnSave(e)
            except cancelled:
                pass
        if cnt:
            self.control.SetSelection(sel)
    
    def OnOpen(self,e):
#--------------------------- cmt-001 - 08/06/2003 ----------------------------
# Set the working directory to the last directory used or current working directory if it doesn't exist 
        wd = self.config.get('lastpath', os.getcwd())

#--------------------------- end cmt-001 - 08/06/2003 ----------------------------

        dlg = wxFileDialog(self, "Choose a/some file(s)...", wd, "", wildcard, wxOPEN| wxMULTIPLE)  #- cmt-001 - 08/06/2003  changed os.getcwd to wd
        if dlg.ShowModal() == wxID_OK:
            dn = dlg.GetDirectory()
            filenames = dlg.GetFilenames()
            for fn in filenames:
                self.OnDrop([self.getAbsolute(fn, dn)])
#--------------------------- cmt-001 - 08/06/2003 ----------------------------
# Add the just-opened file to the file history menu and set the last directory 
                self.fileHistory.AddFileToHistory(os.path.join(dn, fn))
            self.config['lp'] = dn
#--------------------------- end cmt-001 - 08/06/2003 ----------------------------
        dlg.Destroy()


    def FindModule(self, mod):
        fndmod = mod.split('.')
        lf = len(fndmod)        
        pth = sys.path[:]
        pth[1:1] = [os.getcwd()]
        for j in range(lf):
            i = fndmod[j]
            fdsc = imp.find_module(i, pth)
            if not (fdsc[0] is None):
                fdsc[0].close()
                mod = fdsc[1]
                if fdsc[2][2] != imp.PY_SOURCE:
                    return self.dialog("%s is not python source"%mod, "not correct format for editing")
                return mod
            elif fdsc[1]:
                pth[1:1] = [fdsc[1]]
            else:
                raise cancelled
        #If we are outside the loop, this means that the current 'module'
        #that we are on is a folder-module.  We can easily load the __init__.py
        #from this folder.  Rock.
        return os.sep.join([pth[1], '__init__.py'])

    def OnOpenModule(self,e):
        dlg = wxTextEntryDialog(self, 'Enter the module name you would like to open', 'Open module...')
        if dlg.ShowModal() == wxID_OK:
            mod = dlg.GetValue()
        else:
            mod = ''
        dlg.Destroy()
        if mod:
            try:
                return self.OnDrop([self.FindModule(mod)])
            except:
                return self.dialog("module %s not found"%mod, "not found")

    def newTab(self, d, fn, switch=0):
        if 'lastpath' in self.config:
            del self.config['lastpath']
        split = wxSplitterWindow(self.control, -1)
        split.parent = self
        nwin = PythonSTC(self.control, -1, split)
        nwin.split = split
        nwin.filename = fn
        nwin.dirname = d
        nwin.changeStyle(stylefile, self.style(fn))
        nwin.tree = HeirCodeTreePanel(self, split)
        split.SetMinimumPaneSize(3)
        split.SplitVertically(nwin, nwin.tree, -10)
        if d:
            f=open(os.sep.join([nwin.dirname,nwin.filename]),'rb')
            txt = f.read()
            f.close()
            nwin.format = detectLineEndings(txt)
            nwin.SetText(txt)
        else:
            nwin.format = eol
            nwin.SetText('')
        #print repr(nwin.format)
        self.control.AddPage(split, nwin.filename, switch)

    def OnReload(self, e):
        num, win = self.getNumWin(e)
        if win.dirty:
            dlg = wxMessageDialog(self, "%s was modified after last save.\nReloading from disk will destroy all changes.\n\nContinue anyway?"%win.filename, 'File was modified, data loss may occur!', wxYES_NO|wxCANCEL)
            a = dlg.ShowModal()
            if a == wxID_CANCEL:
                raise cancelled
            elif a == wxID_NO:
                return
        try:
            fil = open(self.getAbsolute(win.filename, win.dirname), 'rb')
            txt = fil.read()
            fil.close()
            win.SetText(txt, 0)
            win.MakeClean()
        except:
            self.dialog("Could not reload from disk", "Reload failed")

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
        self.saveHistory()
        return self.Close(true)

#--------------------------- cmt-001 - 08/06/2003 ----------------------------
#------------- Open the file selected from the file history menu -------------
    def OnFileHistory(self, e):
        
        fileNum = e.GetId() - wxID_FILE1
        path = self.fileHistory.GetHistoryFile(fileNum)
        self.OnDrop([path])
#------------------------- end cmt-001 - 08/06/2003 --------------------------

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
            if incr < 0:
                a = win.GetLineIndentation(lnstart)%(abs(incr))
                if a:
                    incr = -a
            pos = win.GetCurrentPos()
            col = win.GetColumn(pos)
            linestart = pos-col
            a = max(linestart+col+incr, linestart)
        else:
            lnstart = win.LineFromPosition(x)
            lnend = win.LineFromPosition(y-1)
        win.BeginUndoAction()
        for ln in xrange(lnstart, lnend+1):
            count = win.GetLineIndentation(ln)
            #print "indenting line", ln, count
            win.SetLineIndentation(ln, max(count+incr,0))
        if x==y:
            win.SetSelection(a, a)
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
            e.Skip()

## Added code from PythonCard's codeEditor to comment/uncomment selected lines 08-04-2003 Mark Tipton    
    def OnCommentSelection(self, e):
        wnum, win = self.getNumWin(e)
        sel = win.GetSelection()
        start = win.LineFromPosition(sel[0])
        end = win.LineFromPosition(sel[1])
        if end > start and win.GetColumn(sel[1]) == 0:
            end = end - 1
        win.MakeDirty()
        win.BeginUndoAction()
        for lineNumber in range(start, end + 1):
            firstChar = win.PositionFromLine(lineNumber)
            win.InsertText(firstChar, '##')
        win.SetCurrentPos(win.PositionFromLine(start))
        win.SetAnchor(win.GetLineEndPosition(end))
        win.EndUndoAction()

    def OnUncommentSelection(self, e):
        wnum, win = self.getNumWin(e)
        sel = win.GetSelection()
        start = win.LineFromPosition(sel[0])
        end = win.LineFromPosition(sel[1])
        if end > start and win.GetColumn(sel[1]) == 0:
            end = end - 1
        win.MakeDirty()
        win.BeginUndoAction()
        for lineNumber in range(start, end + 1):
            firstChar = win.PositionFromLine(lineNumber)
            if chr(win.GetCharAt(firstChar)) == '#':
                if chr(win.GetCharAt(firstChar + 1)) == '#':
                    # line starts with ##
                    win.SetCurrentPos(firstChar + 2)
                else:
                    # line starts with #
                    win.SetCurrentPos(firstChar + 1)
                win.DelLineLeft()

        win.SetCurrentPos(win.PositionFromLine(start))
        win.SetAnchor(win.GetLineEndPosition(end))
        win.EndUndoAction()
## End modifications 08-04-2003 Mark Tipton  

#--------------------- Find and replace dialogs and code ---------------------
    def getNumWin(self, e):
        num = self.control.GetSelection()
        if num >= 0:
            return num, self.control.GetPage(num).GetWindow1()
        e.Skip()
        raise cancelled

    def OnShowFind(self, evt):
        wcount = self.control.GetPageCount()
        if not wcount:
            return evt.Skip()
        for wnum in xrange(wcount):
            win = self.control.GetPage(wnum).GetWindow1()
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
            win = self.control.GetPage(wnum).GetWindow1()
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
                    win.EnsureCaretVisible()
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
                a = win.FindText(win.last, win.GetTextLength(), findTxt, evt.GetFlags())
                win.SetSelection(a, a+len(findTxt))
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
        win.changeStyle(stylefile, lexers[e.GetId()])
    def style(self, fn):
        ext = fn.split('.')[-1].lower()
        return extns.get(ext, 'python')
    def OnZoom(self, e):
        wnum, win = self.getNumWin(e)
        if e.GetId() == ZI:incr = 1
        else:              incr = -1
        win.SetZoom(win.GetZoom()+incr)
        
#---------------------------- View Menu Commands -----------------------------
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

    def OnSnippet(self, e, resize=0):
        split = self.split
        num = self.control.GetSelection()
        if num != -1:
            resize = 1
            width = self.control.GetClientSize()[0]
            orig = self.control.GetPage(num).GetSashPosition()
        if split.GetSashPosition() < 10:
            split.SetSashPosition(100)
        else:
            split.SetSashPosition(split.GetMinimumPaneSize())
        if resize:
            delta = self.control.GetClientSize()[0]-width
            self.control.GetPage(num).SetSashPosition(orig+delta)

    def OnTree(self, e):
        num, win = self.getNumWin(e)
        split = self.control.GetPage(num)
        width = self.control.GetClientSize()[0]-10
        if (width-split.GetSashPosition())<10:
            split.SetSashPosition(width-100)
        else:
            split.SetSashPosition(width-split.GetMinimumPaneSize())
        

    def OnRefresh(self, e):
        num, win = self.getNumWin(e)
        win.heirarchy, win.kw = fast_parser(win.GetText(), win.format)
        win.kw.sort()
        win.kw = ' '.join(win.kw)
        win.tree.new_heirarchy(win.heirarchy)

    def OnRefreshSlow(self, e):
        num, win = self.getNumWin(e)
        try:
            self.SetStatusText("Working...(can take up to 20 seconds for large sources and slow computers)")
            win.heirarchy, win.kw, win.tooltips = slow_parser(win.GetText(), win.format, 2)
            self.SetStatusText("")
        except exceptions.Exception, e:
            self.SetStatusText("%s, using fast_parser, tooltips may be unavailable"%str(e))
            win.heirarchy, win.kw = fast_parser(win.GetText(), win.format)
        win.kw.sort()
        win.kw = ' '.join(win.kw)
        win.tree.new_heirarchy(win.heirarchy)


    def OnAutoCompleteToggle(self, event):
        # Images are specified with a appended "?type"
        #for i in range(len(kw)):
        #    if kw[i] in keyword.kwlist:
        #        kw[i] = kw[i]# + "?1"
        self.config['showautocomp'] = (self.config.get('showautocomp', 0) + 1)%2
        globals()['showautocomp'] = self.config['showautocomp']
#------------------------- Bookmarked Path Commands --------------------------
    def OnBookmark(self, e, st=type('')):
        if 'lastpath' in self.config:
            del self.config['lastpath']
        try:
            key = e.GetKeyCode()
            pth = pathmarks.get(key)
        except:
            pth = pathmarks[bmId2Keypress[e.GetId()]]
        if (type(pth) is st) and os.path.isdir(pth):
            os.chdir(pth)
            self.SetStatusText("Changed path to %s"%pth)

    def ViewBookmarks(self, e, titl="Pathmarks", styl=wxOK, sel=0, st=type('')):
        kys = pathmarks.keys()
        kys.sort()
        out = []
        for i in kys:
            if type(pathmarks[i]) is st:
                out.append("%i            %s    "%(i-48, pathmarks[i]))
            else:
                out.append("%i            <unused>    "%(i-48))

        dlg = wxSingleChoiceDialog(self, "Pathmark       Path",titl, out, styl|wxDD_DEFAULT_STYLE)
        dlg.SetSelection(sel)
        if dlg.ShowModal() == wxID_OK:
            retr = dlg.GetStringSelection()
        else:
            retr = None
        dlg.Destroy()
        return retr
        
    def AddBookmark(self, e):
        pth = self.ViewBookmarks(e, "Select a pathmark to update", wxOK|wxCANCEL)
        while pth != None:
            posn = int(pth[0])-1
            opth = pathmarks[posn+1+48]
            if opth == 0: opth = os.getcwd()
            dlg = wxDirDialog(self, "Choose a path", opth, style=wxDD_DEFAULT_STYLE|wxDD_NEW_DIR_BUTTON)
            if dlg.ShowModal() == wxID_OK:
                pmn = posn+1+48
                path = dlg.GetPath()
                self.dpm = 1
                self.remPos(pmn)
                self.addPos(pmn, path)
            else:
                self.SetStatusText("Pathmark modification aborted")
            pth = self.ViewBookmarks(e, "Select a pathmark to update", wxOK|wxCANCEL, posn)
        self.SetStatusText("Finished updating pathmarks")

    def itemPos(self, pmn):
        cnt = 0
        for i in xrange(49, pmn):
            if pathmarks[i] != 0:
                cnt += 1
        return cnt

    def remPos(self, pmn):
        if pathmarks[pmn] != 0:
            posn = self.itemPos(pmn)
            a = pathmarks[pmn]
            self.pm.Delete(self.pm.GetMenuItems()[posn+4].GetId())
            pathmarks[pmn] = 0
            self.SetStatusText("Deleted %s from bookmark %i"%(a, pmn-48))

    def addPos(self, pmn, path):
        posn = self.itemPos(pmn)
        self.pm.Insert(posn+4, bmPm2Id[pmn], "Ctrl+%i\t%s"%(pmn-48, path), "Change the current working directory to %s"%path)
        pathmarks[pmn] = path
        self.SetStatusText("Set bookmark %i to %s"%(pmn-48, path))

    def RemoveBookmark(self, e):
        pth = self.ViewBookmarks(e, "Delete pathmark (cancel to finish)", wxOK|wxCANCEL)
        while pth != None:
            self.dpm = 1
            posn = int(pth[0])-1
            pmn = posn+1+48
            if pathmarks[pmn] != 0:
                self.remPos(pmn)
            pth = self.ViewBookmarks(e, "Delete pathmark (cancel to finish)", wxOK|wxCANCEL, posn)

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
        showpress=0
        if showpress: print "keypressed", event.KeyCode()
        key = event.KeyCode()
        wnum = self.control.GetSelection()
        pagecount = self.control.GetPageCount()
        if wnum > -1:
            win = self.control.GetPage(wnum).GetWindow1()
            #print win.GetStyleAt(win.GetCurrentPos()-1), win.GetStyleAt(win.GetCurrentPos()), win.GetStyleAt(win.GetCurrentPos()+1)
            #if win.CallTipActive():
            #    win.CallTipCancel()
        if event.ShiftDown() and event.ControlDown():
            if key == ord(','):
                self.snippet.OnSnippetP(event)
            elif key == ord('.'):
                self.snippet.OnSnippetN(event)
        if event.ControlDown() and event.AltDown():
            #commands for both control and alt pressed

            #shift current tab left with Ctrl+Alt+, (same key as <)
            if key == ord(','):
                self.MoveLeft(event)
            #shift current tab right with Ctrl+Alt+. (same key as >)
            elif key == ord('.'):
                self.MoveRight(event)
            else:
                return event.Skip()
        elif event.ControlDown():
            #commands for just control pressed
            if key in self.ctrlpress:
                #only works for self.function(event) commands
                self.ctrlpress[key](event)
            elif pagecount >= 1:
                #makes document dirty on cut, paste, undo, redo
                if dirty_edit.get(key, 0):
                    win.MakeDirty(event)
                else:
                    event.Skip()
            else:
                event.Skip()
        #elif event.AltDown():
        #    #events for just the alt key down
        #    event.Skip()
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
            if pagecount:
                if (key==13):
                    #when 'enter' is pressed, indentation needs to happen.
                    #
                    #will indent the current line to be equivalent to the line above
                    #unless a ':' is at the end of the previous, then will indent
                    #configuration.indent more.
                    if win.AutoCompActive():
                        return win.AutoCompComplete()
                    #get information about the current cursor position
                    linenum = win.GetCurrentLine()
                    pos = win.GetCurrentPos()
                    col = win.GetColumn(pos)
                    line = win.GetLine(linenum)[:col]
                    linestart = pos-col

                    #get info about the current line's indentation
                    ind = win.GetLineIndentation(linenum)
                    colon = ord(':')
                    if col <= ind:
                        win.ReplaceSelection(win.format+col*' ')
                    elif pos:
                        xtra = 0
                        if (line.find(':')>-1):
                            for i in xrange(linestart, min(pos, win.GetTextLength())):
                                styl = win.GetStyleAt(i)
                                #print styl, win.GetCharAt(i)
                                if not xtra:
                                    if (styl==10) and (win.GetCharAt(i) == colon):
                                        xtra = 1
                                elif (styl == 1):
                                    #it is a comment, ignore the character
                                    pass
                                elif (styl == 0) and (win.GetCharAt(i) in [ord(i) for i in ' \t\r\n']):
                                    #is not a comment, but is the space before a comment
                                    #or the end of a line, ignore the character
                                    pass
                                else:
                                    #this is not a comment or some innocuous other character
                                    #this is a docstring or otherwise, no additional indent
                                    xtra = 0
                                    break
                            if xtra:
                                #This deals with ending single and multi-line definitions properly.
                                while linenum >= 0:
                                    found = []
                                    for i in ['def', 'class', 'if', 'else', 'while',
                                              'for', 'try', 'except', 'finally']:
                                        #'elif' is found while searching for 'if'
                                        a = line.find(i)
                                        if (a > -1):
                                            found.append(a)
                                    #print 'fnd', found
                                    if found: found = min(found)
                                    else:     found = -1
                                    if (found > -1) and\
                                       (win.GetStyleAt(win.GetLineEndPosition(linenum)-len(line)+found)==5) and\
                                       (win.GetLineIndentation(linenum) == found):
                                           ind = win.GetLineIndentation(linenum)
                                           break
                                    linenum -= 1
                                    line = win.GetLine(linenum)
                        #if we were to do indentation for ()[]{}, it would be here
                        if not xtra:
                            #yep, right here.
                            fnd = 0
                            for i in "(){}[]":
                                if (line.find(i) > -1):
                                    fnd = 1
                                    break
                            if fnd:
                                seq = []
                                #print "finding stuff"
                                for i in "(){}[]":
                                    a = line.find(i)
                                    start = 0
                                    while a > -1:
                                        start += a+1
                                        if win.GetStyleAt(start+linestart-1)==10:
                                            seq.append((start, i))
                                        a = line[start:].find(i)
                                seq.sort()
                                cl = {')':'(', ']': '[', '}': '{',
                                      '(':'',  '[': '',  '{': ''}
                                stk = []
                                #print "making tree"
                                for po, ch in seq:
                                    #print ch,
                                    if not cl[ch]:
                                        #standard opening
                                        stk.append((po, ch))
                                    elif stk:
                                        if cl[ch] == stk[-1][1]:
                                            #proper closing of something
                                            stk.pop()
                                        else:
                                            #probably a syntax error
                                            #does it matter what is done?
                                            stk = []
                                            break
                                    else:
            #Probably closing something on another line, should probably find
            #the indent level of the opening, but that looks to be a hard
            #problem, and multiple lines would need to be checked for the
            #location of the closing item.
            #This would require an incremental line-by-line stepping back.
            #Almost like what was done for ['def', 'class', 'if', 'while', 'for']
            #and ':'.  However, there is no guarantee that there is a proper
            #start, and we could end up parsing the entire file...a few times
            #over.  Incremental backwards things end up doing worst case
            #O(n^2) line parsings.
            #Fuck that.
            #People can use the improved single-line dedent with crtl+[.
                                        stk = []
                                        break
                                if stk:
                                    #print "stack remaining", stk
                                    ind = stk[-1][0]
                        if xtra:
                            #print ind
                            ind += indent
                        win.ReplaceSelection(win.format+ind*' ')
                    else:
                        win.ReplaceSelection(win.format)
                    #chrs = ''
                    #for i in xrange(3):
                    #    chrs += chr(win.GetCharAt(pos+i))
                    #print repr(win.format), repr(chrs)
                    #win.SetLineIndentation(ln, ind)
                else:
                    event.Skip()
                    if not (win.GetStyleAt(win.GetCurrentPos())):
                        #3, 13, 6, 7
                        if win.CallTipActive():
                            good = {}
                            for i in STRINGPRINTABLE:
                                good[ord(i)] = None
                            if (key in good) or (key in (WXK_SHIFT, WXK_CONTROL)):
                                if key in (48, 57) and event.ShiftDown():
                                    win.CallTipCancel()
                                #else it is something in the arguments that is OK.
                            else:
                                win.CallTipCancel()
                        if (not win.CallTipActive()) and event.ShiftDown() and (key == ord('9')):
                            win.CallTipSetBackground(wxColour(255, 255, 232))
                            cur, colpos, word = self.getLeftFunct(win)
                            tip = '\n'.join(win.tooltips.get(word, []))
                            if tip:
                                win.CallTipShow(win.GetCurrentPos(),tip)
                        elif showautocomp and bool(win.kw) and (not win.AutoCompActive()) and (ord('A') <= key) and (key <= ord('Z')):
                            #if win.CallTipActive():
                            #    win.CallTipCancel()
                            cur, colpos, word = self.getLeftFunct(win)
                            indx = win.kw.find(word)
                            if (not word) or ((indx > -1) and ((win.kw[indx-1] == ' ') or (indx==0))):
                                win.AutoCompSetIgnoreCase(False)
                                win.AutoCompShow(colpos-cur, win.kw)
            else:
                return event.Skip()

    def getLeftFunct(self, win):
        t = ' .,;:([)]}\'"\\<>%^&+-=*/|`'
        bad = dict(zip(t, [0]*len(t)))
        line = win.GetLine(win.GetCurrentLine())
        colpos = win.GetColumn(win.GetCurrentPos())
        cur = colpos-1
        while (cur >= 0) and not (line[cur:cur+1] in bad):
            cur -= 1
        cur += 1
        return cur, colpos, line[cur:colpos]

#------------- Ahh, Styled Text Control, you make this possible. -------------
class PythonSTC(wxStyledTextCtrl):
    def __init__(self, parent, ID, prnt):
        wxStyledTextCtrl.__init__(self, prnt, ID, style = wxNO_FULL_REPAINT_ON_RESIZE)
        
        self.heirarchy = []
        self.kw = []
        self.tooltips = {}

        self.prnt = prnt
        self.parent = parent
        self.dirty = 0
        
        #Text is included in the original, but who drags text?  Below for dnd file support.
        if dnd_file: self.SetDropTarget(FileDropTarget(self.parent.parent))

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
        self.AutoCompStops(' .,;:([)]}\'"\\<>%^&+-=*/|`')

#-------------------- fix for SetText for the 'dirty bit' --------------------
    def SetText(self, txt, emptyundo=1):
        self.SetEOLMode(fmt_mode[self.format])
        wxStyledTextCtrl.SetText(self, txt)
        self.opened = 1
        self.heirarchy, self.kw = fast_parser(txt, self.format)
        self.kw.sort()
        self.kw = ' '.join(self.kw)
        self.tree.new_heirarchy(self.heirarchy)
        if emptyundo:
            self.EmptyUndoBuffer()

#----- Takes care of the little '*' modified next to the open file name ------
    def MakeDirty(self, e=None):
        if (not self.dirty) and self.opened:
            self.dirty = 1
            self.parent.SetPageText(self.parent.GetSelection(), '* '+self.filename)
            self.parent.Refresh(False)
            self.do(self.nada)
        if e:
            e.Skip()

    def nada(self, e):
        pass

    def MakeClean(self, e=None):
        self.dirty = 0
        self.parent.SetPageText(self.parent.GetSelection(), self.filename)
        self.parent.Refresh(False)
        self.do(self.nada, 0)
        if e:
            e.Skip()

    def do(self, funct, dirty=1):
        if dirty: self.MakeDirty(None)
        funct(self)
        a = self.prnt.GetSashPosition()
        self.prnt.SetSashPosition(a-1)
        self.prnt.SetSashPosition(a)
        #self.parent.Refresh(False)
        #self.prnt.Refresh(False)
        #self.prnt.GetWindow2().Refresh(False)
        #self.Refresh(False)

    def Cut(self):      self.do(wxStyledTextCtrl.Cut)
    def Paste(self):    self.do(wxStyledTextCtrl.Paste)
    def Undo(self):     self.do(wxStyledTextCtrl.Undo)
    def Redo(self):     self.do(wxStyledTextCtrl.Redo)

#--------- Ahh, the style change code...isn't it great?  Not really. ---------
    def changeStyle(self, stylefile, language):
        try:
            #from StyleSupport import initSTC
            from STCStyleEditor import initSTC
            initSTC(self, stylefile, language)

        except:
            self.parent.parent.exceptDialog("Style Change failed, assuming Python")
            
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
    def __init__(self, parent, id, pparent):
        #the left-tab, while being nice, turns the text sideways, ick.
        wxNotebook.__init__(self, pparent, id, style=
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
        
        self.SetDropTarget(FileDropTarget(self.parent))

    def OnPageChanged(self, event):
        new = event.GetSelection()
        #fix for dealing with current paths.  They are wonderful.
        if new > -1:
            win = self.GetPage(new).GetWindow1()
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
        #self.parent.Refresh(False)
        #self.Refresh(False)

class FileDropTarget(wxFileDropTarget):
    def __init__(self, parent):
        wxFileDropTarget.__init__(self)
        self.parent = parent
    def OnDropFiles(self, x, y, filenames):
        self.parent.OnDrop(filenames)

class TextDropTarget(wxTextDropTarget):
    def __init__(self, parent):
        wxTextDropTarget.__init__(self)
        self.parent = parent

    def OnDropText(self, x, y, text):
        self.parent.OnDropText(text)
        #This is so that you can keep your document unchanged while adding
        #code snippets.
        return False

class CodeSnippet(wxPanel):
    def __init__(self, parent, id, pparent, display2code, displayorder):
        wxPanel.__init__(self, pparent, id)
        self.parent = parent

        self.display2code = display2code
        self.displayorder = displayorder
        self.dirty = 0

        self.lb = wxListBox(self, LB_ID, choices = self.displayorder, style=wxLB_SINGLE|wxLB_NEEDED_SB)
        EVT_LISTBOX_DCLICK(self, LB_ID, self.OnListBoxDClick)
        EVT_KEY_DOWN(self.lb, self.OnKeyPressed)

        self.SetDropTarget(TextDropTarget(self))
        self.lb.SetDropTarget(TextDropTarget(self))

        sizer = RowColSizer()
        sizer.Add(self.lb, flag=wxEXPAND, row=0, col=0)
        sizer.AddGrowableRow(0)
        sizer.AddGrowableCol(0)
        self.SetSizer(sizer)
        self.SetAutoLayout(True)

    def lb_refresh(self):
        self.lb.Clear()
        self.lb.Set(self.displayorder)

    def OnKeyPressed(self,e):
        key = e.KeyCode()
        if key in [WXK_DELETE, WXK_BACK] and self.displayorder:
            self.OnListBoxDelete(e)
        elif key == 86 and e.ControlDown():
            wxTheClipboard.Open()
            tmp = wxTheClipboard.GetData()
            wxTheClipboard.Close()
            self.OnDropText(tmp)
        elif key == 13:
            self.OnListBoxDClick(e)
        else:
            e.Skip()

    def OnListBoxDClick(self, e):
        num, win = self.parent.getNumWin(e)
        sel = self.lb.GetSelection()
        if sel < 0:
            return e.Skip()
        code = self.display2code.get(self.displayorder[sel], '')
        if code != '':
            win.ReplaceSelection(code)
            win.MakeDirty()
            win.SetFocus()

    def OnListBoxDelete(self, e):
        disp = self.lb.GetSelection()
        if disp >= 0:
            self.dirty = 1
            a = self.displayorder[disp]
            del self.display2code[a]
            self.lb.Delete(disp)
            self.displayorder.pop(disp)
            cnt = self.lb.GetCount()
            #if this is the last snippet in the list, select the previous
            #snippet (if one exists)
            if disp == cnt:
                if cnt > 0:
                    self.lb.SetSelection(disp-1)
            #otherwise select the snippet that is just after this one
            else:
                self.lb.SetSelection(disp)
        else:   e.Skip()
    
    def OnDropText(self, text):
        rpt = 0
        str1 = 'What would you like this code snippet to be called?'
        err = {0:'',
               1:'Snippet name already used, please choose another.\n\n',
               2:'Snippet is composed entirely of blank characters,\nplease choose another.\n\n'
               }
        while 1:
            dlg = wxTextEntryDialog(self, err[rpt]+str1, 'Snippet Name')
            if dlg.ShowModal() == wxID_OK:
                nam = dlg.GetValue().strip()
            else:
                nam = None
            dlg.Destroy()
            if nam != None:
                if not nam: rpt = 2;self.parent.SetStatusText("Snippet name will not display")
                elif not nam in self.display2code:
                    self.display2code[nam] = text[:]
                    self.displayorder.append(nam)
                    self.lb.Append(nam)
                    self.dirty = 1
                    return self.parent.SetStatusText("Snippet %s added"%nam)
                else: rpt = 1;self.parent.SetStatusText("Snippet name already used")
            else: self.parent.SetStatusText("Snippet addition aborted");return

    def seladj(self, incr):
        cnt = self.lb.GetCount()
        if cnt:
            self.lb.SetSelection((self.lb.GetSelection()+incr)%cnt)

    def OnSnippetP(self, e):
        self.seladj(-1)
    def OnSnippetN(self, e):
        self.seladj(1)
    

class RunShell(wxMenu):
    def __init__(self, parent):
        wxMenu.__init__(self)
        self.parent = parent
        
        cur = [("Run current file", "Run the current open file", self.runScript),
               ("View shell commands", "View the list of shell command working paths and the command that would be executed", self.viewShellCommands),
               ("Edit shell command", "Edit a pre-existing shell command", self.editShellCommand),
               ("Add shell command", "Add a shell command to this menu", self.addShellCommand),
               ("Remove shell command", "Remove a shell command from this menu", self.removeShellCommand)]
        
        for i in range(5):
            a = wxNewId()
            self.Append(a, cur[i][0], cur[i][1])
            EVT_MENU(self.parent, a, cur[i][2])

        self.AppendSeparator()
        
        #parse settings file, adding the menu
        #format will be:
        #[("name in menu", "working path", "command args"), ...]
        self.menu = {}
        self.order = []
        for i in shellcommands:
            apply(self.appendShellCommand, i)
        
        self.dirty = 0

        self.cnt = 6

    def runScript(self, evt):
        num, win = self.parent.getNumWin(evt)
        use = self.makeuse(win.dirname, win.filename)
        os.system("%s %s %s"%(os.path.join(runpath, 'runscript.py'), use['path'], use['full']))

    def viewShellCommands(self, event, titl="Shell Commands", styl=wxOK, sel=0, st=type('')):
        count = 1
        out = []
        for i in self.order:
            out.append("%i          %s    "%(count, repr(self.menu[i])))
            count += 1
        dlg = wxSingleChoiceDialog(self.parent, "order      (name, working dir, command, arguments)", titl, out, styl|wxDD_DEFAULT_STYLE)
        if self.order:
            dlg.SetSelection(min(len(self.order)-1, sel))
        if dlg.ShowModal() == wxID_OK:
            a = dlg.GetStringSelection()
            if a:
                retr = int(dlg.GetStringSelection()[:].split(' ', 1)[0])-1
            else:
                retr = None
        else:
            retr = None
        dlg.Destroy()
        return retr

    def editShellCommand(self, event):
        title = "Choose a shell command to edit"
        style = wxOK|wxCANCEL
        tmp = self.viewShellCommands(event, title, style)
        while tmp != None:
            a = self.order[tmp]
            a1, a2, a3 = self.menu[a]
            if self.addShellCommand(event, a1, a2, a3, tmp) != None:
                del self.order[tmp+1]
                del self.menu[a]
                self.Delete(a)
            self.parent.SetStatusText("Edited shell command named %s"%a1)
            tmp = self.viewShellCommands(event, title, style, min(tmp, len(self.order)))

    def addShellCommand(self, event, a1='', a2='', a3='', posn=-1):
        commandname = a1
        recentcwd = a2 
        recentexec = a3
        scaa = "Shell command addition aborted"
        ex = {'path':runpath, 'file':os.path.split(sys.argv[0])[1]}
        ex['full'] = os.path.join(ex['path'], ex['file'])
        hlp = """What is given is completely unchanged, except for those that include the
        below string expansions:
        %(path)s  ->  The path of the file that is currently open
        %(file)s    ->  The name of the file that is currently open
        %(full)s    ->  The equivalent of os.path.join(path, file)
        All other expansions will cause an exception dialog, and your shell
        command will not run.
        
        Spaces in the above expansions, are handled properly for your system.
        Spaces in the paths you enter manually are not repaired.
        If you have paths or arguments that require spaces, other than the above
        expansions, you must repair them yourself.
        For example:
        If I wanted to ssh to another machine to run a command, like ps mayhaps...
        In *nix arguments: hostname ps -u user
        In windows arguments: hostname "ps -u user"
        
        If we were passing files as arguments while connecting to a *nix host...
        In *nix arguments: hostname cat file\\ name\\ with\\ spaces
        In windows arguments: hostname "cat file\\ name\\ with\\ spaces"
        
        Play around, you'll figure it out.
        """.replace('        ', '')
        while 1:
            
            dlg = wxTextEntryDialog(self.parent, "What would you like your command to be called?", "Command name")
            dlg.SetValue(commandname)
            rslt = dlg.ShowModal()
            commandname = dlg.GetValue()
            dlg.Destroy()
            if rslt != wxID_OK:
                return self.parent.SetStatusText(scaa)
            
            dlg = wxTextEntryDialog(self.parent, hlp, "Choose a working directory (if any)")
            dlg.SetValue(recentcwd)
            rslt = dlg.ShowModal()
            recentcwd = dlg.GetValue()
            dlg.Destroy()
            if rslt != wxID_OK:
                return self.parent.SetStatusText(scaa)
            
            dlg = wxTextEntryDialog(self.parent, hlp, "Enter the command as you would in a console (including arguments)")
            dlg.SetValue(recentexec)
            rslt = dlg.ShowModal()
            recentexec = dlg.GetValue()
            dlg.Destroy()
            if rslt != wxID_OK:
                return self.parent.SetStatusText(scaa)
            
            cmd = recentexec
            
            out = "The functional equivalent to the following will be\nevalutated when the menu item is started, if the\nsource file for this editor was currently being viewed:\n\n"
            if recentcwd:
                out += 'cd %s\n'%recentcwd%ex
            out += cmd%ex
            if self.parent.dialog(out, "Is this correct?", styl=wxYES_NO) == wxID_YES:
                self.appendShellCommand(commandname, recentcwd, recentexec, posn)
                self.parent.SetStatusText("Added shell command")
                return 1
            else:
                self.parent.SetStatusText("Editing shell command")

    def removeShellCommand(self, event):
        title = "Choose a shell command to remove"
        style = wxOK|wxCANCEL
        tmp = self.viewShellCommands(event, title, style)
        while tmp != None:
            a = self.order.pop(tmp)
            b = self.menu[a]
            del self.menu[a]
            self.Delete(a)
            self.parent.SetStatusText("Removed shell command named %s"%b[0])
            tmp = self.viewShellCommands(event, title, style, min(tmp, len(self.order)))

    def OnMenu(self, evt):
        try:
            (name, path, command) = self.menu[evt.GetId()]
            try:
                num, win = self.parent.getNumWin(evt)
                dn = win.dirname
                fn = win.filename
            except:
                dn = '.'
                fn = ''

            use = self.makeuse(dn, fn)
            if sys.platform=='win32':
                if (path.find(' ')+1): path = '"%s"'%path
                if (command.find(' ')+1): command = '"%s"'%command
            else:
                if (path.find(' ')+1): path = path.replace(' ', '\\ ')
                if (command.find(' ')+1): command = command.replace(' ', '\\ ')

            os.system("%s %s %s"%(os.path.join(runpath, 'runscript.py'), path or '*', command)%use)
        except:
            self.parent.exceptDialog()

    def makeuse(self, dn, fn):
        use = {}
        if sys.platform=='win32':
            if (dn.find(' ')+1): use['path'] = '"%s"'%dn
            else:                use['path'] = dn
            if (fn.find(' ')+1): use['file'] = '"%s"'%fn
            else:                use['file'] = fn
            use['full'] = os.path.join(use['path'], use['file'])
        else:
            if (dn.find(' ')+1): use['path'] = dn.replace(' ', '\\ ')
            else:                use['path'] = dn
            if (fn.find(' ')+1): use['file'] = fn.replace(' ', '\\ ')
            else:                use['file'] = fn
            use['full'] = os.path.join(use['path'], use['file'])
        return use


    def appendShellCommand(self, name, path, command, posn=-1):
        self.dirty = 1
        a = wxNewId()
        if posn == -1:
            self.Append(a, name)
            self.order.append(a)
        else:
            self.Insert(posn+self.cnt, a, name)
            self.order.insert(posn, a)
        EVT_MENU(self.parent, a, self.OnMenu)
        self.menu[a] = (name, path, command)

class HeirCodeTreePanel(wxPanel):
    class TreeCtrl(wxTreeCtrl):
        def __init__(self, parent, prnt, tid):
            wxTreeCtrl.__init__(self, prnt, tid, style=wxTR_DEFAULT_STYLE|wxTR_HAS_BUTTONS|wxTR_HIDE_ROOT)
            self.parent = parent
            
            isz = (16,16)
            il = wxImageList(isz[0], isz[1])
            self.images = [wxArtProvider_GetBitmap(wxART_FOLDER, wxART_OTHER, isz),
                      wxArtProvider_GetBitmap(wxART_FILE_OPEN, wxART_OTHER, isz),
                      wxArtProvider_GetBitmap(wxART_HELP_PAGE, wxART_OTHER, isz)]
            for i in self.images:
                il.Add(i)
            self.SetImageList(il)
            self.il = il

        def OnCompareItems(self, item1, item2):
            return cmp(self.GetItemData(item1).GetData(), self.GetItemData(item2).GetData())
        
        def GetRootItem(self):
            return self.root

        def getchlist(self, parent):
            #when using ItemHasChildren(parent)
            #an assert exception saying "can't retrieve virtual root item"
            #kept coming up.
            #for some reason GetChildrenCount(parent, 0) doesn't.
            numchildren = self.GetChildrenCount(parent, 0) 
            lst = {}
            if numchildren>0:
                ch, cookie = self.GetFirstChild(parent, wxNewId())
                lst[self.GetItemText(ch)] = [ch]
                for i in xrange(numchildren-1):
                    ch, cookie = self.GetNextChild(parent, cookie)
                    txt = self.GetItemText(ch)
                    if txt in lst:
                        lst[txt].append(ch)
                    else:
                        lst[txt] = [ch]
            return lst

    def __init__(self, parent, prnt):
        # Use the WANTS_CHARS style so the panel doesn't eat the Return key.
        wxPanel.__init__(self, prnt, -1, style=wxWANTS_CHARS)
        EVT_SIZE(self, self.OnSize)

        self.parent = parent

        tID = wxNewId()

        self.tree = self.TreeCtrl(parent, self, tID)
        self.root = self.tree.AddRoot("Unseen Root")
        self.tree.root = self.root

        #self.tree.Expand(self.root)
        EVT_LEFT_DCLICK(self, self.OnLeftDClick)
        EVT_TREE_ITEM_ACTIVATED (self, tID, self.OnActivate)

    def new_heirarchy(self, heir):
        #self.tree.DeleteAllItems()
        root = [self.root]
        stk = [(self.tree.getchlist(self.root), heir)]
        while stk:
            chlist, cur = stk.pop()
            while cur:
                name, line_no, leading, children = cur.pop()
                if name in chlist:
                    item_no = chlist[name].pop()
                    if not chlist[name]:
                        del chlist[name]
                    self.tree.SetPyData(item_no, line_no)
                    icons = 0
                else:
                    item_no = self.tree.AppendItem(root[-1], name)
                    self.tree.SetPyData(item_no, line_no)
                    icons = 1
                if children:
                    if icons:
                        self.tree.SetItemImage(item_no, 0, wxTreeItemIcon_Normal)
                        self.tree.SetItemImage(item_no, 1, wxTreeItemIcon_Expanded)
                    stk.append((chlist, cur))
                    root.append(item_no)
                    chlist = self.tree.getchlist(item_no)
                    cur = children
                elif icons:
                    self.tree.SetItemImage(item_no, 2, wxTreeItemIcon_Normal)
                    self.tree.SetItemImage(item_no, 2, wxTreeItemIcon_Selected)
            for j in chlist.itervalues():
                for i in j:
                    self.tree.DeleteChildren(i)
                    self.tree.Delete(i)
            self.tree.SortChildren(root[-1])
            root.pop()

    def OnSize(self, event):
        w,h = self.GetClientSizeTuple()
        self.tree.SetDimensions(0, 0, w, h)

    def OnLeftDClick(self, event):
        #pity this doesn't do what it should.
        num, win = self.parent.getNumWin(event)
        win.SetFocus()

    def OnActivate(self, event):
        num, win = self.parent.getNumWin(event)
        dat = self.tree.GetItemData(event.GetItem()).GetData() 
        if dat == None:
            return event.Skip()
        ln = dat[1]
        #print ln
        #print dir(win)
        linepos = win.GetLineEndPosition(ln)
        win.EnsureVisible(ln)
        win.SetSelection(linepos-len(win.GetLine(ln))+len(win.format), linepos)
        win.ScrollToColumn(0)
        win.SetFocus()

#--------------------------- And the main...*sigh* ---------------------------
import wx
VS = wx.VERSION_STRING
del wx

def main():
    app = wxPySimpleApp()
    if VS < VREQ:
        app.frame = wxFrame(None, -1, "Improper version of wxPython")
        dlg = wxMessageDialog(app.frame, "PyPE is only known to run on wxPython %s or later.\nYou are running version %s of wxPython.\nYou should upgrade your version of wxPython.\nNewer versions of wxPython are available at\nwww.wxpython.org"%(VREQ,VS), "Improper version of wxPython", wxOK|wxICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
        return
    app.frame = MainWindow(None, -1, "PyPE %s"%VERSION, (sys.argv[1:]))
    app.SetTopWindow(app.frame)
    app.frame.Show(1)
    app.MainLoop()

if __name__ == '__main__':
    main()
