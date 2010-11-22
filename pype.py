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
#--------------------------- configuration import ----------------------------
from configuration import *
#--------- The two most useful links for constructing this editor... ---------
# http://personalpages.tds.net/~edream/out2.htm
# http://www.pyframe.com/wxdocs/stc/selnpos.html

#---------------------------- Event Declarations -----------------------------
if 1:
    #if so I can collapse the declarations
    ID_NEW=108
    ID_OPEN=109
    ID_SAVE=111
    ID_SAVEAS=112
    ID_SAVEALL=114
    ID_CLOSE=113
    ID_EXIT=110
    
    edit_nums = range(120, 131)
    [UD, RD, SA, CU, CO, PA, IR, DR, FI, RE, IC] = edit_nums
    
    style_nums = range(115, 120)
    [PY_S, HT_S, CC_S, XM_S, TX_S] = style_nums
    lkp = dict(zip(style_nums, ['python', 'html', 'cpp', 'xml', 'text']))
    ZI = 137
    ZO = 138
    
    tab_nums = range(131, 135)
    [PT, NT, MTL, MTR] = tab_nums
    
    help_nums = range(135, 137)
    [ABOUT, HELP] = help_nums
    
    #for some default font styles
    
    cn = 'Courier New'
    if wxPlatform == '__WXMSW__':
        faces = { 'times': cn, 'mono' : cn, 'helv' : cn, 'other': cn, 'size' : 10, 'size2': 9}
    else:
        faces = { 'times': 'Courier', 'mono' : 'Courier', 'helv' : 'Courier', 'other': 'Courier', 'size' : 10, 'size2': 10 }
    
#----------------------- Useful Function Declarations ------------------------
    def getbits(num, siz=8):
        cur = []
        while num:
            cur.append(num%2)
            num /= 2
        cur = cur + (8-len(cur))*[0]
        return cur
        
    def detectFileFormat(text):
        crlf_ = text.count('\r\n')
        lf_ = text.count('\n')
        cr_ = text.count('\r')
        mx = max(crlf_, lf_, cr_)
        if not mx:
            return eol
        elif crlf_ is mx:
            return '\r\n'
        elif lf_ is mx:
            return '\n'
        else:# cr_ is mx:
            return '\r'

#-------- Very Useful dictionary definition for the keypress stuff... --------
#---------- That is, it's an O(1) operation to find out if the key -----------
#---------------------- pressed makes the file 'dirty' -----------------------
    a = [316,319,318,317,366,313,312,314,315,324,310,367,306,308,311,309,27]+\
        range(342, 352) #to deal with the f1, f2, ...f10 keys
    notdirty = dict(zip(a,len(a)*[0]))
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
        wxFrame.__init__(self,parent,-4, title, size = ( 800, 600 ),
                         style=wxDEFAULT_FRAME_STYLE|wxNO_FULL_REPAINT_ON_RESIZE)
        self.control = MyNB(self, -1)
        self.CreateStatusBar() # A Statusbar in the bottom of the window
        # Setting up the menu.
        #filemenu.Append(ID_ABOUT, "&About"," Information about this program")

#--------------------------------- File Menu ---------------------------------
        filemenu= wxMenu()
        filemenu.Append(ID_NEW,  "&New     CTRL-N",  " New file")
        filemenu.Append(ID_OPEN, "&Open   CTRL-O"," Open a file")
        filemenu.Append(ID_SAVE, "&Save    CTRL-S"," Save a file")
        filemenu.Append(ID_SAVEAS, "Save &As"," Save a file as...")
        filemenu.Append(ID_SAVEALL, "Sa&ve All", "Save all open files...")
        filemenu.AppendSeparator()
        filemenu.Append(ID_CLOSE,"&Close   CTRL-W"," Close the file in this tab")
        filemenu.AppendSeparator()
        filemenu.Append(ID_EXIT, "E&xit      ALT-F4"," Terminate the program")
        EVT_MENU(self, ID_NEW, self.OnNew)
        EVT_MENU(self, ID_OPEN, self.OnOpen)
        EVT_MENU(self, ID_SAVE, self.OnSave)
        EVT_MENU(self, ID_SAVEAS, self.OnSaveAs)
        EVT_MENU(self, ID_SAVEALL, self.OnSaveAll)
        EVT_MENU(self, ID_CLOSE, self.OnClose)
        EVT_MENU(self, ID_EXIT, self.OnExit)
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
        for i in [UD, RD, 0, SA, CU, CO, PA, 0, IR, DR, 0, FI, RE, 0, 0, IC]:
            if i:
                editmenu.Append(i, name[i-UD], help[i-UD])
                EVT_MENU(self, i, functs[i-UD])
            else:
                editmenu.AppendSeparator()

        EVT_COMMAND_FIND(self, -1, self.OnFind)
        EVT_COMMAND_FIND_NEXT(self, -1, self.OnFind)
        EVT_COMMAND_FIND_REPLACE(self, -1, self.OnFind)
        EVT_COMMAND_FIND_REPLACE_ALL(self, -1, self.OnFind)
        EVT_COMMAND_FIND_CLOSE(self, -1, self.OnFindClose)

#-------------------------------- Format Menu --------------------------------
        stylemenu= wxMenu()
        stylemenu.Append(PY_S, "Python", "Highlight for Python syntax")
        stylemenu.Append(HT_S, "HTML", "Highlight for HTML syntax")
        stylemenu.Append(XM_S, "XML", "Highlight for XML syntax")
        stylemenu.Append(CC_S, "C/C++", "Highlight for C/C++ syntax")
        stylemenu.Append(TX_S, "Text", "No Syntax Highlighting")
        stylemenu.AppendSeparator()
        stylemenu.Append(ZI, "Zoom In     CTRL-<plus>", "Make everything bigger")
        stylemenu.Append(ZO, "Zoom Out   CTRL-<minus>", "Make everything smaller")
        EVT_MENU(self, PY_S, self.OnStyleChange)
        EVT_MENU(self, HT_S, self.OnStyleChange)
        EVT_MENU(self, XM_S, self.OnStyleChange)
        EVT_MENU(self, CC_S, self.OnStyleChange)
        EVT_MENU(self, TX_S, self.OnStyleChange)
        EVT_MENU(self, ZI, self.OnZoom)
        EVT_MENU(self, ZO, self.OnZoom)

#zoom in ctrl-<plus>
#zoom out ctrl-<minus>

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
        for i in [PT, NT, 0, MTL, MTR]:
            if i:
                tabmenu.Append(i, name[i-PT], help[i-PT])
                EVT_MENU(self, i, functs[i-PT])
            else:
                tabmenu.AppendSeparator()        

#--------------------------------- Help Menu ---------------------------------
        helpmenu= wxMenu()
        name = ["About...",
                "Help    F1"]
        help = ["About this piece of software",
                "View the help"]
        functs = [self.OnAbout,
                  self.OnHelp]
        for i in [ABOUT, 0, HELP]:
            if i:
                helpmenu.Append(i, name[i-ABOUT], help[i-ABOUT])
                EVT_MENU(self, i, functs[i-ABOUT])
            else:
                helpmenu.AppendSeparator()

#------------------------- Insert menus into Menubar -------------------------
        menuBar = wxMenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        menuBar.Append(editmenu, "&Edit")
        menuBar.Append(stylemenu,"F&ormat")
        menuBar.Append(tabmenu, "Document &Tabs")
        menuBar.Append(helpmenu, "&Help")
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.


#-------------------------- Couple state variables ---------------------------
        self.Show(true)
        self.dirname = '.'
        self.closing = 0
        self.openfiles = {}

    def dialog(self, message, title):
        d= wxMessageDialog(self,message,title,wxOK)
        d.ShowModal()
        d.Destroy()

#--------------------- Find and replace dialogs and code ---------------------
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
        dlg.Show(True)


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
        dlg.Show(True)


    def OnFind(self, evt):
        wnum = self.control.GetSelection()
        if wnum < 0:
            return evt.Skip()
        win = self.control.GetPage(wnum)

        et = evt.GetEventType()
        try:
            evtType = map[et]
        except KeyError:
            evtType = "**Unknown Event Type**"
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
        if win.last == -1:
            self.dialog("Reached the end of the document.", "")

    def OnFindClose(self, evt):
        #self.log.write("wxFindReplaceDialog closing...\n")
        evt.GetDialog().Destroy()
        wnum = self.control.GetSelection()
        if wnum < 0:
            return evt.Skip()
        win = self.control.GetPage(wnum)
        if win.last == -1:
            win.SetSelection(win.gcp, win.gcp)
            win.ScrollToColumn(0)
        

#---------------------------- File Menu Commands -----------------------------
    def isOpen(self, fn, dn):
        return dn and fn and (self.getAbsolute(fn, dn) in self.openfiles)

    def makeOpen(self, fn, dn):
        if fn and dn:
            self.openfiles[self.getAbsolute(fn, dn)] = (dn,fn)

    def closeOpen(self, fn, dn):
        if fn and dn:
            del self.openfiles[self.getAbsolute(fn, dn)]

    def getAbsolute(self, fn, dn):
        return os.path.normcase(os.path.normpath(os.path.join(dn, fn)))

    def OnNew(self,e):
        self.newTab('', ' ', 1)
        self.control.GetPage(self.control.GetSelection()).opened = 1

    def OnSave(self,e):
        wnum = self.control.GetSelection()
        try:
            win = self.control.GetPage(wnum)
        except:
            return e.Skip()
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
                raise "cancelled"
        else:
            self.OnSaveAs(e)

    def OnSaveAs(self,e):
        wnum = self.control.GetSelection()
        try:
            win = self.control.GetPage(wnum)
        except:
            return e.Skip()
        
        dlg = wxFileDialog(self, "Save file as...", os.getcwd(), "", wildcard, wxOPEN)
        rslt = dlg.ShowModal()
        if rslt == wxID_OK:
            fn=dlg.GetFilename()
            dn=dlg.GetDirectory()
            if self.isOpen(fn, dn):
                self.dialog("Another file with that name and path is already open.\nSave aborted to prevent data corruption.", "Save Aborted!")
                raise "cancelled"
            if self.isOpen(win.filename, win.dirname):
                self.closeOpen(win.filename, win.dirname)
            win.filename = fn
            win.dirname = dn
            self.makeOpen(fn, dn)
            self.OnSave(e)
            win.MakeClean()
        else:
            raise "cancelled"

    def OnSaveAll(self, e):
        sel = self.control.GetSelection()
        cnt = self.control.GetPageCount()
        for i in range(cnt):
            self.control.SetSelection(i)
            try:
                self.OnSave(e)
            except 'cancelled':
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
                if self.isOpen(fn, dn):
                    (old_dir, old_file) = self.openfiles[rfn]
                    for i in xrange(self.control.GetPageCount()):
                        b = self.control.GetPage(i)
                        if (b.dirname == old_dir) and (b.filename == old_file):
                            self.control.SetSelection(i)
                            break
                else:
                    self.openfiles[rfn] = (dn, fn)
                    self.newTab(dn,fn, len(filenames)==1)
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
            nwin.format = detectFileFormat(txt)
            nwin.SetText(txt)
        else:
            nwin.format = eol
            nwin.SetText('')
        print repr(nwin.format)
        self.control.AddPage(nwin, nwin.filename, switch)
        
    def OnClose(self, e):
        wnum = self.control.GetSelection()
        #print wnum
        if wnum > -1:
            win = self.control.GetPage(wnum)
            if win.dirty:
                dlg = wxMessageDialog(self, "%s was modified after last save.\nSave changes before closing?"%win.filename, 'Save changes?', wxYES_NO|wxCANCEL)
                a = dlg.ShowModal()
                if a == wxID_CANCEL:
                    raise 'cancelled'
                elif a == wxID_NO:
                    pass
                else:
                    self.OnSave(e)
            if self.isOpen(win.filename, win.dirname):
                self.closeOpen(win.filename, win.dirname)
            self.control.DeletePage(wnum)
                    
    def OnExit(self,e):
        if self.closing:
            return e.Skip()
        self.closing = 1
        while self.control.GetPageCount():
            try:
                self.OnClose(e)
            except 'cancelled':
                self.closing = 0
                try:    return e.Veto()
                except: return e.Skip()
        self.Close(true)

#---------------------------- Edit Menu Commands -----------------------------
    def OneCmd(self, funct_name):
        wnum = self.control.GetSelection()
        try:
            win = self.control.GetPage(wnum)
        except:
            return
        getattr(win, funct_name)()

    def OnUndo(self, e):
        self.OneCmd('Undo')
    def OnRedo(self, e):
        self.OneCmd('Redo')
    def OnSelectAll(self, e):
        self.OneCmd('SelectAll')
    def OnCut(self, e):
        self.OneCmd('Cut')
    def OnCopy(self, e):
        self.OneCmd('Copy')
    def OnPaste(self, e):
        self.OneCmd('Paste')
    def Dent(self, win, incr):
        win.MakeDirty()
        x,y = win.GetSelection()
        if x==y:
            lnstart = win.GetCurrentLine()
            lnend = lnstart
        else:
            lnstart = win.LineFromPosition(x)
            lnend = win.LineFromPosition(y-1)
        for ln in xrange(lnstart, lnend+1):
            count = win.GetLineIndentation(ln)
            #print "indenting line", ln, count
            win.SetLineIndentation(ln, max(count+incr,0))
    def OnIndent(self, e):
        wnum = self.control.GetSelection()
        if wnum >= 0:
            win = self.control.GetPage(wnum)
            self.Dent(win, indent)
        else:
            event.Skip()
    def OnDedent(self, e):
        wnum = self.control.GetSelection()
        if wnum >= 0:
            win = self.control.GetPage(wnum)
            self.Dent(win, -indent)
        else:
            event.Skip()
    def OnInsertComment(self, e):
        wnum = self.control.GetSelection()
        if wnum >= 0:
            win = self.control.GetPage(wnum)
        else:
            return event.Skip()
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
                win.InsertText(win.GetLineEndPosition(lin-1)+1, st)
            else:
                win.InsertText(0, st)
            win.MakeDirty()
        else:
            event.Skip()
#------------------ Format Menu Commands and Style Support -------------------
    def OnStyleChange(self,e):
        wnum = self.control.GetSelection()
        try:
            win = self.control.GetPage(wnum)
        except:
            return e.Skip()
        nwin = PythonSTC(self.control, -1)
        nwin.format = win.format
        #print dir(nwin)
        nwin.changeStyle(stylefile, lkp[e.GetId()])
        nwin.SetText(win.GetText()[:])
        nwin.filename, nwin.dirname = win.filename, win.dirname
        nwin.GotoPos(win.GetCurrentPos())
        nwin.dirty = win.dirty
        self.control.InsertPage(wnum, nwin, self.control.GetPageText(wnum))
        self.control.SetPageText(wnum, win.dirty*'* '+win.filename)
        self.control.DeletePage(wnum+1)
        self.control.SetSelection(wnum)
    def style(self, fn):
        ext = fn.split('.')[-1].lower()
        return extns.get(ext, 'python')
    def OnZoom(self, e):
        wnum = self.control.GetSelection()
        try:   win = self.control.GetPage(wnum)
        except:return e.Skip()
        if e.GetId() == ZI:incr = 1
        else:              incr = -1
        win.SetZoom(win.GetZoom()+incr)
        
#----------------------------- Tab Menu Commands -----------------------------
    def next(self, incr):
        pagecount = self.control.GetPageCount()
        wnum = self.control.GetSelection()
        if wnum >= 0:
            wnum = (wnum+incr)%pagecount
            self.control.SetSelection(wnum)
        else:
            event.Skip()
    def OnLeft(self, e):
        self.next(-1)
    def OnRight(self, e):
        self.next(1)
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
            event.Skip()
#---------------------------- Help Menu Commands -----------------------------
    def OnAbout(self, e):
        txt = """
        You're wondering what this editor is all about, right?  Easy, this edior was
        written to scratch an itch.  I (Josiah Carlson), was looking for an editor
        that had the features I wanted, I couldn't find one.  So I wrote one.  And
        here it is.
        
        PyPE 1.0 (Python Programmer's Editor')
        http://come.to/josiah
        PyPE is copyright 2003 Josiah Carlson.
        
        This software is licensed under the GPL (GNU General Public License) as it
        appears here: http://www.gnu.org/copyleft/gpl.html  It is also included with
        this software as gpl.txt.
        
        If you do not also receive a copy of gpl.txt with your version of this
        software, please inform the me of the violation at the web page near the top
        of this document."""
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
        print "keypressed", event.KeyCode()
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

            #find string with ctrl-f
            if (key == 70) and (pagecount>=1):
                self.OnShowFind(event)
            #find and replace string with ctrl-r
            elif (key == 82) and (pagecount >=1):
                self.OnShowFindReplace(event)

            #shifts current line down one, inserting a line-long comment
            elif (key == 73) and (pagecount >=1):
                    self.OnInsertComment(event)
            #makes document dirty on paste with ctrl-v
            elif (key == 86) and (pagecount >=1):
                win.MakeDirty()
                event.Skip()
            #makes document dirty on cut with ctrl-x
            elif (key == 88) and (pagecount >=1):
                win.MakeDirty()
                event.Skip()

            #create a new document with ctrl-n
            elif (key == 78):
                self.OnNew(event)
            #open an old document with ctrl-o
            elif key == 79:
                self.OnOpen(event)
            #close the currently open document with ctrl-q
            elif key == 87:
                try:
                    self.OnClose(event)
                except "cancelled":
                    event.Skip()
            #save the currently open document with ctrl-s
            elif key == 83:
                self.OnSave(event)

            #go to the tab to the left with ctrl-, (same key as <)
            elif key == 44:
                self.next(-1)
            #go to the tab to the right with ctrl-. (same key as >)
            elif key == 46:
                self.next(1)

            #indent the current line or selection of lines (indent) spaces with ctrl-]
            elif key == 93:
                self.OnIndent(event)
            #dedent the current line or selection of lines (indent) spaces with ctrl-[
            elif key == 91:
                self.OnDedent(event)
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
            if key==13:
                if wnum >= 0:
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
                    print repr(win.format), repr(chrs)
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
    def MakeDirty(self):
        if (not self.dirty) and self.opened:
            self.dirty = 1
            self.parent.SetPageText(self.parent.GetSelection(), '* '+self.filename)
            self.parent.Refresh(False)
            #self.parent.Refresh(True)
            self.Refresh(False)
            #self.Refresh(True)
            
    def MakeClean(self):
        self.dirty = 0
        self.parent.SetPageText(self.parent.GetSelection(), self.filename)
        self.parent.Refresh(False)
        #self.parent.Refresh(True)
        self.Refresh(False)
        #self.Refresh(True)

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
            if evt.GetShift() and evt.GetControl():
                self.FoldAll()
            else:
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
    app.frame = MainWindow(None, -1, "PyPE 1.0.1")
    app.frame.Show(1)
    app.MainLoop()

if __name__ == '__main__':
    main()
