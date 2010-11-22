#!/usr/bin/env python

#-------------- User changable settings are in configuration.py --------------

#------------------------------ System Imports -------------------------------
from __future__ import generators

import sys
if not hasattr(sys, 'frozen'):
    import wxversion;wxversion.ensureMinimal('2.6')
import os, stat
import keyword, traceback, cStringIO, imp, fnmatch, re
import time, pprint
from wxPython.wx import *
from wxPython.stc import *
from wxPython.lib.rcsizer import RowColSizer
from wxPython.lib.dialogs import wxScrolledMessageDialog
import wx.lib.mixins.listctrl as listctrl
wxListCtrlAutoWidthMixin, wxColumnSorterMixin, wxTextEditMixin = \
  listctrl.ListCtrlAutoWidthMixin, listctrl.ColumnSorterMixin, listctrl.TextEditMixin
import copy
import inspect
import textwrap
import md5
import compiler
USE_THREAD = 1
if USE_THREAD:
    import Queue
    import threading


UNICODE = wxUSE_UNICODE

#--------------------------- configuration import ----------------------------
from configuration import *

#---------------------------- Event Declarations -----------------------------

class cancelled(Exception):
        pass

def isdirty(win):
    if win.dirty:
        return True

    fn = win.root.getAbsolute(win.filename, win.dirname)
    dirty = 0
    try:
        mod = os.stat(fn)[8]
        dirty += mod != win.mod
    except:
        dirty += bool(fn.strip())
    r = dirty and True or False
    if r:
        win.MakeDirty()
    return r

#plugin-type thing imports
from plugins import logger
from plugins import findbar
from plugins import lru
from plugins import filehistory
from plugins import browser
from plugins import workspace
from plugins import todo
from plugins import findinfiles
from plugins import shell
from plugins import textrepr
from plugins import single_instance
from plugins import interpreter
from plugins import spellcheck

## from plugins import project

for i in [logger, findbar, lru, filehistory, browser, workspace, todo,
          findinfiles, shell, textrepr, spellcheck]:#, project]:
    i.cancelled = cancelled
    i.isdirty = isdirty

#
VERSION_ = VERSION = "2.3"

#some definitions
if 1:

    try:
        True
    except:
        True = bool(1)
        False = not True

    import string
    STRINGPRINTABLE = dict.fromkeys(map(ord, string.printable))
    
    IDR = wxNewId()
    DDR = wxNewId()

#keypresses
if 1:
    keys = ["BACK", "TAB", "RETURN", "ESCAPE", "SPACE", "DELETE", "START",
    "LBUTTON", "RBUTTON", "CANCEL", "MBUTTON", "CLEAR", "PAUSE",
    "CAPITAL", "PRIOR", "NEXT", "END", "HOME", "LEFT", "UP", "RIGHT",
    "DOWN", "SELECT", "PRINT", "EXECUTE", "SNAPSHOT", "INSERT", "HELP",
    "NUMPAD0", "NUMPAD1", "NUMPAD2", "NUMPAD3", "NUMPAD4", "NUMPAD5",
    "NUMPAD6", "NUMPAD7", "NUMPAD8", "NUMPAD9", "MULTIPLY", "ADD",
    "SEPARATOR", "SUBTRACT", "DECIMAL", "DIVIDE", "F1", "F2", "F3", "F4",
    "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12", "F13", "F14",
    "F15", "F16", "F17", "F18", "F19", "F20", "F21", "F22", "F23", "F24",
    "NUMLOCK", "SCROLL", "PAGEUP", "PAGEDOWN", "NUMPAD_SPACE",
    "NUMPAD_TAB", "NUMPAD_ENTER", "NUMPAD_F1", "NUMPAD_F2", "NUMPAD_F3",
    "NUMPAD_F4", "NUMPAD_HOME", "NUMPAD_LEFT", "NUMPAD_UP",
    "NUMPAD_RIGHT", "NUMPAD_DOWN", "NUMPAD_PRIOR", "NUMPAD_PAGEUP",
    "NUMPAD_NEXT", "NUMPAD_PAGEDOWN", "NUMPAD_END", "NUMPAD_BEGIN",
    "NUMPAD_INSERT", "NUMPAD_DELETE", "NUMPAD_EQUAL", "NUMPAD_MULTIPLY",
    "NUMPAD_ADD", "NUMPAD_SEPARATOR", "NUMPAD_SUBTRACT", "NUMPAD_DECIMAL",
    "NUMPAD_DIVIDE"]

    keyMap = {}
    #RkeyMap = {}
    for i in keys:
        key = eval("WXK_"+i)
        keyMap[key] = i
        #RkeyMap[i] = key
    for i in ["SHIFT", "ALT", "CONTROL", "MENU"]:
        key = eval("WXK_"+i)
        keyMap[key] = ''
    del key

    def GetKeyPress(evt):
        keycode = evt.GetKeyCode()
        keyname = keyMap.get(keycode, None)
        modifiers = ""
        for mod, ch in ((evt.ControlDown(), 'Ctrl+'),
                        (evt.AltDown(),     'Alt+'),
                        (evt.ShiftDown(),   'Shift+'),
                        (evt.MetaDown(),    'Meta+')):
            if mod:
                modifiers += ch

        if keyname is None:
            if 27 < keycode < 256:
                keyname = chr(keycode)
            else:
                keyname = "(%s)unknown" % keycode
        return modifiers + keyname

#menu preferences
if 1:
    MENULIST = []
    MENUPREF = {}
    OLD_MENUPREF= {}
    HOTKEY_TO_ID = {}

    def _spl(n):
        return (n.split('\t', 1) + [''])[:2]

    def recmenu(menu, id):
        #this was a pain in the ass.
        if isinstance(menu, wxMenuItem) or isinstance(menu, wxMenuItemPtr):
            sm = menu.GetSubMenu()
            if sm:
                a = recmenu(sm, id)
                if a:
                    return '%s->%s'%(menu.GetLabel(), a)
                return ''
            elif menu.GetId() == id:
                return menu.GetLabel()
            else:
                return ''
        elif isinstance(menu, wxMenu) or isinstance(menu, wxMenuPtr):
            ITEMS = menu.GetMenuItems()
            for i in ITEMS:
                a = recmenu(i, id)
                if a:
                    return a
            return ''
        else:
            for i in xrange(menu.GetMenuCount()):
                r = menu.GetMenu(i)
                if r.FindItemById(id):
                    return "%s->%s"%(menu.GetLabelTop(i), recmenu(r, id))
        raise Exception("Item not found.")

    def menuAdd(root, menu, name, desc, funct, id, kind=wxITEM_NORMAL):

        a = wxMenuItem(menu, id, 'TEMPORARYNAME', desc, kind)
        menu.AppendItem(a)
        EVT_MENU(root, id, funct)

        ns, oacc = _spl(name)
        hier = recmenu(menuBar, id)[:-13] + ns
        if hier in MENUPREF:
            name, acc = MENUPREF[hier]
        else:
            if hier in OLD_MENUPREF:
                name, acc = MENUPREF[hier] = OLD_MENUPREF[hier]
            else:
                name, acc = MENUPREF[hier] = (ns, oacc)
            MENULIST.append((hier, name, oacc, acc, kind in [wxITEM_NORMAL, wxITEM_CHECK]))

        if acc:
            HOTKEY_TO_ID[acc] = id

        menuBar.SetLabel(id, '%s\t%s'%(name, acc))
        menuBar.SetHelpString(id, desc)

    def menuAddM(parent, menu, name, help=''):
        if isinstance(parent, wxMenu) or isinstance(parent, wxMenuPtr):
            id = wxNewId()
            parent.AppendMenu(id, "TEMPORARYNAME", menu, help)
            hier = recmenu(menuBar, id) + name
            name, toss = MENUPREF.setdefault(hier, (name, ''))

            menuBar.SetLabel(id, name)
            menuBar.SetHelpString(id, help)
        else:
            hier = name
            name, toss = MENUPREF.setdefault(name, (name, ''))

            parent.Append(menu, name)

        MENULIST.append((hier, name, '', '', 0))

    def getIcon():
        data = getData()
        stream = cStringIO.StringIO(data)
        image = wxImageFromStream(stream)
        bitmap = wxBitmapFromImage(image)
        icon = wxEmptyIcon()
        icon.CopyFromBitmap(bitmap)
        return icon

    NEWDOCUMENT = 0L

#document styling events
if 1:
    #style ids
    #         _S     0   _DS    1      2            3           _DD    4   _DD2   5      6
    assoc = [(wxNewId(), wxNewId(), 'python', wxSTC_LEX_PYTHON, wxNewId(), wxNewId(), "Python"),
             (wxNewId(), wxNewId(), 'pyrex',  wxSTC_LEX_PYTHON, wxNewId(), wxNewId(), "Pyrex"),
             (wxNewId(), wxNewId(), 'html',   wxSTC_LEX_HTML,   wxNewId(), wxNewId(), "HTML"),
             (wxNewId(), wxNewId(), 'xml',    wxSTC_LEX_XML,    wxNewId(), wxNewId(), "XML"),
             (wxNewId(), wxNewId(), 'cpp',    wxSTC_LEX_CPP,    wxNewId(), wxNewId(), "C/C++"),
             (wxNewId(), wxNewId(), 'text',   wxSTC_LEX_NULL,   wxNewId(), wxNewId(), "Text"),
             (wxNewId(), wxNewId(), 'tex',    wxSTC_LEX_LATEX,  wxNewId(), wxNewId(), "TeX/LaTeX")]
    ASSOC = assoc
    
    SITO = [i[4] for i in assoc]
    SITO2 = [i[5] for i in assoc]
    ## PY_S,   PYX_S,   HT_S,   XM_S,   CC_S,   TX_S,   TEX_S   = [i[0] for i in assoc]
    ## PY_DS,  PYX_DS,  HT_DS,  XM_DS,  CC_DS,  TX_DS,  TEX_DS  = [i[1] for i in assoc]
    ## PY_DD,  PYX_DD,  HT_DD,  XM_DD,  CC_DD,  TX_DD,  TEX_DD  = SITO
    ## PY_DD2, PYX_DD2, HT_DD2, XM_DD2, CC_DD2, TX_DD2, TEX_DD2 = SITO2
    
    lexers =      dict([(i[0],i[2]) for i in assoc])
    lexers2 =     dict([(i[2],i[0]) for i in assoc])
    lexers.update(dict([(i[1],i[2]) for i in assoc]))
    lexers3 =     dict([(i[2],i[1]) for i in assoc])
    lexer2lang =  dict([(i[3],i[2]) for i in assoc])
    
    SOURCE_ID_TO_OPTIONS  = dict([(i[4], (i[2], i[6])) for i in assoc])
    SOURCE_ID_TO_OPTIONS2 = dict([(i[5], (i[2], i[6])) for i in assoc])
    del assoc

#checkbox ids
if 1:
    AUTO = wxNewId()
    NUM = wxNewId()
    MARGIN = wxNewId()
    USETABS = wxNewId()
    INDENTGUIDE = wxNewId()
    WRAPL = wxNewId()
    SAVE_CURSOR = wxNewId()
    S_WHITE = wxNewId()
    DND_ID = wxNewId()
    DB_ID = wxNewId()
    LB_ID = wxNewId()
    WIDE_ID = wxNewId()
    TALL_ID = wxNewId()
    SINGLE_ID = wxNewId()
    TD_ID = wxNewId()
    FINDBAR_BELOW_EDITOR = wxNewId()
    NO_FINDBAR_HISTORY = wxNewId()
    CLEAR_FINDBAR_HISTORY = wxNewId()

    ZI = wxNewId()

    #toolbar ids
    
    TB_MAPPING = {
        wxNewId(): (0, 'Hide', "Don't show the tool bar"),
        wxNewId(): (1, 'Top',  "Show the toolbar accross the top horizontally"),
        wxNewId(): (2, 'Left', "Show the toolbar along the left side vertically")
    }
    TB_RMAPPING = dict([(j[0], (j[0], i, j[1], j[2])) for i,j in TB_MAPPING.iteritems()])

    #line ending ids
    LE_MAPPING = {
        wxNewId():(wxSTC_EOL_CRLF, 0, "CRLF (windows)", "Change the line endings for the current document to CRLF/Windows line endings"),
        wxNewId():(wxSTC_EOL_LF,   1, "LF (*nix)",      "Change the line endings for the current document to LF/*nix line endings"),
        wxNewId():(wxSTC_EOL_CR,   2, "CR (mac)",       "Change the line endings for the current document to CR/Macintosh line endings")
    }
    LE_RMAPPING = dict([(j[0], (j[1], i, j[2], j[3])) for i,j in LE_MAPPING.iteritems()])

    #long line indicator ids
    LL_MAPPING = {
        wxNewId():(wxSTC_EDGE_BACKGROUND, 0, "Background", "Long lines will have a different background color beyond the column limit"),
        wxNewId():(wxSTC_EDGE_LINE,       1, "Line", "Long lines will have a vertical line at the column limit"),
        wxNewId():(wxSTC_EDGE_NONE,       2, "None", "Show no long line indicator")
    }
    
    LL_RMAPPING = dict([(j[0],(j[1], i, j[2], j[3])) for i,j in LL_MAPPING.iteritems()])

    #cursor behavior ids
    CARET_ID_TO_OPTIONS = {
        wxNewId()        : (0, wxSTC_CARET_EVEN|wxSTC_CARET_SLOP|wxSTC_CARET_STRICT, 1, "Margin Respecting", "Caret is at least M lines from the top and bottom, N*M pixels from the right and left"),
        wxNewId()        : (1, wxSTC_CARET_EVEN|wxSTC_CARET_STRICT, 4, "Centered", "Caret is centered on the display, if possible"),
        wxNewId()        : (2, wxSTC_CARET_STRICT, 3, "Top Attached", "Caret is always on the top line, if possible"),
        wxNewId()        : (3, wxSTC_CARET_SLOP|wxSTC_CARET_STRICT, 2, "Margin Attached", "Caret is always M lines from the top, and N*M pixels from the right, if possible"),
        wxNewId()        : (4, wxSTC_CARET_EVEN, 0, "PyPE Classic", "Caret is at least 1 line from the top and bottom, 10 pixels from the right and left"),
    }

    CARET_OPTION_TO_ID = dict([(j[0], (i, j[1])) for i,j in CARET_ID_TO_OPTIONS.iteritems()])
    
    #title display ids
    
    TITLE_ID_TO_OPTIONS = {
        wxNewId()           : (0, "%(pype)s",                       "No file information"),
        wxNewId()           : (1, "%(pype)s - %(fn)s",              "File name after title"),
        wxNewId()           : (2, "%(fn)s - %(pype)s",              "File name before title"),
        wxNewId()           : (3, "%(pype)s - %(fn)s - [%(long)s]", "File and full path after title"),
        wxNewId()           : (4, "%(fn)s - [%(long)s] - %(pype)s", "File and full path before title"),
    }
    
    TITLE_OPTION_TO_ID = dict([(j[0], (i, j[1], j[2])) for i,j in TITLE_ID_TO_OPTIONS.iteritems()])

    #bookmark support
    BOOKMARKNUMBER = 1
    BOOKMARKSYMBOL = wxSTC_MARK_CIRCLE
    BOOKMARKMASK = 2

#unicode BOM stuff
if 1:
    BOM = [('+/v8-', 'utf-7'),
          ('\xef\xbb\xbf', 'utf-8'),
          ('\xfe\xff', 'utf-16-be'),
          ('\xff\xfe\xff\xfe', 'utf-16'),
          ('\xff\xfe', 'utf-16-le'),
          ('', 'ascii'),
          ('', 'other')]
    ADDBOM = {}
    ENCODINGS = {}
    for i,j in BOM:
        ADDBOM[j] = i
        ENCODINGS[j] = wxNewId()
    del i;del j;

#font stuff
if 1:
    cn = 'Courier New'
    if wxPlatform == '__WXMSW__':
        faces = {'times': cn, 'mono' : cn, 'helv' : cn, 'other': cn,
                 'size' : 10, 'size2': 9}
    else:
        faces = {'times': 'Courier', 'mono' : 'Courier',
                 'helv' : 'Courier', 'other': 'Courier', 'size' : 10,
                 'size2': 10 }
    del cn

#SashWindow stuff
if 1:
    def makeSubWindow(parent, id, size, orientation, alignment, sash):
        win = wxSashLayoutWindow(
                parent, id, wxDefaultPosition, size,
                wxNO_BORDER|wxSW_3D
                )
        win.SetDefaultSize(size)
        win.SetOrientation(orientation)
        win.SetAlignment(alignment)
        ## win.SetBackgroundColour(wx.Colour(127, 0, 0))
        win.SetSashVisible(sash, True)
        ## win.SetMinimumSizeX(30)
        return win

    #subwindow ids
    ID_WINDOW_BOTTOM = wxNewId()
    ID_WINDOW_RIGHT = wxNewId()

    #subwindow constants
    SMALL = 10
    BIG = 10000

    DB_LOC = {0:(wxLAYOUT_LEFT, wxSASH_RIGHT),
              1:(wxLAYOUT_RIGHT, wxSASH_LEFT)}

    LB_LOC = {0:(wxLAYOUT_TOP, wxSASH_BOTTOM),
              1:(wxLAYOUT_BOTTOM, wxSASH_TOP)}

#findbar ids
if 1:

    pypeID_DELETE = wxNewId()
    pypeID_FINDBAR = wxNewId()
    pypeID_REPLACEBAR = wxNewId()
    pypeID_TOGGLE_BOOKMARK = wxNewId()
    pypeID_NEXT_BOOKMARK = wxNewId()
    pypeID_PRIOR_BOOKMARK = wxNewId()

#extension to image map
EXT_TO_IMG = {'python':1, 'pyrex':1}
#
RESET = {'cursorposn':0,
         'BM':[],
         'FOLD':[]}

#threaded parser
if USE_THREAD:
    parse_queue = Queue.Queue()
    from wx.lib.newevent import NewEvent
    
    DoneParsing, EVT_DONE_PARSING = NewEvent()
    
    def parse(lang, source, le, which, x, slowparse=0):
        if lang in ('python', 'pyrex'):
            if slowparse:
                try:
                    return fast_parser(source, le, which, x)
                except:
                    pass
            return faster_parser(source, le, which, x)
        elif lang == 'tex':
            return latex_parser(source, le, which, x)
        elif lang == 'cpp':
            return c_parser(source, le, which, x)
        else:
            return [], [], {}, []
    
    def start_parse_thread(frame):
        a = threading.Thread(target=parse_thread, args=(frame,))
        ## a.setDaemon(1)
        a.start()
    
    def parse_thread(frame):
        null = lambda:None
        while 1:
            x = parse_queue.get()
            if not x:
                break
            source, stc, lang = x
            t = time.time()
            tpl = parse(lang, source, '\n', 3, null, 1)
            t = time.time()-t
            try:
                wxPostEvent(frame, DoneParsing(stc=stc, tpl=tpl, delta=t))
            except:
                #if this raises an exception, then the main frame has closed
                break

sys_excepthook = sys.excepthook

def my_excepthook(typ, inst, trace):
    if typ is cancelled:
        return
    return sys_excepthook(typ, inst, trace)

sys.excepthook = my_excepthook

def veto(*args):
    args[-1].Veto()

#---------------------- Frame that contains everything -----------------------
class MainWindow(wxFrame):
    def __init__(self,parent,id,title,fnames):
        self.starting = 1
        wxFrame.__init__(self,parent,id, title, size = ( 1024, 600 ),
                         style=wxDEFAULT_FRAME_STYLE|wxNO_FULL_REPAINT_ON_RESIZE)

        self.SetIcon(getIcon())
        self.FINDSHOWN = 0
        path = os.path.join(homedir, 'menus.txt')
        if UNICODE:
            p = os.path.join(homedir, 'menus.u.txt')
            if os.path.exists(p):
                path = p
        try:    OLD_MENUPREF.update(self.readAndEvalFile(path))
        except: pass
        
        single_instance.callback = self.OnDrop
        
        #recent menu relocated to load configuration early on.
        recentmenu = wxMenu()
#--------------------------- cmt-001 - 08/06/2003 ----------------------------
#----------------- Adds opened file history to the File menu -----------------
        self.fileHistory = wxFileHistory()
        self.fileHistory.UseMenu(recentmenu)
        self.configPath = homedir
        self.loadHistory()
        self.SetSize(LASTSIZE)
        self.SetPosition(LASTPOSITION)
        self.restart = 0
        self.restartt = 0
        EVT_MENU_RANGE(self, wxID_FILE1, wxID_FILE9, self.OnFileHistory)
        self.lastused = lru.lastused(128+len(lastopen), LASTUSED)
        self.curdocstates = {}
#------------------------- end cmt-001 - 08/06/2003 --------------------------
        self.toparse = []
        self.parsing = 0

        try:
            typ = wxITEM_RADIO
            self.HAS_RADIO = 1
        except:
            typ = wxITEM_NORMAL
            self.HAS_RADIO = 0

        #EVT_IDLE(self, self.SetPos)
        #a = wxNewId()
        #self.T = wxTimer(self, a)
        #EVT_TIMER(self, a, self.SetPos)
        #self.T.Start(100)

        self.sb = wxStatusBar(self, -1)
        if UNICODE:
            #to display encoding in unicode supporting platforms
            self.sb.SetFieldsCount(3)
            self.sb.SetStatusWidths([-1, 95, 60])
        else:
            self.sb.SetFieldsCount(2)
            self.sb.SetStatusWidths([-1, 95])
        self.SetStatusBar(self.sb)
        
        if TOOLBAR:
            self._setupToolBar()

        self.control = MyNB(self, -1, self)

        # Setting up the menu


        bottom = makeSubWindow(self, ID_WINDOW_BOTTOM, (BIG, SASH1),
                               wxLAYOUT_HORIZONTAL,
                               *LB_LOC[logbarlocn])

        right = makeSubWindow(self, ID_WINDOW_RIGHT, (SASH2, BIG),
                              wxLAYOUT_VERTICAL,
                              *DB_LOC[docbarlocn])

        self.BOTTOM = bottom
        self.RIGHT = right

        self.BOTTOMNB = wxNotebook(bottom, -1)
        self.RIGHTNB = wxNotebook(right, -1)
        
        if TODOBOTTOM:
            self.todolist = todo.VirtualTodo(self.BOTTOMNB, self)
            self.BOTTOMNB.AddPage(self.todolist, 'Todo')
        
        
        self.BOTTOMNB.AddPage(logger.logger(self.BOTTOMNB), 'Log')
        ## self.BOTTOMNB.AddPage(findinfiles.FindInFiles(self.BOTTOMNB, self), "Find in Files")
        self.BOTTOMNB.AddPage(findinfiles.FindInFiles(self.BOTTOMNB, self), "Search")
        self.BOTTOMNB.AddPage(spellcheck.SpellCheck(self.BOTTOMNB, self), "Spell Check")
        ## self.shell = shell.Shell(self.BOTTOMNB, self, self.config.get('shellprefs', {}))
        ## self.BOTTOMNB.AddPage(self.shell, "Shell")
        if UNICODE:
            self.BOTTOMNB.AddPage(textrepr.TextRepr(self.BOTTOMNB, self), "repr(text)")

        self.leftt = wxPanel(self.RIGHTNB)#HiddenPanel(self.RIGHTNB, self, 0)#hierCodeTreePanel(self, self.RIGHTNB)
        self.leftt.sizer = wxBoxSizer(wxVERTICAL)
        self.leftt.SetSizer(self.leftt.sizer)
        self.leftt.SetAutoLayout(True)

        self.rightt = wxPanel(self.RIGHTNB)#HiddenPanel(self.RIGHTNB, self, 1)#hierCodeTreePanel(self, self.RIGHTNB)
        self.rightt.sizer = wxBoxSizer(wxVERTICAL)
        self.rightt.SetSizer(self.rightt.sizer)
        self.rightt.SetAutoLayout(True)

        self.dragger = MyLC(self.RIGHTNB, self)

        ## self.RIGHTNB.AddPage(project.Project(self.RIGHTNB, -1, self), 'Project')
        self.RIGHTNB.AddPage(self.rightt, 'Name')
        self.RIGHTNB.AddPage(self.leftt, 'Line')
        if not TODOBOTTOM:
            self.todolist = todo.VirtualTodo(self.RIGHTNB, self)
            self.RIGHTNB.AddPage(self.todolist, 'Todo')
        self.RIGHTNB.AddPage(self.dragger, 'Documents')
        self.pathmarks = browser.FilesystemBrowser(self.RIGHTNB, self, pathmarksn)
        self.RIGHTNB.AddPage(self.pathmarks, "Browse...")

        self.Bind(EVT_SASH_DRAGGED_RANGE, self.OnSashDrag, id=ID_WINDOW_BOTTOM, id2=ID_WINDOW_RIGHT)

#------------------------- Insert menus into Menubar -------------------------
        global menuBar
        menuBar = wxMenuBar()

        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
        self.menubar = menuBar

#--------------------------------- File Menu ---------------------------------

        filemenu= wxMenu()
        menuAddM(menuBar, filemenu, "&File")
        menuAdd(self, filemenu, "&New\tCtrl+N",         "New file", self.OnNew, wxID_NEW)
        menuAdd(self, filemenu, "&Open\tCtrl+O",        "Open a file", self.OnOpen, wxID_OPEN)
        menuAdd(self, filemenu, "Open &Module\tAlt+M",  "Open a module for editing using the same path search as import would", self.OnOpenModule, wxNewId())
        menuAdd(self, filemenu, "Open &Last\t",         "Open all the documents that were opening before last program exit", self.OnOpenPrevDocs, wxNewId())
        menuAddM(filemenu, recentmenu, "Open Recent")
        filemenu.AppendSeparator()
        menuAdd(self, filemenu, "&Save\tCtrl+S",        "Save a file", self.OnSave, wxID_SAVE)
        menuAdd(self, filemenu, "Save &As",             "Save a file as...", self.OnSaveAs, wxID_SAVEAS)
        menuAdd(self, filemenu, "Sa&ve All",            "Save all open files...", self.OnSaveAll, wxNewId())
        filemenu.AppendSeparator()
        menuAdd(self, filemenu, "New Python Shell",     "Opens a Python shell in a new tab", self.OnNewPythonShell, wxNewId())
        menuAdd(self, filemenu, "New Command Shell",    "Opens a command line shell in a new tab", self.OnNewCommandShell, wxNewId())
        filemenu.AppendSeparator()
        menuAdd(self, filemenu, "Add Module Search Path", "Add a path to search during subsequent 'Open Module' executions", self.AddSearchPath, wxNewId())
        menuAdd(self, filemenu, "&Reload",              "Reload the current document from disk", self.OnReload, wxID_REVERT)
        menuAdd(self, filemenu, "&Close\tCtrl+W",        "Close the file in this tab", self.OnClose, wxNewId())
        workspace.WorkspaceMenu(filemenu, self, workspaces, workspace_order)
        menuAdd(self, filemenu, "E&xit\tAlt+F4",        "Terminate the program", self.OnExit, wxNewId())

#--------------------------------- Edit Menu ---------------------------------

        editmenu= wxMenu()
        menuAddM(menuBar, editmenu, "&Edit")
        menuAdd(self, editmenu, "Undo\tCtrl+Z",         "Undo last modifications", self.OnUndo, wxID_UNDO)
        menuAdd(self, editmenu, "Redo\tCtrl+Y",         "Redo last modifications", self.OnRedo, wxID_REDO)
        editmenu.AppendSeparator()
        menuAdd(self, editmenu, "Select All\tCtrl+A",   "Select all text", self.OnSelectAll, wxNewId())
        menuAdd(self, editmenu, "Cut\tCtrl+X",          "Cut selected text", self.OnCut, wxID_CUT)
        menuAdd(self, editmenu, "Copy\tCtrl+C",         "Copy selected text", self.OnCopy, wxID_COPY)
        menuAdd(self, editmenu, "Paste\tCtrl+V",        "Paste selected text", self.OnPaste, wxID_PASTE)
        menuAdd(self, editmenu, "Delete",               "Delete selected text", self.OnDeleteSelection, pypeID_DELETE)
        editmenu.AppendSeparator()
        menuAdd(self, editmenu, "Show Find Bar\tCtrl+F", "Shows the find bar at the bottom of the editor", self.OnShowFindbar, pypeID_FINDBAR)
        menuAdd(self, editmenu, "Show Replace Bar\tCtrl+R", "Shows the replace bar at the bottom of the editor", self.OnShowReplacebar, pypeID_REPLACEBAR)
        menuAdd(self, editmenu, "Find again\tF3",        "Finds the text in the find bar again", self.OnFindAgain, wxNewId())
        ## editmenu.AppendSeparator()
        ## if self.config['usesnippets']:
            ## menuAdd(self, editmenu, "Insert Snippet\tCtrl+return", "Insert the currently selected snippet into the document", self.snippet.OnListBoxDClick, wxNewId())
        
#------------------------------ Transform Menu -------------------------------
        transformmenu= wxMenu()
        menuAddM(menuBar, transformmenu, "&Transforms")

        menuAdd(self, transformmenu, "Indent Region\tCtrl+]", "Indent region", self.OnIndent, IDR)
        menuAdd(self, transformmenu, "Dedent Region\tCtrl+[", "Dedent region", self.OnDedent, DDR)
        menuAdd(self, transformmenu, "Wrap Selected Text\tAlt+W", "Wrap selected text to a specified width", self.OnWrap, wxNewId())
        transformmenu.AppendSeparator()
        menuAdd(self, transformmenu, "Insert Comment\tCtrl+I", "Insert a centered comment", self.OnInsertComment, wxNewId())
        menuAdd(self, transformmenu, "Comment Selection\tAlt+8", "Comment selected lines", self.OnCommentSelection, wxNewId())
        menuAdd(self, transformmenu, "Uncomment Selection\tAlt+9", "Uncomment selected lines", self.OnUncommentSelection, wxNewId())
        transformmenu.AppendSeparator()
        menuAdd(self, transformmenu, "Wrap try/except", "Wrap the selected code in a try/except clause", self.WrapExcept, wxNewId())
        menuAdd(self, transformmenu, "Wrap try/finally", "Wrap the selected code in a try/finally clause", self.WrapFinally, wxNewId())
        menuAdd(self, transformmenu, "Wrap try/except/finally", "Wrap the selected code in a try/except/finally clause", self.WrapExceptFinally, wxNewId())
        transformmenu.AppendSeparator()
        menuAdd(self, transformmenu, "Perform Trigger", "Performs a trigger epansion if possible", self.OnTriggerExpansion, wxNewId())        

#--------------------------------- View Menu ---------------------------------

        viewmenu= wxMenu()
        menuAddM(menuBar, viewmenu,"&View")
        menuAdd(self, viewmenu, "Previous Tab\tAlt+,", "View the tab to the left of the one you are currently", self.OnLeft, wxNewId())
        menuAdd(self, viewmenu, "Next Tab\tAlt+.", "View the tab to the right of the one you are currently", self.OnRight, wxNewId())
        viewmenu.AppendSeparator()
        menuAdd(self, viewmenu, "Zoom In\tCtrl++", "Make the text in the editing component bigger", self.OnZoom, ZI)
        menuAdd(self, viewmenu, "Zoom Out\tCtrl+-", "Make the text in the editing component smaller", self.OnZoom, wxNewId())
        viewmenu.AppendSeparator()
        menuAdd(self, viewmenu, "Go to line number\tAlt+G", "Advance to the given line in the currently open document", self.OnGoto, wxNewId())
        menuAdd(self, viewmenu, "Go to position", "Advance to the given position in the currently open document", self.OnGotoP, wxNewId())
        menuAdd(self, viewmenu, "Jump forward", "Advance the cursor to the next quote/bracket", self.OnJumpF, wxNewId())
        menuAdd(self, viewmenu, "Jump backward", "Advance the cursor to the previous quote/bracket", self.OnJumpB, wxNewId())
        viewmenu.AppendSeparator()
        menuAdd(self, viewmenu, "Toggle Bookmark\tCtrl+M", "Create/remove bookmark for this line", self.OnToggleBookmark, pypeID_TOGGLE_BOOKMARK)
        menuAdd(self, viewmenu, "Next Bookmark\tF2", "Hop to the next bookmark in this file", self.OnNextBookmark, pypeID_NEXT_BOOKMARK)
        menuAdd(self, viewmenu, "Previous Bookmark\tShift+F2", "Hop to the previous bookmark in this file", self.OnPreviousBookmark, pypeID_PRIOR_BOOKMARK)

#------------------------------- Document menu -------------------------------

        setmenu= wxMenu()
        menuAddM(menuBar, setmenu, "&Document")
        ## menuAdd(self, setmenu, "Use Snippets (req restart)", "Enable or disable the use of snippets, requires restart for change to take effect", self.OnSnipToggle, SNIPT, wxITEM_CHECK)
        ## setmenu.AppendSeparator()

        #-------------------------------- Style subenu -----------------------
        stylemenu= wxMenu()
        menuAddM(setmenu, stylemenu, "Syntax Highlighting", "Change the syntax highlighting for the currently open document")
        for i in ASSOC:
            name, mid = i[6], i[0]
            st = "Highlight for %s syntax"%name
            if name == 'Text':
                st = "No Syntax Highlighting"
            menuAdd(self, stylemenu, name, st, self.OnStyleChange, mid, typ)

        #------------------------------ Encodings submenu --------------------
        if UNICODE:
            encmenu= wxMenu()
            menuAddM(setmenu, encmenu, "Encodings", "Change text encoding")
            menuAdd(self, encmenu, 'ascii', "Change encoding for the current file to ascii (will use utf-8 if unicode characters found)", self.OnEncChange, ENCODINGS['ascii'], typ)
            menuAdd(self, encmenu, 'other', "Will use the encoding specified in your encoding declaration, reverting to ascii if not found, and utf-8 as necessary", self.OnEncChange, ENCODINGS['other'], typ)
            for bom, enc in BOM[:-2]:
                menuAdd(self, encmenu, enc, "Change encoding for the current file to %s"%enc, self.OnEncChange, ENCODINGS[enc], typ)

        #----------------------------- Line ending menu ----------------------
        endingmenu = wxMenu()
        menuAddM(setmenu, endingmenu, "Line Ending", "Change the line endings on the current document")
        
        x = LE_RMAPPING.values()
        x.sort()
        for _, idn, name, help in x:
            menuAdd(self, endingmenu, name, help, self.OnLineEndChange, idn, typ)
        #
        setmenu.AppendSeparator()
        menuAdd(self, setmenu, "Show Autocomplete", "Show the autocomplete dropdown while typing", self.OnAutoCompleteToggle, AUTO, wxITEM_CHECK)
        menuAdd(self, setmenu, "Show line numbers", "Show or hide the line numbers on the current document", self.OnNumberToggle, NUM, wxITEM_CHECK)
        menuAdd(self, setmenu, "Show margin", "Show or hide the bookmark signifier margin on the current document", self.OnMarginToggle, MARGIN, wxITEM_CHECK)
        menuAdd(self, setmenu, "Show Indentation Guide", "Show or hide gray indentation guides in indentation", self.OnIndentGuideToggle, INDENTGUIDE, wxITEM_CHECK)
        menuAdd(self, setmenu, "Show Whitespace", "Show or hide 'whitespace' characters", self.OnWhitespaceToggle, S_WHITE, wxITEM_CHECK)
        menuAdd(self, setmenu, "Save Position", "Remember or forget the last position of the cursor when the current document is closed", self.OnSavePositionToggle, SAVE_CURSOR, wxITEM_CHECK)
        setmenu.AppendSeparator()
        ## menuAdd(self, setmenu, "Show/hide tree\tCtrl+Shift+G", "Show/hide the hierarchical source tree for the currently open document", self.OnTree, wxNewId())
        ## menuAdd(self, setmenu, "Hide all trees", "Hide the browsable source tree for all open documents", self.OnTreeHide, wxNewId())
        menuAdd(self, setmenu, "Refresh\tF5", "Refresh the browsable source tree, autocomplete listing, and the tooltips (always accurate, but sometimes slow)", self.OnRefresh, wxNewId())
        setmenu.AppendSeparator()
        ## menuAdd(self, setmenu, "Sort Tree by Name", "If checked, will sort the items in the browsable source tree by name, otherwise by line number", self.OnTreeSortToggle, SORTBY, wxITEM_CHECK)
        menuAdd(self, setmenu, "Expand all", "Expand all folded code through the entire document", self.OnExpandAll, wxNewId())
        menuAdd(self, setmenu, "Fold all", "Fold all expanded code through the entire document", self.OnFoldAll, wxNewId())
        menuAdd(self, setmenu, "Use Tabs", "New indentation will include tabs", self.OnSetTabToggle, USETABS, wxITEM_CHECK)
        menuAdd(self, setmenu, "Wrap Long Lines", "Visually continue long lines to the next line", self.OnWrapL, WRAPL, wxITEM_CHECK)
        setmenu.AppendSeparator()
        menuAdd(self, setmenu, "Set Triggers", "Sets trigger expansions for the current document", self.OnSetTriggers, wxNewId())
        menuAdd(self, setmenu, "Set Indent Width", "Set the number of spaces per indentation level", self.OnSetIndent, wxNewId())
        menuAdd(self, setmenu, "Set Tab Width", "Set the visual width of tabs in the current open document", self.OnSetTabWidth, wxNewId())
        menuAdd(self, setmenu, "Set Long Line Column", "Set the column number for the long line indicator", self.OnSetLongLinePosition, wxNewId())

        #------------------------------ Long line submenu --------------------
        longlinemenu = wxMenu()
        menuAddM(setmenu, longlinemenu, "Set Long Line Indicator", "Change the mode that signifies long lines")
        
        x = LL_RMAPPING.values()
        x.sort()
        for _, idn, name, help in x:
            menuAdd(self, longlinemenu, name, help, self.OnSetLongLineMode, idn, typ)

#-------------------------------- Shell Menu ---------------------------------

        ## self.shell = RunShell(self, menuBar, "&Shell")

#------------------------------- Options Menu --------------------------------
        optionsmenu= wxMenu()
        menuAddM(menuBar, optionsmenu, "&Options")
        settingsmenu = wxMenu()
        menuAddM(optionsmenu, settingsmenu, "Save Settings", "Set the default behavior of documents opened of a given type")
        for mid in SITO:
            lang, desc = SOURCE_ID_TO_OPTIONS[mid]
            menuAdd(self, settingsmenu, desc, "Save the settings for the current document as the default for %s documents"%desc, self.OnSaveLang, mid)
        #menuAdd(self, settingsmenu, "", ", self.OnSaveSettings, wxNewId())
        loadsettingsmenu = wxMenu()
        menuAddM(optionsmenu, loadsettingsmenu, "Load Settings", "Set the current document behavior to that of the default for documents of a given type")
        for mid in SITO2:
            lang, desc = SOURCE_ID_TO_OPTIONS2[mid]
            menuAdd(self, loadsettingsmenu, desc, "Set the current document behavior to that of the default for %s"%desc, self.OnLoadSavedLang, mid)
        
        optionsmenu.AppendSeparator()
                #---------------------------- Default Style submenu ------------------
        stylemenu2 = wxMenu()
        menuAddM(optionsmenu, stylemenu2, "Default Highlighting", "Set the default syntax highlighting for new or unknown documents")
        for i in ASSOC:
            name, mid = i[6], i[1]
            st = "All new or unknown documents will be highlighted as %s"%name
            menuAdd(self, stylemenu2, name, st, self.OnDefaultStyleChange, mid, typ)

        optionsmenu.AppendSeparator()
        menuAdd(self, optionsmenu, "Enable File Drops", "Enable drag and drop file support onto the text portion of the editor", self.OnDNDToggle, DND_ID, wxITEM_CHECK)
        optionsmenu.AppendSeparator()
        menuAdd(self, optionsmenu, "Editor on top", "When checked, the editor is above the Todos, Log, etc., otherwise it is below (requires restart)", self.OnLogBarToggle, LB_ID, wxITEM_CHECK)
        menuAdd(self, optionsmenu, "Editor on left", "When checked, the editor is left of the source trees, document list, etc., otherwise it is to the right (requires restart)", self.OnDocBarToggle, DB_ID, wxITEM_CHECK)
        menuAdd(self, optionsmenu, "Show Wide Tools", "Shows or hides the tabbed tools that are above or below the editor", self.OnShowWideToggle, WIDE_ID, wxITEM_CHECK)
        menuAdd(self, optionsmenu, "Show Tall Tools", "Shows or hides the tabbed tools that are right or left of the editor", self.OnShowTallToggle, TALL_ID, wxITEM_CHECK)
        menuAdd(self, optionsmenu, "Wide Todo", "When checked, the todo list will be near the Log tab, when unchecked, will be near the Documenst tab (requires restart)", self.OnTodoToggle, TD_ID, wxITEM_CHECK)
        menuAdd(self, optionsmenu, "One PyPE", "When checked, will listen on port 9999 for filenames to open", self.OnSingleToggle, SINGLE_ID, wxITEM_CHECK)
        toolbarOptionsMenu = wxMenu()
        menuAddM(optionsmenu, toolbarOptionsMenu, "Toolbar", "When checked, will show a toolbar (requires restart)")
        
        x = TB_RMAPPING.values()
        x.sort()
        for _, idn, name, help in x:
            menuAdd(self, toolbarOptionsMenu, name, help, self.OnToolBar, idn, typ)
        
        optionsmenu.AppendSeparator()
        caretmenu = wxMenu()
        menuAddM(optionsmenu, caretmenu, "Caret Options", "Set how your caret behaves while it is moving around")
        
        x = [(j[2], i, j[3], j[4]) for i,j in CARET_ID_TO_OPTIONS.iteritems()]
        x.sort()
        for _, idn, name, help in x:
            menuAdd(self, caretmenu, name, help, self.OnCaret, idn, typ)
        
        menuAdd(self, optionsmenu, "Set Caret M value", "Set the number of lines of unapproachable margin, the M value referenced in Caret Options", self.OnCaretM, wxNewId())
        menuAdd(self, optionsmenu, "Set Caret N value", "Set the multiplier, the N value referenced in Caret Options", self.OnCaretN, wxNewId())
        optionsmenu.AppendSeparator()
        menuAdd(self, optionsmenu, "Findbar below editor", "When checked, any new find/replace bars will be below the editor, otherwise above (bars will need to be reopened)", self.OnFindbarToggle, FINDBAR_BELOW_EDITOR, wxITEM_CHECK)
        menuAdd(self, optionsmenu, "Use Findbar history", "When checked, allows for the find and replace bars to keep history of searches (bars will need to be reopened)", self.OnFindbarHistory, NO_FINDBAR_HISTORY, wxITEM_CHECK)
        menuAdd(self, optionsmenu, "Clear Find Bar history", "Clears the find/replace history on the current document", self.OnFindbarClear, CLEAR_FINDBAR_HISTORY)
        optionsmenu.AppendSeparator()
        menuAdd(self, optionsmenu, "Change Menus and Hotkeys", "Change the name of menu items and their hotkeys, any changes will require a restart to take effect", self.OnChangeMenu, wxNewId())
        titlemenu = wxMenu()
        menuAddM(optionsmenu, titlemenu, "Title Options", "Set what information you would like PyPE to display in the title bar")
        fn = "pype.py"
        long = "C:\\PyPE\\pype.py"
        pype = "PyPE %s"%VERSION
        for i in xrange(5):
            title_id, proto, desc = TITLE_OPTION_TO_ID[i]
            menuAdd(self, titlemenu, desc, "Set the title like: "+proto%locals(), self.OnChangeTitle, title_id, typ)
        menuAdd(self, optionsmenu, "Save preferences", "Saves all of your current preferences now", self.OnSavePreferences, wxNewId())
            

#--------------------------------- Help Menu ---------------------------------

        helpmenu= wxMenu()
        menuAddM(menuBar, helpmenu, "&Help")
        menuAdd(self, helpmenu, "About...", "About this piece of software", self.OnAbout, wxID_ABOUT)
        helpmenu.AppendSeparator()
        menuAdd(self, helpmenu, "PyPE Help\tF1", "View the help", self.OnHelp, wxID_HELP)

#------------------------ A ...few... state variables ------------------------

        self.Show(true)
        self.dirname = '.'
        self.closing = 0
        self.openfiles = {}
        self.realfn = {}
        self.dpm = 0
        self.menubar.Check(AUTO, showautocomp)
        self.menubar.Check(WRAPL, wrapmode != wxSTC_WRAP_NONE)
        self.menubar.Check(DND_ID, dnd_file)
        self.menubar.Check(LB_ID, logbarlocn)
        self.menubar.Check(DB_ID, docbarlocn)
        self.menubar.Check(WIDE_ID, SHOWWIDE)
        self.menubar.Check(TALL_ID, SHOWTALL)
        self.menubar.Check(SINGLE_ID, single_pype_instance)
        self.menubar.Check(TD_ID, TODOBOTTOM)
        self.menubar.Check(TB_RMAPPING[TOOLBAR][1], 1)
        self.menubar.Check(USETABS, use_tabs)
        self.menubar.Check(INDENTGUIDE, indent_guide)
        self.menubar.Check(lexers3[DEFAULTLEXER], 1)
        self.menubar.Check(SAVE_CURSOR, save_cursor)
        self.menubar.Check(CARET_OPTION_TO_ID[caret_option][0], 1)
        self.menubar.Check(TITLE_OPTION_TO_ID[title_option][0], 1)
        self.menubar.Check(FINDBAR_BELOW_EDITOR, findbar_location)
        self.menubar.Check(NO_FINDBAR_HISTORY, not no_findbar_history)
        self.menubar.FindItemById(CLEAR_FINDBAR_HISTORY).Enable(not no_findbar_history)

#------------------------ Drag and drop file support -------------------------
        self.SetDropTarget(FileDropTarget(self))

        #set up some events
        EVT_CLOSE(self, self.OnExit)
        EVT_SIZE(self, self.OnSize)
        EVT_ACTIVATE(self, self.OnActivation)
        EVT_KEY_DOWN(self, self.OnKeyPressed)
        self.starting = 0
        if self.control.GetPageCount() > 0:
            stc = self.getNumWin()[1]
            self.OnDocumentChange(stc)

        #set up some timers
        tid = wxNewId()
        self.timer = wxTimer(self, tid)
        EVT_TIMER(self, tid, self.ex_size)
        tid = wxNewId()
        self.timer2 = wxTimer(self, tid)
        EVT_TIMER(self, tid, self.keyposn)
        self.timer2.Start(100, wxTIMER_CONTINUOUS)

#------------------ Open files passed as arguments to PyPE -------------------
        if not SHOWTALL:
            self.RIGHT.Hide()
        if not SHOWWIDE:
            self.BOTTOM.Hide()
        
        if (not SHOWWIDE) or (not SHOWTALL):
            self.OnSize(None)
        
        self.OnDrop(fnames, 0)
        if single_pype_instance:
            single_instance.startup()
        if USE_THREAD:
            self.Bind(EVT_DONE_PARSING, self.doneParsing)
            wxCallAfter(start_parse_thread, self)

    #...

    def getglobal(self, nam):
        return globals()[nam]

    def getInt(self, title, text, default):
        dlg = wxTextEntryDialog(self, text, title, str(default))
        resp = dlg.ShowModal()
        valu = dlg.GetValue()
        dlg.Destroy()
        if resp != wxID_OK:
            raise cancelled
        return validate(valu, default)
    
    def _setupToolBar(self):
        size = (16,16)
        def getBmp(artId, client):
            bmp = wxArtProvider_GetBitmap(artId, client, size)
            if not bmp.Ok():
                bmp = EmptyBitmap(*size)
            return bmp
        
        if TOOLBAR == 1:
            orient = wxTB_HORIZONTAL
        else:
            orient = wxTB_VERTICAL
        tb = self.CreateToolBar(
            orient|wxNO_BORDER|wxTB_FLAT|wxTB_TEXT)
        
        tb.SetToolBitmapSize(size)
        
        icon = getBmp(wxART_NORMAL_FILE, wxART_TOOLBAR)
        tb.AddSimpleTool(wxID_NEW, icon, "New Document",
            "Create a new empty document")
        icon = getBmp(wxART_FILE_OPEN, wxART_TOOLBAR)
        tb.AddSimpleTool(wxID_OPEN, icon, "Open",
            "Open an existing document")
        icon = getBmp(wxART_FILE_SAVE, wxART_TOOLBAR)
        tb.AddSimpleTool(wxID_SAVE, icon, "Save", "Save current document")
        
        icon = getBmp(wxART_FILE_SAVE_AS, wxART_TOOLBAR)
        tb.AddSimpleTool(wxID_SAVEAS, icon, "Save as...", "Save current document as...")

        tb.AddSeparator()

        icon = getBmp(wxART_CUT, wxART_TOOLBAR)
        tb.AddSimpleTool(wxID_CUT, icon, "Cut",
            "Cut selection to the clibboard")
        icon = getBmp(wxART_COPY, wxART_TOOLBAR)
        tb.AddSimpleTool(wxID_COPY, icon, "Copy",
            "Copy selection to the clibboard")
        icon = getBmp(wxART_PASTE, wxART_TOOLBAR)
        tb.AddSimpleTool(wxID_PASTE, icon, "Paste",
            "Paste current clibboard contents")
        icon = getBmp(wxART_DELETE, wxART_TOOLBAR)
        tb.AddSimpleTool(pypeID_DELETE, icon, "Delete",
            "Delete selection")

        tb.AddSeparator()

        icon = getBmp(wxART_UNDO, wxART_TOOLBAR)
        tb.AddSimpleTool(wxID_UNDO, icon, "Undo",
            "Undo edit")
        icon = getBmp(wxART_REDO, wxART_TOOLBAR)
        tb.AddSimpleTool(wxID_REDO, icon, "Redo",
            "Redo edit (i.e. undo undo edit)")

        tb.AddSeparator()

        icon = getBmp(wxART_FIND, wxART_TOOLBAR)
        tb.AddSimpleTool(pypeID_FINDBAR, icon, "Find",
            "Find")
        icon = getBmp(wxART_FIND_AND_REPLACE, wxART_TOOLBAR)
        tb.AddSimpleTool(pypeID_REPLACEBAR, icon, "Replace",
            "Find and replace")

        tb.AddSeparator()

        icon = getBmp(wxART_ADD_BOOKMARK, wxART_TOOLBAR)
        tb.AddSimpleTool(pypeID_TOGGLE_BOOKMARK, icon, "Toggle Bookmark",
            "Create or Remove a bookmark at the current line")
        
        icon = getBmp(wxART_GO_DOWN, wxART_TOOLBAR)
        tb.AddSimpleTool(pypeID_NEXT_BOOKMARK, icon, "Next Bookmark",
            "Go to the next bookmark in this file")

        icon = getBmp(wxART_GO_UP, wxART_TOOLBAR)
        tb.AddSimpleTool(pypeID_PRIOR_BOOKMARK, icon, "Previous Bookmark",
            "Go to the previous bookmark in this file")
        
        tb.AddSeparator()
        tb.AddSeparator()
        
        icon = getBmp(wxART_HELP, wxART_TOOLBAR)
        tb.AddSimpleTool(wxID_HELP, icon, "Help!",
            "Opens up the help for PyPE")
        
        tb.Realize()

    def OnDocumentChange(self, stc, forced=False):
        if not self.starting:
            start = time.time()

            if stc.cached is None or forced:
                if stc.refresh:
                    return
                stc.ConvertEOLs(fmt_mode[stc.format])
                out = wxStyledTextCtrl.GetText(stc).replace('\t', stc.GetTabWidth()*' ')
                lang = lexer2lang.get(stc.GetLexer(), 'text')
                if out and USE_THREAD:
                    stc.refresh = 1
                    parse_queue.put((out, stc, lang))
                    return
                tpl = parse(lang, out, stc.format, 3, lambda:None)

                stc.cached = tpl
                h1, stc.kw, stc.tooltips, todo = tpl

                stc.kw.sort()
                stc.kw = ' '.join(stc.kw)

                ## ex1 = copy.deepcopy(h1)
                stc.tree1.new_hierarchy(h1)
                stc.tree2.new_hierarchy(h1)

                forced = 1
            else:
                todo = copy.deepcopy(stc.cached[-1])

            self.todolist.NewItemList(todo)
            self.updateWindowTitle()
            if forced:
                self.SetStatusText(("Browsable source tree, autocomplete, tooltips and todo"
                                    " updated for %s in %.1f seconds.")%(stc.filename, time.time()-start))
    def doneParsing(self, evt):
        stc = evt.stc
        try:
            stc.refresh = 0
        except:
            return
        
        tpl = evt.tpl
        
        stc.cached = tpl
        h1, stc.kw, stc.tooltips, todo = tpl
        stc.kw.sort()
        stc.kw = ' '.join(stc.kw)
        ## ex1 = copy.deepcopy(h1)
        stc.tree1.new_hierarchy(h1)
        stc.tree2.new_hierarchy(h1)
        self.SetStatusText(("Browsable source tree, autocomplete, tooltips and todo"
                            " updated for %s in %.1f seconds.")%(stc.filename, evt.delta))

    def updateWindowTitle(self):
        pype = "PyPE %s"%VERSION
        stc = None
        try:
            num, stc = self.getNumWin()
        except cancelled:
            self.SetTitle(pype)
            return
        if stc is not None:
            fn, dn = stc.filename, stc.dirname
            if fn == ' ':
                fn = "<untitled %i>"%stc.NEWDOCUMENT
            long = os.path.join(dn, fn)
            
            disp = TITLE_OPTION_TO_ID[title_option][1]%locals()
        else:
            disp = pype
        self.SetTitle(disp)

    def ex_size(self, evt=None):
        #an attempt to keep the findbar the correct size
        try:
            win = self.getNumWin()[1]
            if win.parent.IsSplit():
                size = (win.parent.GetWindow2().GetAdjustedBestSize())[1]+5
                win.parent.SetSashPosition(-size)
            win.tree1.OnSize(None)
            win.tree2.OnSize(None)
        except cancelled:
            pass

    def keyposn(self, evt=None):
        #an attempt to keep the line and column indicators correct
        try:
            win = self.getNumWin()[1]
            win.pos_ch(evt)
        except cancelled:
            pass
        
        if single_pype_instance:
            single_instance.poll()

    def OnSashDrag(self, event):
        if event.GetDragStatus() == wxSASH_STATUS_OUT_OF_RANGE:
            return

        eID = event.GetId()

        if eID == ID_WINDOW_RIGHT:
            self.RIGHT.SetDefaultSize((max(event.GetDragRect().width, SMALL), BIG))

        elif eID == ID_WINDOW_BOTTOM:
            self.BOTTOM.SetDefaultSize((BIG, max(event.GetDragRect().height, SMALL)))

        wxLayoutAlgorithm().LayoutWindow(self, self.control)
        self.control.Refresh()

        self.ex_size()

    def OnSize(self, event):
        wxLayoutAlgorithm().LayoutWindow(self, self.control)
        self.ex_size()

    def dialog(self, message, title, styl=wxOK):
        d= wxMessageDialog(self,message,title,styl)
        retr = d.ShowModal()
        d.Destroy()
        return retr

    def exceptDialog(self, title="Error"):
        k = cStringIO.StringIO()
        traceback.print_exc(file=k)
        k.seek(0)
        dlg = wxScrolledMessageDialog(self, k.read(), title)
        dlg.ShowModal()
        dlg.Destroy()

    def OnDrop(self, fnames, error=1):
        cwd = os.getcwd()
        for i in fnames:
            dn, fn = os.path.split(self.getAlmostAbsolute(i, cwd))
            if self.isOpen(fn, dn):
                if len(fnames)==1:
                    self.selectAbsolute(self.getAbsolute(fn, dn))
            else:
                self.makeOpen(fn, dn)
                try:
                    a = self.newTab(dn, fn, len(fnames)==1)
                    i = os.path.join(dn, fn)
                    if UNICODE: a = "%s as %s"%(i, a)
                    else:       a = i
                    self.SetStatusText("Opened %s"%a)
                except:
                    if error:
                        self.exceptDialog("File open failed")

        self.redrawvisible()

    def SetStatusText(self, text, number=0, log=1):
        if (number == 0) and text:
            if log:
                print text
                text = "[%s] %s"%(time.asctime(), text)
        self.sb.SetStatusText(text, number)

    def OnActivation(self, e):
        try:
            self.control.__iter__
        except wxPyDeadObjectError:
            e.Skip()
            return
        try:
            self.iter
            e.Skip()
            return
        except:
            self.iter = None
        for document in self.control.__iter__():
            if document.mod != None:
                fn = self.getAlmostAbsolute(document.filename, document.dirname)
                try:
                    mod = os.stat(fn)[8]
                except OSError:
                    document.MakeDirty(None)
                    self.dialog("%s\n"\
                                "has been deleted from the disk by an external program.\n"\
                                "Unless the file is saved again, data loss may occur."%fn,
                                "WARNING!")
                    document.mod = None
                    continue
                if mod != document.mod:
                    if open(fn, 'rb').read() == document.GetText():
                        #Compare the actual text, just to make sure...
                        #Fixes a problem with PyPE being open during daylight
                        #savings time changes.
                        #Also fixes an issue when an identical file is saved
                        #over a currently-being-edited file.
                        document.mod = mod
                        document.MakeClean(None)
                        continue

                    document.MakeDirty(None)
                    a = self.dialog("%s\n"\
                                    "has been modified by an external program.\n"\
                                    "Would you like to reload the file from disk?"%fn,
                                    "WARNING!", wxYES_NO)
                    if a == wxID_NO:
                        document.mod = None
                    else:
                        self.OnReload(None, document)
        del self.iter
        self.redrawvisible()
        self.SendSizeEvent()
        e.Skip()

#--------------------------- cmt-001 - 08/06/2003 ----------------------------
#--------------------- Saving and loading of preferences ---------------------
    def loadHistory(self):
        if not os.path.exists(self.configPath):
            os.mkdir(self.configPath)
        path = os.path.join(self.configPath, 'history.txt')
        if UNICODE:
            p = os.path.join(self.configPath, 'history.u.txt')
            if os.path.exists(p):
                path = p
        print "Loading history from", path
        try:    self.config = self.readAndEvalFile(path)
        except: self.config = {}
        if 'history' in self.config:
            history = self.config['history']
            history.reverse()
            for h in history:
                self.fileHistory.AddFileToHistory(h)
        if 'lastpath' in self.config:
            self.lastpath = self.config['lastpath']

        doc_def = {}
        #insert global document defaults here
        dct =     {'use_tabs':0,
             'spaces_per_tab':8,
                     'indent':4,
                   'collapse':1,
              'marker_margin':1,
                'line_margin':1,
                   'col_line':78,
                   'col_mode':wxSTC_EDGE_LINE,
               'indent_guide':0,
               'showautocomp':0,
                   'wrapmode':wxSTC_WRAP_NONE,
                   'sortmode':1,
                'save_cursor':0,
                'cursor_posn':0,
                 'whitespace':0,
                   'triggers':{},
               'findbarprefs':{}}
        for _i in ASSOC:
            doc_def[_i[2]] = dict(dct)
        for (nam, dflt) in [('modulepaths', []),
                            ## ('usesnippets', 0),
                            ## ('usetodo', 0),
                            ## ('paths', {}),
                            ## ('display2code', {}),
                            ## ('displayorder', []),
                            ## ('shellcommands', []),
                            ('lastopen', []),
                            ('LASTUSED', []),
                            ('DEFAULTLEXER', 'python'),
                            ('FIF_STATE', ([], [], [], 0, 0, 0)),
                            ('match_flags', wxFR_DOWN),
                            ('pathmarksn', []),
                            ('workspaces', {}),
                            ('workspace_order', []),
                            ('SASH1', 60),
                            ('SASH2', 300),
                            ('LASTSIZE', (900,600)),
                            ('LASTPOSITION', self.GetPositionTuple()),
                            ('logbarlocn', 1),
                            ('docbarlocn', 1),
                            ('dnd_file', 1),
                            ('caret_option', 0),
                            ('caret_slop', 10),
                            ('caret_multiplier', 20),
                            ('findbarprefs', {}),
                            ('no_findbar_history', 0),
                            ('title_option', 0),
                            ('document_defaults', doc_def),
                            ('DOCUMENT_DEFAULTS', dct),
                            ('TODOBOTTOM', 1),
                            ('TOOLBAR', 0),
                            ('SHOWWIDE', 1),
                            ('SHOWTALL', 1),
                            ('shellprefs', {}),
                            ('findbar_location', 1),
                            ('single_pype_instance', 0),
                            ('DICTIONARIES', {}),
                            ]:
            if nam in self.config:
                if isinstance(dflt, dict):
                    for k,v in dflt.iteritems():
                        if k not in self.config[nam]:
                            if isinstance(v, dict):
                                self.config[nam][k] = dict(v)
                            else:
                                self.config[nam][k] = v
                        elif isinstance(v, dict):
                            V = self.config[nam][k]
                            for k2,v2 in v.iteritems():
                                if k2 not in V:
                                    V[k2] = v2
            elif isinstance(dflt, dict):
                self.config[nam] = dict(dflt)
            else:
                self.config[nam] = dflt
            globals()[nam] = self.config[nam]
        globals().update(dct)
        globals().update(self.config.setdefault('DOCUMENT_DEFAULTS', dct))

    def saveHistory(self):
        
        LASTOPEN = []
        sav = []
        for win in self.control:
            if win.dirname:
                sav.append(self.getAlmostAbsolute(win.filename, win.dirname))
                LASTOPEN.append((self.getAbsolute(win.filename, win.dirname), win.GetSaveState()))


        if 'LASTOPEN' in self.config:
            del self.config['LASTOPEN']
        #saving document state
        self.config['lastopen'] = sav
        self.config['LASTUSED'] = self.lastused.items() + LASTOPEN
        self.config['LASTSIZE'] = self.GetSizeTuple()
        self.config['LASTPOSITION'] = self.GetPositionTuple()
        self.config['SASH1'] = self.BOTTOM.GetSizeTuple()[1]
        self.config['SASH2'] = self.RIGHT.GetSizeTuple()[0]
        
        history = []
        for i in range(self.fileHistory.GetNoHistoryFiles()):
            history.append(self.fileHistory.GetHistoryFile(i))
        self.config['history'] = history
        ## a = []
        ## for i in self.shell.order:
            ## a.append(self.shell.menu[i])
        ## self.config['shellcommands'] = a
        self.config['match_flags'] = match_flags
        self.config['pathmarksn'] = self.pathmarks.op.GetLabels()
        self.config['workspaces'] = workspaces
        self.config['workspace_order'] = workspace_order
        self.config['logbarlocn'] = logbarlocn
        self.config['docbarlocn'] = docbarlocn
        self.config['dnd_file'] = dnd_file
        self.config['caret_option'] = caret_option
        self.config['caret_slop'] = caret_slop
        self.config['caret_multiplier'] = caret_multiplier
        self.config['findbarprefs'] = findbarprefs
        self.config['no_findbar_history'] = no_findbar_history
        self.config['title_option'] = title_option
        self.config['TODOBOTTOM'] = TODOBOTTOM
        self.config['single_pype_instance'] = single_pype_instance
        self.config['TOOLBAR'] = TOOLBAR
        self.config['SHOWWIDE'] = SHOWWIDE
        self.config['SHOWTALL'] = SHOWTALL
        ## self.config['shellprefs'] = self.shell.save_prefs()
        self.config['findbar_location'] = findbar_location
        ## if self.config['usesnippets'] and (not self.restart):
            ## self.config['display2code'] = self.snippet.display2code
            ## self.config['displayorder'] = self.snippet.displayorder
        self.config['lastpath'] = self.config.get('lp', os.getcwd())
        try:
            if UNICODE:
                path = os.sep.join([self.configPath, 'history.u.txt'])
            else:
                path = os.sep.join([self.configPath, 'history.txt'])
            print "Saving history to", path
            f = open(path, "w")
            f.write(pprint.pformat(self.config))
            f.close()
            if UNICODE:
                path = os.sep.join([self.configPath, 'menus.u.txt'])
            else:
                path = os.sep.join([self.configPath, 'menus.txt'])
            print "Saving menus to", path
            f = open(path, "w")
            f.write(pprint.pformat(MENUPREF))
            f.close()
        except:
            self.exceptDialog("Could not save preferences to %s"%path)

    def readAndEvalFile(self, filename):
        f = open(filename)
        txt = f.read().replace('\r\n','\n')
        f.close()
        return eval(txt)
#------------------------- end cmt-001 - 08/06/2003 --------------------------

    def redrawvisible(self, win=None):

        if (not win) and self.control.GetPageCount() > 0:
            num, win = self.getNumWin()
        if win:
            win.parent.Refresh()
#----------------------------- File Menu Methods -----------------------------
    def getPositionAbsolute(self, path, newf=0):
        ## print path
        path = os.path.normcase(path)
        dn, fn = self.splitAbsolute(path)
        if newf:
            try:
                v = int(fn[10:-1])
            except:
                return -1
        for i in xrange(self.control.GetPageCount()):
            win = self.control.GetPage(i).GetWindow1()
            if newf:
                if not win.dirname and v == win.NEWDOCUMENT:
                    return i
            elif path == self.getAbsolute(win.filename, win.dirname):
                return i

        return -1

    def selectAbsolute(self, path):
        if self.isAbsOpen(path):
            i = self.getPositionAbsolute(path)
            if i != -1:
                self.control.SetSelection(i)

    def isOpen(self, fn, dn):
        return dn and fn and (self.getAbsolute(fn, dn) in self.openfiles)
    def isAbsOpen(self, path):
        return path in self.openfiles

    def makeOpen(self, fn, dn):
        if fn and dn:
            a = self.getAbsolute(fn, dn)
            self.openfiles[a] = self.splitAbsolute(a)
            self.realfn[a] = self.getAlmostAbsolute(fn, dn)

    def closeOpen(self, fn, dn):
        if fn and dn:
            a = self.getAbsolute(fn, dn)
            del self.openfiles[a]
            del self.realfn[a]

    def getAbsolute(self, fn, dn):
        return os.path.normcase(os.path.normpath(os.path.realpath(os.path.join(dn, fn))))
    def getAlmostAbsolute(self, fn, dn):
        return os.path.normpath(os.path.realpath(os.path.join(dn, fn)))
    def splitAbsolute(self, path):
        return os.path.split(os.path.normcase(path))

    def OnNew(self,e):
        self.newTab('', ' ', 1)
        self.control.GetPage(self.control.GetSelection()).GetWindow1().opened = 1

    def OnSave(self,e):
        wnum, win = self.getNumWin(e)
        if win.dirname:
            try:
                txt = win.GetText()
                ofn = os.path.join(win.dirname, win.filename)
                fil = open(ofn, 'wb')
                fil.write(txt)
                fil.close()
                if UNICODE: a = "%s as %s"%(ofn, win.enc)
                else:       a = ofn
                win.mod = os.stat(ofn)[8]
                self.SetStatusText("Correctly saved %s"%a)
                self.curdocstates[ofn] = win.GetSaveState()
                self.curdocstates[ofn]['checksum'] = md5.new(txt).hexdigest()
                win.MakeClean()
            except cancelled:
                raise
            except:
                self.exceptDialog("Save Failed")
                raise cancelled
        else:
            self.OnSaveAs(e)

    def OnSaveAs(self,e):
        wnum, win = self.getNumWin(e)

        dlg = wxFileDialog(self, "Save file as...", os.getcwd(), "", "All files (*.*)|*.*", wxSAVE|wxOVERWRITE_PROMPT)
        rslt = dlg.ShowModal()
        if rslt == wxID_OK:
            fn=dlg.GetFilename()
            dn=dlg.GetDirectory()
            if sys.platform == 'win32' and dn[1:] == ':':
                dn += '\\'
            
            pth = self.getAlmostAbsolute(fn, dn)
            dn, fn = os.path.split(pth)

            if win.filename != fn or win.dirname != dn:
                if self.isOpen(fn, dn):
                    self.dialog("Another file with that name and path is already open.\nSave aborted to prevent data corruption.", "Save Aborted!")
                    raise cancelled
                if self.isOpen(win.filename, win.dirname):
                    self.closeOpen(win.filename, win.dirname)
            
            #we do a quick GetText to make sure we don't set the file/dir names
            #unless we really can get the text for the file.
            x = win.GetText()
            
            win.filename = fn
            win.dirname = dn
            self.makeOpen(fn, dn)
            self.fileHistory.AddFileToHistory(pth)
            self.OnSave(e)

            #fix the icons and names.
            self.dragger._RemoveItem(wnum)
            self.dragger._InsertItem(wnum, fn)

            win.MakeDirty()
            win.MakeClean()

            self.control.SetPageImage(wnum, EXT_TO_IMG.get(extns.get(fn.split('.')[-1].lower(), 0), 0))
            self.control.SetSelection(wnum)
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
        wd = self.config.get('lastpath', os.getcwd())
        dlg = wxFileDialog(self, "Choose a/some file(s)...", wd, "", wildcard, wxOPEN|wxMULTIPLE|wxHIDE_READONLY)
        if dlg.ShowModal() == wxID_OK:
            self.OnDrop(dlg.GetPaths())
            self.config['lp'] = dlg.GetDirectory()
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
        #from this folder.
        return os.sep.join([pth[1], '__init__.py'])

    def OnOpenModule(self,e):
        dlg = wxTextEntryDialog(self, 'Enter the module name you would like to open', 'Open module...')
        if dlg.ShowModal() == wxID_OK:
            mod = dlg.GetValue()
        else:
            mod = ''
        dlg.Destroy()
        if mod:
            sp = sys.path[:]
            sys.path.extend(self.config['modulepaths'])
            try:
                self.OnDrop([self.FindModule(mod)])
            except:
                self.dialog("module %s not found"%mod, "not found")
            sys.path = sp

    def OnOpenPrevDocs(self, e):
        if "lastopen" in self.config:
            self.OnDrop(self.config['lastopen'], 1)
    def AddSearchPath(self, e):
        dlg = wxDirDialog(self, "Choose a path", "", style=wxDD_DEFAULT_STYLE|wxDD_NEW_DIR_BUTTON)
        if dlg.ShowModal() == wxID_OK:
            path = os.path.normcase(os.path.normpath(dlg.GetPath()))
            if not (path in self.config['modulepaths']) and not (path in sys.path):
                self.config['modulepaths'].append(path)
    def OnNewPythonShell(self, e):
        self.newTab("", " ", 1, 1)
    def OnNewCommandShell(self, e):
        self.newTab("", " ", 1, 2)

    def newTab(self, d, fn, switch=0, shell=0):
        if 'lastpath' in self.config:
            del self.config['lastpath']
        #ctrlwidth, ctrlh = self.control.GetSizeTuple()

        if d:
            d, fn = os.path.split(self.getAlmostAbsolute(fn, d))
            FN = self.getAbsolute(fn, d)
            f=open(FN,'rb')
            txt = f.read()
            f.close()
        else:
            FN = ''
            txt = ''
        
        split = SplitterWindow(self.control, wxNewId(), style=wxSP_NOBORDER)
        split.SetMinimumPaneSize(0)
        EVT_SPLITTER_SASH_POS_CHANGING(self, split.GetId(), veto)
        
        ftype = extns.get(fn.split('.')[-1].lower(), 'python')
        if ftype in document_defaults:
            print "found filetype-specific defaults", ftype
        else:
            print "could not find", ftype
        state = dict(document_defaults.get(ftype, DOCUMENT_DEFAULTS))
        if not shell:
            nwin = PythonSTC(self.control, wxNewId(), split)
        else:
            t1 = hierCodeTreePanel(self, self.leftt)
            t1.Hide()
            t1.tree.SORTTREE = 0
            t1.parent.sizer.Layout()
            t2 = hierCodeTreePanel(self, self.rightt)
            t2.Hide()
            t2.tree.SORTTREE = 1
            t1.parent.sizer.Layout()
            state = dict(state)
            state['wrapmode'] = 1
            state['whitespace'] = 0
            nwin = interpreter.MyShell(split, wxNewId(), self, (t1, t2), shell&1)

        nwin.filename = fn
        nwin.dirname = d
        if shell < 2:
            nwin.changeStyle(stylefile, self.style(fn))
        else:
            #we don't want to syntax highlight by default for non-python shells.
            nwin.changeStyle(stylefile, self.style('a.txt'))
        
        if d:
            nwin.mod = os.stat(FN)[8]
            if len(txt) == 0:
                nwin.format = eol
                nwin.SetText('')
            else:
                nwin.format = detectLineEndings(txt)
                nwin.SetText(txt)

            #if FN in self.config['LASTOPEN']:
            #    state = self.config['LASTOPEN'][FN]
            if FN in self.lastused:
                state.update(self.lastused[FN])
                ## print "found saved state"
                del self.lastused[FN]

        else:
            nwin.mod = None
            nwin.format = eol
            nwin.SetText(txt)

        ## print 2
        if not ((d == '') and (fn == ' ')):
            self.fileHistory.AddFileToHistory(os.path.join(d, fn))
        
        if 'checksum' in state:
            if md5.new(txt).hexdigest() != state['checksum']:
                state.update(RESET)
        
        if FN:
            self.curdocstates[FN] = state
        
        nwin.SetSaveState(state)
        ## nwin.SetSaveState({})

        ## print 3
        if fn == ' ':
            ## print 3.5
            globals()['NEWDOCUMENT'] += 1
            nwin.NEWDOCUMENT = NEWDOCUMENT
            fn = '<untitled %i>'%NEWDOCUMENT
        ## print 4
        split.Initialize(nwin)
        ## print 5
        self.control.AddPage(split, fn, switch)
        nwin.MakeClean()
        ## self.OnRefresh(None, nwin)
        self.updateWindowTitle()
        if switch:
            nwin.SetFocus()
        ## self.OnDocumentChange(nwin)
        
        return nwin.enc

    def OnReload(self, e, win=None):
        if win == None:
            num, win = self.getNumWin(e)
        if not e is None:
            dlg = wxMessageDialog(self, "%s was modified after last save.\nReloading from disk will destroy all changes.\n\nContinue anyway?"%win.filename, 'File was modified, data loss may occur!', wxYES_NO|wxCANCEL)
            a = dlg.ShowModal()
            if a == wxID_CANCEL:
                raise cancelled
            elif a == wxID_NO:
                return
        try:
            FN = self.getAbsolute(win.filename, win.dirname)
            fil = open(FN, 'rb')
            txt = fil.read()
            fil.close()
            win.BeginUndoAction()
            win.SetText(txt, 0)
            win.EndUndoAction()
            win.mod = os.stat(FN)[8]
            win.SetSavePoint()
            win.MakeClean()
            self.curdocstates[FN] = {'checksum':md5.new(txt).hexdigest()}
            self.OnRefresh(None, win)
        except:
            self.dialog("Error encountered while trying to reload from disk.", "Reload failed")

    def sharedsave(self, win):
        nam = win.filename
        if not win.dirname:
            nam = "<untitled %i>"%win.NEWDOCUMENT
        a = self.dialog("%s was modified after last save.\nSave changes before closing?"%nam,\
                        "Save changes?", wxYES_NO|wxCANCEL)
        if a == wxID_CANCEL:
            raise cancelled
        elif a == wxID_NO:
            return 0
        else:
            self.OnSave(None)
            return 1

    def OnClose(self, e, wnum=None, win=None):
        if wnum is None or win is None:
            wnum, win = self.getNumWin(e)
        
        fn = self.getAbsolute(win.filename, win.dirname)
        
        if isdirty(win):
            for i, w in enumerate(self.control):
                if w is win:
                    self.control.SetSelection(i)
                    break
            if win.GetParent().IsSplit():
                f = win.GetParent().GetWindow2()
                if f.replacing:
                    f.loop = 1
                del f
            saved = self.sharedsave(win)
        elif self.isOpen(win.filename, win.dirname):
            self.curdocstates[fn] = win.GetSaveState()
            self.curdocstates[fn]['checksum'] = md5.new(win.GetText()).hexdigest()

        if self.isOpen(win.filename, win.dirname):
            self.lastused[fn] = self.curdocstates.pop(fn, {})
            self.closeOpen(win.filename, win.dirname)
            self.SetStatusText("Closed %s"%self.getAlmostAbsolute(win.filename, win.dirname))
        else:
            self.SetStatusText("Closed unnamed file without saving")
        if hasattr(win, "kill"):
            win.kill()
        self.control.DeletePage(wnum)
        self.updateWindowTitle()

    def OnExit(self,e):
        if self.closing:
            return e.Skip()
        self.closing = 1
        if USE_THREAD:
            parse_queue.put(None)
        sel = self.control.GetSelection()
        cnt = self.control.GetPageCount()
        try:
            for i in xrange(cnt):
                win = self.control.GetPage(i).GetWindow1()

                if isdirty(win):
                    self.control.SetSelection(i)
                    self.sharedsave(win)
        except cancelled:
            self.closing = 0
            try:    return e.Veto()
            except: return e.Skip()

        self.saveHistory()
        if sel > -1:
            self.control.SetSelection(sel)
        return self.Close(True)

#--------------------------- cmt-001 - 08/06/2003 ----------------------------
#------------- Open the file selected from the file history menu -------------
    def OnFileHistory(self, e):
        fileNum = e.GetId() - wxID_FILE1
        path = self.fileHistory.GetHistoryFile(fileNum)
        self.OnDrop([path])
#------------------------- end cmt-001 - 08/06/2003 --------------------------

#----------------------------- Edit Menu Methods -----------------------------
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
    def OnDeleteSelection(self, e):
        self.OneCmd('DeleteSelection',e)
        
#----------------------- Find and Replace Bar Display ------------------------
    def getNumWin(self, e=None):
        num = self.control.GetSelection()
        if num >= 0:
            return num, self.control.GetPage(num).GetWindow1()
        if e:
            e.Skip()
        raise cancelled

    def OnShowFindbar(self, evt):
        num, win = self.getNumWin(evt)
        if win.parent.IsSplit() and not isinstance(win.parent.GetWindow2(), findbar.FindBar):
            win.parent.GetWindow2().close()
        
        if not win.parent.IsSplit():
            bar = findbar.FindBar(win.parent, self)
            win.parent.SplitHorizontally(win, bar, -(bar.GetBestSize())[1]-5, 1-findbar_location)

        bar = win.parent.GetWindow2()
        focused = self.FindFocus()
        hasfocus = (focused == bar) or (focused and focused.GetParent() == bar)

        self.commonbar(win)

        if hasfocus:
            bar.OnFindN(evt)

    def OnShowReplacebar(self, evt):
        num, win = self.getNumWin(evt)
        if win.parent.IsSplit() and isinstance(win.parent.GetWindow2(), findbar.FindBar):
            win.parent.GetWindow2().close()
        
        if not win.parent.IsSplit():
            bar = findbar.ReplaceBar(win.parent, self)
            win.parent.SplitHorizontally(win, bar, -(bar.GetBestSize())[1]-5, 1-findbar_location)

        self.commonbar(win)

    def commonbar(self, win):
        st,end = win.GetSelection()
        box = win.parent.GetWindow2().box1
        if st == end and box.GetLastPosition() == 0:
            gcp = win.GetCurrentPos()
            st = win.WordStartPosition(gcp, 1)
            end = win.WordEndPosition(gcp, 1)
        if st != end:
            x = win.GetTextRange(st, end)
            try:
                x = str(x)
            except UnicodeError:
                pass
            if not isinstance(x, unicode):
                rx = x.encode('string-escape')
                if rx != x:
                    x = repr(x)
            box.SetValue(x)
            win.SetSelection(st, end)

        box.SetFocus()
        if isinstance(box, wxTextCtrl):
            box.SetSelection(0, box.GetLastPosition())
        else:
            box.SetMark(0, box.GetLastPosition())

    def OnFindAgain(self, evt):
        num, win = self.getNumWin(evt)
        if win.parent.IsSplit():
            win.parent.GetWindow2().OnFindN(evt)
        win.SetFocus()

#-------------------------- Transforms Menu Methods --------------------------
    def OnWrap(self, e):
        wnum, win = self.getNumWin(e)

        valu = self.getInt('Wrap to how many columns?', '', col_line)

        win.MakeDirty()
        x,y = win.GetSelection()
        if x==y:
            return
        lnstart = win.LineFromPosition(x)
        lnend = win.LineFromPosition(y-1)

        paragraphs = []
        lines = []
        for ln in xrange(lnstart, lnend+1):
            lin = win.GetLine(ln)
            if not lin.strip():
                if lines:
                    paragraphs.append(win.format.join(textwrap.wrap(' '.join(lines), valu)))
                paragraphs.append(lin.rstrip('\r\n'))
                lines = []
            else:
                lines.append(lin.strip())
        if lines:
            paragraphs.append(win.format.join(textwrap.wrap(' '.join(lines), valu)))

        x = win.GetLineEndPosition(lnstart)-len(lines[0])
        y = win.GetLineEndPosition(lnend)
        #win.SetSelection(x, y)
        win.ReplaceSelection(win.format.join(paragraphs))

    def Dent(self, e, incr):
        wnum, win = self.getNumWin(e)
        incr *= win.GetIndent()
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
            m = (count+incr)
            m += cmp(0, incr)*(m%incr)
            m = max(m, 0)
            win.SetLineIndentation(ln, m)
        if x==y:
            pos = pos + (m-count) - min(0, col + (m-count))
            win.SetSelection(pos, pos)
        else:
            p = 0
            if lnstart != 0:
                p = win.GetLineEndPosition(lnstart-1) + len(win.format)
            win.SetSelection(p, win.GetLineEndPosition(lnend))
        win.EndUndoAction()

    def OnIndent(self, e):
        self.Dent(e, 1)
    def OnDedent(self, e):
        self.Dent(e, -1)
    def OnInsertComment(self, e):
        wnum, win = self.getNumWin(e)
        dlg = wxTextEntryDialog(self, '', 'Enter a comment.', '')
        resp = dlg.ShowModal()
        valu = dlg.GetValue()
        dlg.Destroy()
        if resp == wxID_OK:
            _lexer = win.GetLexer()
            k = len(valu)
            d = ''
            if _lexer == wxSTC_LEX_CPP:
                c = '/*'
                d = '*/'
            elif _lexer in (wxSTC_LEX_HTML, wxSTC_LEX_XML):
                c = '<!-- '
                d = ' -->'
            elif _lexer == wxSTC_LEX_LATEX:
                c = '%'
            else:
                c = '#'
            a = win.GetEdgeColumn() - len(c) - len(d) - 2 - k
            b = a*'-'
            st = '%s%s %s %s%s%s'%(c, b[:a/2], valu, b[a/2:], d, win.format)
            lin = win.GetCurrentLine()
            if lin>0:
                win.InsertText(win.GetLineEndPosition(lin-1)+len(win.format), st)
            else:
                win.InsertText(0, st)
            win.MakeDirty()
        else:
            e.Skip()

    def OnCommentSelection(self, e):
        wnum, win = self.getNumWin(e)
        sel = win.GetSelection()
        start = win.LineFromPosition(sel[0])
        end = win.LineFromPosition(sel[1])
        if end > start and win.GetColumn(sel[1]) == 0:
            end = end - 1
        win.MakeDirty()
        win.BeginUndoAction()
        _lexer = win.GetLexer()
        for lineNumber in range(start, end + 1):
            firstChar = win.GetLineIndentPosition(lineNumber)
            lastChar = win.GetLineEndPosition(lineNumber)
            ranga = win.GetTextRange(firstChar,lastChar)
            if len(ranga.strip()) != 0:
                if _lexer == wxSTC_LEX_CPP:
                    win.InsertText(firstChar, '// ')
                ## elif win.GetLexer() in (wxSTC_LEX_HTML, wxSTC_LEX_XML):
                    ## win.InsertText(lastChar, ' -->')
                    ## win.InsertText(firstChar, '<!-- ')
                elif _lexer == wxSTC_LEX_LATEX:
                    win.InsertText(firstChar, '%')
                else:
                    win.InsertText(firstChar, '## ')
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
        _lexer = win.GetLexer()
        for lineNumber in range(start, end + 1):
            firstChar = win.GetLineIndentPosition(lineNumber)
            lastChar = win.GetLineEndPosition(lineNumber)
            texta = win.GetTextRange(firstChar,lastChar)
            lengtha = 0
            rangeb = None
            if len(texta.strip()) != 0:
                if _lexer == wxSTC_LEX_CPP:
                    if texta.startswith('// '):
                        lengtha = 3
                    elif texta.startswith('//'):
                        lengtha = 2
                ## elif win.GetLexer() in (wxSTC_LEX_HTML, wxSTC_LEX_XML):
                    ## if texta.startswith('<!-- '):
                        ## lengtha = 5
                    ## elif texta.startswith('<!--'):
                        ## lengtha = 4
                    
                    ## if lengtha:
                        ## if texta.endswith(' -->'):
                            ## rangeb = (lastChar-4, lastChar)
                        ## elif texta.endswith('-->'):
                            ## rangeb = (lastChar-3, lastChar)
                elif _lexer == wxSTC_LEX_LATEX:
                    if texta.startswith('%'):
                        lengtha = 1
                else:
                    if texta.startswith('## '):
                        lengtha = 3
                    elif texta.startswith('##'):
                        lengtha = 2
                    elif texta.startswith('#'):
                        lengtha = 1
            if lengtha:
                if rangeb:
                    win.SetSelection(*rangeb)
                    win.ReplaceSelection("")
                
                win.SetSelection(firstChar,firstChar+lengtha)
                win.ReplaceSelection("")

        win.SetCurrentPos(win.PositionFromLine(start))
        win.SetAnchor(win.GetLineEndPosition(end))
        win.EndUndoAction()

    def WrapFE(self, e, tail):
        num, win = self.getNumWin(e)
        
        x,y = win.GetSelection()
        if x==y:
            lnstart = win.GetCurrentLine()
            lnend = lnstart
        else:
            lnstart = win.LineFromPosition(x)
            lnend = win.LineFromPosition(y-1)
        
        for linenum in xrange(lnstart, lnend+1):
            line = win.GetLine(linenum)
            if not line.strip():
                continue
            x = win.GetLineIndentation(linenum)
            break
        else:
            self.SetStatusText("Could not find anything to wrap with try: %s:!"%tail)
            return
        
        win.BeginUndoAction()
        self.OnIndent(e)

        #find the indentation level for the except/finally clause
        xp = x+win.GetIndent()
        xp -= xp%win.GetIndent()
        
        #get some line and selection information
        ss, es = win.GetSelection()
        lnstart = win.LineFromPosition(ss)
        lnend = win.LineFromPosition(es)
        
        #insert the except: or finally:
        win.SetSelection(es, es)
        win.ReplaceSelection(win.format + tail + ':' + win.format)
        win.SetLineIndentation(lnend+1, x)
        win.SetLineIndentation(lnend+2, xp)
        
        #insert the try:
        win.SetSelection(ss, ss)
        win.ReplaceSelection('try:' + win.format)
        win.SetLineIndentation(lnstart, x)
        
        #relocate the cursor
        p = 0
        if lnstart != 0:
            p = win.GetLineEndPosition(lnstart-1) + len(win.format)
        win.SetSelection(p, win.GetLineEndPosition(lnend+3))
        
        win.EndUndoAction()
        
    def WrapFinally(self, e):
        self.WrapFE(e, 'finally')
    def WrapExcept(self, e):
        self.WrapFE(e, 'except')
    def WrapExceptFinally(self, e):
        num, win = self.getNumWin(e)
        win.BeginUndoAction()
        self.WrapFE(e, 'except')
        self.WrapFE(e, 'finally')
        win.EndUndoAction()

    def OnTriggerExpansion(self, e):
        num, win = self.getNumWin(e)
        win.added(None)

#----------------------------- View Menu Methods -----------------------------

    def Maximize(self, b):
        wxFrame.Maximize(b)
        wxPostEvent(wxSizeEvent((0,0), self.GetId()))

    def OnZoom(self, e):
        wnum, win = self.getNumWin(e)
        if e.GetId() == ZI:incr = 1
        else:              incr = -1
        win.SetZoom(win.GetZoom()+incr)

    def OnGoto(self, e):

        wnum, win = self.getNumWin(e)
        valu = self.getInt('Which line would you like to advance to?', '', win.LineFromPosition(win.GetSelection()[0])+1)
        valu -= 1
        if valu < win.GetLineCount():
            linepos = win.GetLineEndPosition(valu)
            win.EnsureVisible(valu)
            win.SetSelection(linepos-len(win.GetLine(valu))+len(win.format), linepos)
            win.ScrollToColumn(0)
    
    def OnGotoP(self, e):
        wnum, win = self.getNumWin(e)
        x = win.GetSelection()[0]
        valu = 0
        while x > 0:
            y, x = x, win.PositionBefore(x)
            valu += len(win.GetTextRange(y,x))
        valu = self.getInt('What position would you like to advance to?', '', valu)
        length = win.GetLength()
        x = 0
        while valu > 0 and x < length:
            y, x = x, win.PositionAfter(x)
            valu -= len(win.GetTextRange(y,x))
        if not valu:
            win.SetSelection(x, x)
    
    def OnJumpF(self, e):
        num, win = self.getNumWin(e)
        win.jump(1)
        
    def OnJumpB(self, e):
        num, win = self.getNumWin(e)
        win.jump(-1)

    def OnRefresh(self, e, win=None):
        if win is None:
            num, win = self.getNumWin(e)
        self.OnDocumentChange(win, True)

    def OnToggleBookmark (self, e):
        wnum, win = self.getNumWin(e)
        lineNo = win.GetCurrentLine()
        if win.MarkerGet(lineNo) & BOOKMARKMASK:
            win.MarkerDelete(lineNo, BOOKMARKNUMBER)
        else:
            win.MarkerAdd(lineNo, BOOKMARKNUMBER)

    def OnNextBookmark  (self, e):
        wnum, win = self.getNumWin(e)
        lineNo = win.GetCurrentLine()
        newLineNo = win.MarkerNext(lineNo + 1, BOOKMARKMASK)
        if newLineNo != -1:
            win.GotoLine(newLineNo)
        else:
            lineNo = win.GetLineCount()
            newLineNo = win.MarkerNext(0, BOOKMARKMASK)
            if newLineNo != -1:
                win.GotoLine(newLineNo)
        win.EnsureVisible(win.GetCurrentLine())
        win.EnsureCaretVisible()

    def OnPreviousBookmark (self, e):
        wnum, win = self.getNumWin(e)
        lineNo = win.GetCurrentLine()
        newLineNo = win.MarkerPrevious(lineNo - 1, BOOKMARKMASK)
        if newLineNo != -1:
            win.GotoLine(newLineNo)
        else:
            lineNo = win.GetLineCount()
            newLineNo = win.MarkerPrevious(lineNo, BOOKMARKMASK)
            if newLineNo != -1:
                win.GotoLine(newLineNo)
        win.EnsureVisible(win.GetCurrentLine())
        win.EnsureCaretVisible()

    def OnLeft(self, e):
        self.control.AdvanceSelection(False)

    def OnRight(self, e):
        self.control.AdvanceSelection(True)        
    
#--------------------------- Document Menu Methods ---------------------------

    def OnStyleChange(self,e):
        wnum, win = self.getNumWin(e)
        win.changeStyle(stylefile, lexers[e.GetId()])

    def style(self, fn):
        ext = fn.split('.')[-1].lower()
        return extns.get(ext, DEFAULTLEXER)

    def OnEncChange(self, e):
        num, win = self.getNumWin(e)
        mid = e.GetId()
        newenc = self.menubar.GetLabel(mid)
        oldenc = win.enc
        if oldenc != newenc:
            win.enc = newenc.strip()
            self.SetStatusText("encoding changed to %s for %s"%(win.enc,
                                  win.filename.strip() or self.control.GetPageText(num).strip(' *')))
        self.SetStatusText(win.enc, 2)

    def OnLineEndChange(self, e):
        n, win = self.getNumWin(e)
        endid = e.GetId()
        newend = LE_MAPPING[endid][0]
        oldend = win.GetEOLMode()
        if oldend != newend:
            win.format = fmt_Rmode[newend]
            win.ConvertEOLs(newend)
            win.SetEOLMode(newend)

    def OnAutoCompleteToggle(self, event):
        # Images are specified with a appended "?type"
        #for i in range(len(kw)):
        #    if kw[i] in keyword.kwlist:
        #        kw[i] = kw[i]# + "?1"
        n, win = self.getNumWin(event)
        win.showautocomp = (win.showautocomp+1)%2

    def OnNumberToggle(self, e):
        n, win = self.getNumWin(e)
        win.SetMarginWidth(0, (win.GetMarginWidth(0)+40)%80)

    def OnMarginToggle(self, e):
        n, win = self.getNumWin(e)
        win.SetMarginWidth(1, (win.GetMarginWidth(1)+16)%32)

    def OnIndentGuideToggle(self, e):
        n, win = self.getNumWin(e)
        win.SetIndentationGuides((win.GetIndentationGuides()+1)%2)
    def OnWhitespaceToggle(self, e):
        n, win = self.getNumWin(e)
        win.SetViewWhiteSpace((win.GetViewWhiteSpace()+1)%2)
        
    def OnSavePositionToggle(self, e):
        n, win = self.getNumWin(e)
        win.save_cursor = (1+win.save_cursor)%2

    def OnExpandAll(self, e):
        n, win = self.getNumWin(e)
        lc = win.GetLineCount()
        win.ShowLines(0, lc-1)
        for line in xrange(lc):
            if win.GetFoldLevel(line) & wxSTC_FOLDLEVELHEADERFLAG:
                win.SetFoldExpanded(line, 1)

    def OnFoldAll(self, e):
        n, win = self.getNumWin(e)
        #these next two lines are to allow
        #win.GetFoldLevel() to be accurate
        win.HideLines(0, win.GetLineCount()-1)
        try: wxYield()
        except: pass

        #toss all the old folds
        self.OnExpandAll(e)

        lc = win.GetLineCount()
        lines = []
        for line in xrange(lc):
            if win.GetFoldLevel(line) & wxSTC_FOLDLEVELHEADERFLAG:
                lines.append(line)
        lines.reverse()
        for line in lines:
            a = win.GetLastChild(line, -1)
            win.HideLines(line+1,a)
            win.SetFoldExpanded(line, 0)

    def OnSetTabToggle(self, e):
        n, win = self.getNumWin(e)
        a = win.GetUseTabs()
        win.SetUseTabs((a+1)%2)
        win.SetProperty("tab.timmy.whinge.level", str(a))

    def OnWrapL(self, e):
        wnum, win = self.getNumWin(e)
        self.WrapToggle(win)

    def WrapToggle(self, win):
        #tossing the current home/end key configuration, as it will change
        win.CmdKeyClear(wxSTC_KEY_HOME,0)
        win.CmdKeyClear(wxSTC_KEY_HOME,wxSTC_SCMOD_SHIFT)
        win.CmdKeyClear(wxSTC_KEY_HOME,wxSTC_SCMOD_ALT)
        win.CmdKeyClear(wxSTC_KEY_HOME,wxSTC_SCMOD_ALT|wxSTC_SCMOD_SHIFT)
        win.CmdKeyClear(wxSTC_KEY_END,0)
        win.CmdKeyClear(wxSTC_KEY_END,wxSTC_SCMOD_SHIFT)
        win.CmdKeyClear(wxSTC_KEY_END,wxSTC_SCMOD_ALT)
        win.CmdKeyClear(wxSTC_KEY_END,wxSTC_SCMOD_ALT|wxSTC_SCMOD_SHIFT)

        if win.GetWrapMode() == wxSTC_WRAP_NONE:
            win.SetWrapMode(wxSTC_WRAP_WORD)

            #making home and end work like we expect them to when lines are wrapped
            win.CmdKeyAssign(wxSTC_KEY_HOME, 0, wxSTC_CMD_HOMEDISPLAY)
            win.CmdKeyAssign(wxSTC_KEY_HOME, wxSTC_SCMOD_SHIFT, wxSTC_CMD_HOMEDISPLAYEXTEND)
            win.CmdKeyAssign(wxSTC_KEY_HOME, wxSTC_SCMOD_ALT, wxSTC_CMD_VCHOME)
            win.CmdKeyAssign(wxSTC_KEY_HOME, wxSTC_SCMOD_ALT|wxSTC_SCMOD_SHIFT, wxSTC_CMD_VCHOMEEXTEND)
            win.CmdKeyAssign(wxSTC_KEY_END, 0, wxSTC_CMD_LINEENDDISPLAY)
            win.CmdKeyAssign(wxSTC_KEY_END, wxSTC_SCMOD_SHIFT, wxSTC_CMD_LINEENDDISPLAYEXTEND)
            win.CmdKeyAssign(wxSTC_KEY_END, wxSTC_SCMOD_ALT, wxSTC_CMD_LINEEND)
            win.CmdKeyAssign(wxSTC_KEY_END, wxSTC_SCMOD_ALT|wxSTC_SCMOD_SHIFT, wxSTC_CMD_LINEENDEXTEND)
        else:
            win.SetWrapMode(wxSTC_WRAP_NONE)

            #making home and end work like we expect them to when lines are not wrapped
            win.CmdKeyAssign(wxSTC_KEY_HOME, 0, wxSTC_CMD_VCHOME)
            win.CmdKeyAssign(wxSTC_KEY_HOME, wxSTC_SCMOD_SHIFT, wxSTC_CMD_VCHOMEEXTEND)
            win.CmdKeyAssign(wxSTC_KEY_HOME, wxSTC_SCMOD_ALT, wxSTC_CMD_HOMEDISPLAY)
            win.CmdKeyAssign(wxSTC_KEY_HOME, wxSTC_SCMOD_ALT|wxSTC_SCMOD_SHIFT, wxSTC_CMD_HOMEDISPLAYEXTEND)
            win.CmdKeyAssign(wxSTC_KEY_END, 0, wxSTC_CMD_LINEEND)
            win.CmdKeyAssign(wxSTC_KEY_END, wxSTC_SCMOD_SHIFT, wxSTC_CMD_LINEENDEXTEND)
            win.CmdKeyAssign(wxSTC_KEY_END, wxSTC_SCMOD_ALT, wxSTC_CMD_LINEENDDISPLAY)
            win.CmdKeyAssign(wxSTC_KEY_END, wxSTC_SCMOD_ALT|wxSTC_SCMOD_SHIFT, wxSTC_CMD_LINEENDDISPLAYEXTEND)

    def OnSetTriggers(self, e):
        num, win = self.getNumWin(e)
        print win.triggers
        a = TriggerDialog(self, win, win.triggers)
        a.ShowModal()

    def OnSetIndent(self, e):
        n, win = self.getNumWin(e)
        rslt = self.getInt("How many spaces per indent level?", "Enter an integer > 0.",
                           win.GetIndent())
        win.SetIndent(rslt)

    def OnSetTabWidth(self, e):
        n, win = self.getNumWin(e)
        rslt = self.getInt("How many spaces per tab?",
                           "How many spaces should a tab character,\n"\
                           "'\\t' represent?  Enter an integer > 0.",
                           win.GetTabWidth())

        win.SetTabWidth(rslt)

    def OnSetLongLinePosition(self, e):
        n, win = self.getNumWin(e)
        rslt = self.getInt("Long Line Indicator",
                           "At what column would you like a long line\n"\
                           "signifier to be displayed?  Enter an integer > 0.",
                           win.GetEdgeColumn())

        win.SetEdgeColumn(rslt)

    def OnSetLongLineMode(self, e):
        n, win = self.getNumWin(e)
        eid = e.GetId()
        win.SetEdgeMode(LL_MAPPING[eid][0])
#--------------------------- Options Menu Methods ----------------------------

    def OnSaveLang(self, e):
        mid = e.GetId()
        lang, desc = SOURCE_ID_TO_OPTIONS.get(mid, ('python', ''))
        n, win = self.getNumWin()
        dct = win.GetSaveState()
        del dct['BM']
        del dct['FOLD']
        document_defaults[lang].update(dct)
        self.SetStatusText("Updated document defaults for " + desc)
    
    def OnLoadSavedLang(self, e):
        mid = e.GetId()
        lang, desc = SOURCE_ID_TO_OPTIONS2.get(mid, ('python', ''))
        n, win = self.getNumWin()
        dct = win.GetSaveState()
        dct.update(document_defaults[lang])
        s,e = win.GetSelection()
        win.SetSaveState(dct)
        win.SetSelection(s,e)
        self.control.updateChecks(win)
        self.SetStatusText("Updated document settings to %s for %s"%(desc, os.path.join(win.dirname, win.filename)))
    
    def OnDefaultStyleChange(self, e):
        dl = lexers[e.GetId()]
        self.config['DEFAULTLEXER'] = dl
        globals()['DEFAULTLEXER'] = dl
    
    def OnSaveSettings(self, e):
        #unused right now.
        n, win = self.getNumWin()
        dct = win.GetSaveState()
        del dct['BM']
        del dct['FOLD']

        globals().update(dct)
        self.config['DOCUMENT_DEFAULTS'] = dct

    def OnDNDToggle(self, e):
        global dnd_file
        dnd_file = (dnd_file + 1)%2

    def OnLogBarToggle(self, e):
        global logbarlocn
        logbarlocn = (logbarlocn + 1)%2

    def OnDocBarToggle(self, e):
        global docbarlocn
        docbarlocn = (docbarlocn + 1)%2
    
    def OnShowWideToggle(self, e):
        global SHOWWIDE
        SHOWWIDE = (SHOWWIDE + 1)%2
        if SHOWWIDE:
            self.BOTTOM.Show()
        else:
            self.BOTTOM.Hide()
        self.OnSize(None)
        
    def OnShowTallToggle(self, e):
        global SHOWTALL
        SHOWTALL = (SHOWTALL + 1)%2
        if SHOWTALL:
            self.RIGHT.Show()
        else:
            self.RIGHT.Hide()
        self.OnSize(None)
    
    def OnTodoToggle(self, e):
        global TODOBOTTOM
        TODOBOTTOM = (TODOBOTTOM + 1)%2
    def OnSingleToggle(self, e):
        global single_pype_instance
        
        if single_pype_instance:
            single_instance.shutdown()
            try:
                x = open(os.path.join(runpath, 'nosocket'), 'w')
                x.close()
            except:
                pass
            single_pype_instance = 0
        else:
            try:
                os.remove(os.path.join(runpath, 'nosocket'))
            except:
                if nosocket:
                    self.menubar.Check(SINGLE_ID, single_pype_instance)
                    return
            try:
                single_instance.startup()
            except:
                single_instance.traceback.print_exc()
                self.menubar.Check(SINGLE_ID, single_pype_instance)
            else:
                single_pype_instance = 1
    
    def OnToolBar(self, e):
        global TOOLBAR
        TOOLBAR = TB_MAPPING[e.GetId()][0]
        self.SetStatusText("To apply your changed toolbar settings, restart PyPE.")
        
    def OnCaret(self, e):
        global caret_option
        i = e.GetId()
        caret_option, flags = CARET_ID_TO_OPTIONS[i][:2]
        self.SharedCaret()

    def OnCaretM(self, e):
        global caret_slop
        caret_slop = self.getInt("Set Caret M Value", "", caret_slop)
        self.SharedCaret()

    def OnCaretN(self, e):
        global caret_multiplier
        caret_multiplier = self.getInt("Set Caret N Value", "", caret_multiplier)
        self.SharedCaret()

    def SharedCaret(self):
        _, flags = CARET_OPTION_TO_ID[caret_option]
        for win in self.control:
            win.SetXCaretPolicy(flags, caret_slop*caret_multiplier)
            win.SetYCaretPolicy(flags, caret_slop)
            win.SetSelection(*win.GetSelection())
    
    def OnFinbarDefault(self, e):
        n, win = self.getNumWin()
        if win.GetParent().IsSplit():
            win.GetParent().GetWindow2().savePreferences()
        a = dict(win.findbarprefs)
        del a['find']
        del a['replace']
        global findbarprefs
        findbarprefs = a
    
    def OnFindbarClear(self, e):
        n, win = self.getNumWin()
        if win.GetParent().IsSplit():
            bar = win.GetParent().GetWindow2()
            bar.box1.Clear()
            bar.box1.SetValue("")
            if not isinstance(bar, findbar.FindBar):
                bar.box2.Clear()
                bar.box2.SetValue("")
            else:
                win.findbarprefs['replace'] = []
        else:
            win.findbarprefs['find'] = []
            win.findbarprefs['replace'] = []
        
    def OnFindbarToggle(self, e):
        global findbar_location
        findbar_location = (findbar_location + 1)%2
        
    def OnFindbarHistory(self, e):
        global no_findbar_history
        no_findbar_history = (no_findbar_history + 1) % 2
        self.menubar.FindItemById(CLEAR_FINDBAR_HISTORY).Enable(not no_findbar_history)
    
    def OnChangeMenu(self, e):
        MenuItemDialog(self, self).ShowModal()
    
    def OnChangeTitle(self, e):
        global title_option
        i = e.GetId()
        title_option, _, _ = TITLE_ID_TO_OPTIONS[i]
        self.updateWindowTitle()
    def OnSavePreferences(self, e):
        self.saveHistory()
        
#----------------------------- Help Menu Methods -----------------------------
    def OnAbout(self, e):
        txt = """
        You're wondering what this editor is all about, right?  Easy, this edior was
        written to scratch an itch.  I (Josiah Carlson), was looking for an editor
        that had the features I wanted, I couldn't find one.  So I wrote one.  And
        here it is.

        PyPE %s (Python Programmers Editor)
        http://come.to/josiah
        PyPE is copyright 2003-2005 Josiah Carlson.
        Contributions are copyright their respective authors.

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
    def OnKeyPressed(self, event):
        showpress=0

        keypressed = GetKeyPress(event)

        if showpress: print "keypressed", keypressed
        key = event.KeyCode()
        wnum = self.control.GetSelection()
        pagecount = self.control.GetPageCount()
        if wnum > -1:
            win = self.control.GetPage(wnum).GetWindow1()

        if keypressed in HOTKEY_TO_ID:
            menuid = HOTKEY_TO_ID[keypressed]
            wxPostEvent(self, wxMenuEvent(wxEVT_COMMAND_MENU_SELECTED, menuid))

        else:
            if pagecount:
                if (key==13):
                    #when 'enter' is pressed, indentation needs to happen.
                    #
                    #will indent the current line to be equivalent to the line above
                    #unless a ':' is at the end of the previous, then will indent
                    #configuration.indent more.
                    if win.AutoCompActive():
                        return win.AutoCompComplete()
                    if win.CallTipActive():
                        win.CallTipCancel()

                    #get information about the current cursor position
                    linenum = win.GetCurrentLine()
                    pos = win.GetCurrentPos()
                    col = win.GetColumn(pos)
                    linestart = win.PositionFromLine(linenum)
                    line = win.GetLine(linenum)[:pos-linestart]

                    #get info about the current line's indentation
                    ind = win.GetLineIndentation(linenum)                    
                    
                    xtra = 0
                    
                    lang = extns.get(win.filename.split('.')[-1].lower(), DEFAULTLEXER)
                    
                    if col <= ind:
                        xtra = None
                        if win.GetUseTabs():
                            win.ReplaceSelection(win.format+(col*' ').replace(win.GetTabWidth()*' ', '\t'))
                        else:
                            win.ReplaceSelection(win.format+(col*' '))
                    elif not pos:
                        xtra = None
                        win.ReplaceSelection(win.format)
                    
                    elif lang == 'cpp':
                        ## print "indent on return for cpp"
                        dmap = {'{':1, '}':2}
                        first = None
                        x = [0,0,0]
                        for ch in line:
                            y = dmap.get(ch, 0)
                            x[y] += 1
                            if not first and y:
                                first=y
                        if first==2:
                            x[2] -= 1
                        xtra = x[1]-x[2]
                        if line.split()[:1] == ['return']:
                            xtra -= 1
                    
                    #insert other indentation per language here.
                    
                    else: #if language is python
                        ## print "indent on return for python"
                        colon = ord(':')
                        
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
                                    #commenting the break fixes stuff like this
                                    # for i in blah[:]:
                                    #break
                            if xtra:
                                #This deals with ending single and multi-line definitions properly.
                                while linenum >= 0:
                                    found = []
                                    for i in ['def', 'class', 'if', 'else', 'elif', 'while',
                                            'for', 'try', 'except', 'finally', 'with']:
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
                        if not xtra:
                            ls = line.lstrip()
                            if (ls[:6] == 'return') or (ls[:4] == 'pass') or (ls[:5] == 'break') or (ls[:8] == 'continue'):
                                xtra = -1
                    
                    if xtra != None:
                        a = ind*' '
                        if win.GetUseTabs():
                            a = a.replace(win.GetTabWidth()*' ', '\t')
                        win.ReplaceSelection(win.format+a)
                        if xtra > 0:
                            for i in xrange(xtra):
                                self.OnIndent(event)
                        elif xtra < 0:
                            for i in xrange(-xtra):
                                self.OnDedent(event)
                else:
                    event.Skip()
                    if not (win.GetStyleAt(win.GetCurrentPos())):
                        #3, 13, 6, 7
                        if win.CallTipActive():
                            good = STRINGPRINTABLE
                            if (key in good) or (key in (WXK_SHIFT, WXK_CONTROL, WXK_ALT)):
                                pass
                                #if key in (48, 57) and event.ShiftDown():
                                #    win.CallTipCancel()
                                #else it is something in the arguments that is OK.
                            else:
                                win.CallTipCancel()
                        if (not win.CallTipActive()) and event.ShiftDown() and (key == ord('9')):
                            win.CallTipSetBackground(wxColour(255, 255, 232))
                            cur, colpos, word = self.getLeftFunct(win)
                            tip = '\n'.join(win.tooltips.get(word, []))
                            if tip:
                                win.CallTipShow(win.GetCurrentPos(),tip)
                        elif win.showautocomp and bool(win.kw) and (not win.AutoCompActive()) and (ord('A') <= key) and (key <= ord('Z')):
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
    def __init__(self, notebook, ID, parent):
        wxStyledTextCtrl.__init__(self, parent, ID)#, style = wxNO_FULL_REPAINT_ON_RESIZE)
        self.SetWordChars('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
        self.SetEndAtLastLine(False)
        self.cached = None
        self.MarkerDefine(BOOKMARKNUMBER, BOOKMARKSYMBOL, 'blue', 'blue')

        _, flags = CARET_OPTION_TO_ID[caret_option]
        self.SetXCaretPolicy(flags, caret_slop*caret_multiplier)
        self.SetYCaretPolicy(flags, caret_slop)

        self.tree1 = hierCodeTreePanel(notebook.root, notebook.root.leftt)
        self.tree1.Hide()
        self.tree1.tree.SORTTREE = 0
        self.tree1.parent.sizer.Layout()
        self.tree2 = hierCodeTreePanel(notebook.root, notebook.root.rightt)
        self.tree2.Hide()
        self.tree2.tree.SORTTREE = 1
        self.tree1.parent.sizer.Layout()

        self.hierarchy = []
        self.kw = []
        self.tooltips = {}
        self.ignore = {}

        self.parent = parent
        self.notebook = notebook #should also be equal to self.parent.parent
        self.root = self.notebook.root
        self.dirty = 0
        self.refresh = 0
        self.lexer = 'text'

        #Text is included in the original, but who drags text?  Below for dnd file support.
        if dnd_file: self.SetDropTarget(FileDropTarget(self.root))

        #for command comlpetion
        self.SetKeyWords(0, " ".join(keyword.kwlist))

        self.SetMargins(0,0)
        self.SetViewWhiteSpace(False)
        self.SetBackSpaceUnIndents(1)
        #self.SetBufferedDraw(False)
        #self.SetViewEOL(True)

        self.SetMarginType(0, wxSTC_MARGIN_NUMBER)
        #self.StyleSetSpec(wxSTC_STYLE_LINENUMBER, "size:%(size)d,face:%(mono)s" % faces)

        # Setup a margin to hold fold markers
        #I agree, what is this value?
        #self.SetFoldFlags(16)  ###  WHAT IS THIS VALUE?  WHAT ARE THE OTHER FLAGS?  DOES IT MATTER?

        self.SetProperty("fold", "1")
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


        # Make some styles,  The lexer defines what each style is used for, we
        # just have to define what each style looks like.  This set is adapted from
        # Scintilla sample property files.

        #And good wxPython users who have seen some demos know the above was copied
        #and pasted, along with a lot of sample code, right out of the demo.  The
        #demo r0XX0rs.

        # Global default styles for all languages
        self.StyleSetSpec(wxSTC_STYLE_DEFAULT,     "fore:#000000,face:%(mono)s,back:#FFFFFF,size:%(size)d" % faces)
        self.StyleSetSpec(wxSTC_STYLE_LINENUMBER,  "back:#C0C0C0,face:Lucida Console,size:%(size2)d" % faces)
        self.StyleSetSpec(wxSTC_STYLE_CONTROLCHAR, "face:%(other)s" % faces)
        self.StyleSetSpec(wxSTC_STYLE_BRACELIGHT,  "fore:#003000,face:%(mono)s,back:#80E0E0"% faces)
        self.StyleSetSpec(wxSTC_STYLE_BRACEBAD,    "fore:#E0FFE0,face:%(mono)s,back:#FF0000"% faces)

        #various settings
        self.SetSelBackground(1, '#B0B0FF')

        #again, some state variables
        self.filename = ''
        self.dirname = ''
        self.opened = 0
        self.AutoCompStops(' .,;:()[]{}\'"\\<>%^&+-=*/|`')

        EVT_STC_UPDATEUI(self,    ID, self.OnUpdateUI)
        EVT_STC_MARGINCLICK(self, ID, self.OnMarginClick)
        EVT_KEY_DOWN(self, self.root.OnKeyPressed)
        #EVT_CHAR(self, self.root.OnKeyPressed)
        EVT_KEY_UP(self, self.key_up)

        EVT_STC_CHARADDED(self, ID, self.added)
        EVT_STC_CHANGE(self, ID, self.cha)
        #unavailable in 2.5.1.2, didn't work in previous versions of wxPython
        # EVT_STC_POSCHANGED(self, ID, self.pos)
        EVT_STC_SAVEPOINTREACHED(self, ID, self.MakeClean)
        EVT_STC_SAVEPOINTLEFT(self, ID, self.MakeDirty)
        self.SetModEventMask(wxSTC_MOD_INSERTTEXT|wxSTC_MOD_DELETETEXT|wxSTC_PERFORMED_USER|wxSTC_PERFORMED_UNDO|wxSTC_PERFORMED_REDO)

        if REM_SWAP:
            self.CmdKeyClear(ord('T'), wxSTC_SCMOD_CTRL)

        self.CmdKeyClear(ord('Z'), wxSTC_SCMOD_CTRL)
        self.CmdKeyClear(ord('Y'), wxSTC_SCMOD_CTRL)
        self.CmdKeyClear(ord('X'), wxSTC_SCMOD_CTRL)
        self.CmdKeyClear(ord('C'), wxSTC_SCMOD_CTRL)
        self.CmdKeyClear(ord('V'), wxSTC_SCMOD_CTRL)
        self.CmdKeyClear(ord('A'), wxSTC_SCMOD_CTRL)

    def pos(self, e):
        #print "position changed event"
        #for some reason I never get called
        self.pos_ch(e)

    def cha(self, e):
        #print "changed event"
        self.key_up(e)

    def save(self, e):
        #print "save reached"
        self.key_up(e)

    def savel(self, e):
        #print "save left"
        self.key_up(e)

    def key_up(self, e):
        if self.GetModify(): self.MakeDirty()
        else:                self.MakeClean()
        self.pos_ch(e)
        #e.Skip()
    
    def pos_ch(self, e):
        if self.root.control.GetCurrentPage() == self.GetParent():
            lin = self.GetCurrentLine()+1
            col = self.GetColumn(self.GetCurrentPos())
            self.root.SetStatusText("L%i C%i"%(lin, col), 1)
        if e:
            e.Skip()

    def added(self, e):
        try:
            full = e is None
            tr = self.triggers
            c = 0
            gcp = self.GetCurrentPos()
            for p in xrange(gcp-1, -1, -1):
                if not full and p < gcp-1:
                    break
                ch = self.GetCharAt(p)
                if UNICODE:
                    ch = (chr((ch>>8)&255)+chr(ch&255)).decode('utf-16-be')
                else:
                    ch = chr(ch)
                c += 1
                tr = tr.get(ch, None)
                if tr is None:
                    ## print "ran off of triggers!", ch, gcp-p-1
                    break
                elif type(tr) is tuple:
                    self.SetSelection(p, p+c)
                    self.ReplaceSelection(tr[0])
                    p += len(tr[0])
                    self.SetSelection(p,p)
                    self.InsertText(p, tr[1])
                    break
        finally:
            self.key_up(e)
    
    def jump(self, direction):
        #1 forward, -1 backward
        if direction not in (1,-1):
            return

        #set up characters
        chars2, chars3 = '({[:,\'"', ')}]\'"'
        if self.GetLexer() in (wxSTC_LEX_HTML, wxSTC_LEX_XML):
            chars2 = chars2 + '>'
            chars3 = chars3 + '<'
        #chars2 are things that we want to be to the right of
        #chars3 are things that we want to be to the left of
        chars1 = chars2 + chars3
        
        #cursor position information
        linenum = self.GetCurrentLine()
        pos = self.GetCurrentPos()
        
        #iterator setup
        if direction == 1:
            it = xrange(pos, self.GetTextLength())
        else:
            it = xrange(pos-1, -1, -1)
        
        #updates information cross-lines
        for p in it:
            ch = self.GetTextRange(p, p+1)
            if ch not in chars1:
                continue
            
            if direction == 1: #if we are heading to the right
                #if we want to be to the right of line[p], make it so
                if ch in chars2:
                    p += 1
                    break
                #else if this character is just to the right of where we are at, skip it
                elif p == pos:
                    continue
                #else if we want to be to the left of line[p], make it so
                elif ch in chars3:
                    break
            else: #else we are heading to the left
                #if we want to be to the left of line[p], make it so
                if ch in chars3:
                    break
                #else if this character is just to the left of where we are at, skip it
                elif p == pos-1:
                    continue
                #else if we want to be to the right of line[p], make it so
                elif ch in chars2:
                    p += 1
                    break
            
        else:
            return
        self.SetSelection(p, p)

#------------------------- persistant document state -------------------------
    def GetSaveState(self):
        BM = []
        FOLD = []
        if self.GetParent().IsSplit():
            self.GetParent().GetWindow2().savePreferences()
        ret =  {'BM':BM,
                'FOLD':FOLD,
                'use_tabs':self.GetUseTabs(),
                'spaces_per_tab':self.GetTabWidth(),
                'indent':self.GetIndent(),
                'marker_margin':bool(self.GetMarginWidth(1)),
                'line_margin':bool(self.GetMarginWidth(0)),
                'col_line':self.GetEdgeColumn(),
                'col_mode':self.GetEdgeMode(),
                'indent_guide':self.GetIndentationGuides(),
                'showautocomp':self.showautocomp,
                'wrapmode':self.GetWrapMode(),
                ## 'sortmode':self.tree.tree.SORTTREE,
                'save_cursor':self.save_cursor,
                'cursor_posn':self.GetCurrentPos(),
                'findbarprefs':self.findbarprefs,
                'triggers':self.triggers,
                'whitespace':self.GetViewWhiteSpace(),
               }
        for line in xrange(self.GetLineCount()):
            if self.MarkerGet(line) & BOOKMARKMASK:
                BM.append(line)

            if (self.GetFoldLevel(line) & wxSTC_FOLDLEVELHEADERFLAG) and\
            (not self.GetFoldExpanded(line)):
                FOLD.append(line)
        FOLD.reverse()
        return ret

    def SetSaveState(self, saved):
        self.SetUseTabs(saved['use_tabs'])
        self.SetProperty("tab.timmy.whinge.level", "10"[bool(saved['use_tabs'])])
        self.SetTabWidth(saved['spaces_per_tab'])
        self.SetIndent(saved['indent'])
        self.SetMarginWidth(0, 40*saved['line_margin'])
        self.SetMarginWidth(1, 16*saved['marker_margin'])
        self.SetEdgeColumn(saved['col_line'])
        self.SetEdgeMode(saved['col_mode'])
        self.SetIndentationGuides(saved['indent_guide'])
        self.showautocomp = saved['showautocomp']
        self.findbarprefs = dict(saved.get('findbarprefs', {}))
        self.triggers = dict(saved['triggers'])
        if self.GetWrapMode() != saved['wrapmode']:
            self.root.WrapToggle(self)
        ## self.tree.tree.SORTTREE = saved.get('sortmode', sortmode)
        self.save_cursor = saved['save_cursor']
        for bml in saved.get('BM', []):
            self.MarkerAdd(bml, BOOKMARKNUMBER)
        for exl in saved.get('FOLD', []):
            a = self.GetLastChild(exl, -1)
            self.HideLines(exl+1,a)
            self.SetFoldExpanded(exl, 0)

        try: wxYield()
        except: pass

        if self.save_cursor:
            a = saved.get('cursor_posn', 0)
            self.SetSelection(a,a)
            self.EnsureCaretVisible()
            self.ScrollToColumn(0)

#-------------------- fix for SetText for the 'dirty bit' --------------------
    def SetText(self, txt, emptyundo=1):
        self.SetEOLMode(fmt_mode[self.format])
        self.enc = 'ascii'
        if UNICODE:
            for bom, enc in BOM:
                if txt[:len(bom)] == bom:
                    self.enc = enc
                    txt = txt[len(bom):]
                    #print "chose", enc
                    break
            if self.enc == 'ascii':
                twolines = txt.split(self.format, 2)[:2]
                for line in twolines:
                    x = re.search('coding[=:]\s*([-\w.]+)', line)
                    if not x:
                        continue
                    x = x.group(1).lower()
                    if x in ADDBOM:
                        self.enc = x
                        break
                    else:
                        self.enc = 'other'
                        try:
                            txt = txt.decode(x)
                        except Exception, why:
                            self.root.dialog(('''\
                                You have used %r as your encoding
                                declaration, but PyPE was unable to decode
                                your document due to:
                                %s
                                PyPE will load your document as ASCII.
                                Depending on the content of your file, this
                                may cause data loss if you save the opened
                                version.  You do so at your own risk, and
                                have now been warned.'''%(x, why)).replace(32*' ', ''),
                                "%r decoding error"%why)
                            self.enc = 'ascii'
                        break
            if self.enc not in ('ascii', 'other'):
                try:
                    txt = txt.decode(self.enc)
                except Exception, why:
                    #print "failed text decoding"
                    self.root.dialog(('''\
                        There has been a unicode decoding error:
                        %s
                        To prevent loss or corruption of data, it
                        is suggested that you close the document,
                        do not save.  Then try to open the document
                        with the application you originally created
                        it with.  If PyPE was the original creator,
                        and only editor of the document, please
                        contact the author and submit a bug report.'''%(why)).replace(24*' ', ''),
                        "Unicode decoding error.")
                    self.enc = 'ascii'
        wxStyledTextCtrl.SetText(self, txt)
        self.ConvertEOLs(fmt_mode[self.format])
        self.opened = 1
        if emptyundo:
            self.EmptyUndoBuffer()
            self.SetSavePoint()

    def GetText(self):
        self.ConvertEOLs(fmt_mode[self.format])
        if UNICODE:
            if self.enc == 'other':
                txt = wxStyledTextCtrl.GetText(self)
                twolines = txt.split(self.format, 2)[:2]
                x = None
                #pull the encoding
                for line in twolines:
                    x = re.search('coding[=:]\s*([-\w.]+)', line)
                    if not x:
                        continue
                    x = str(x.group(1).lower())
                    break
                #try the encoding, ascii, then utf-8 in that order
                why = None
                for i in [j for j in (x, 'ascii', 'utf-8') if j]:
                    try:
                        txt = txt.encode(i)
                    except UnicodeEncodeError, wh:
                        if why is None:
                            why = wh
                    else:
                        if x != None and x != i:
                            y = os.path.join(self.dirname, self.filename)
                            if self.root.dialog(('''\
                                    While trying to save the file named:
                                        %s
                                    PyPE was not able to encode the file as specified in the encoding declaration as:
                                        %r
                                    Due to:
                                        %s
                                    Would it be all right for PyPE to instead use %r as an encoding?
                                    '''%(y, x, why, i)).replace(36*' ', ''),
                                    "Continue with alternate encoding?", wxYES_NO) != wxID_YES:
                                raise cancelled
                            self.root.SetStatusText("Using %r encoding for %s"%(i, y))
                        return ADDBOM.get(i, '') + txt
            if self.enc == 'ascii':
                try:
                    return wxStyledTextCtrl.GetText(self).encode(self.enc)
                except:
                    #Previously non-unicode ascii file has had unicode characters
                    #inserted.  Must encode into some sort of unicode format.
                    #I choose you, utf-8!
                    self.enc = 'utf-8'
                    self.root.SetStatusText(self.enc, 2)
                    if self.root.HAS_RADIO:
                        self.root.menubar.Check(ENCODINGS[self.enc], 1)
            return ADDBOM.get(self.enc, '') + wxStyledTextCtrl.GetText(self).encode(self.enc)
        return wxStyledTextCtrl.GetText(self)

#----- Takes care of the little '*' modified next to the open file name ------
    def MakeDirty(self, e=None):
        if (not self.dirty) and self.opened:
            self.dirty = 1
            f = self.filename
            if f == ' ':
                f = '<untitled %i>'%self.NEWDOCUMENT
            c = 0
            for i in self.notebook:
                if i == self:
                    break
                c += 1
            self.notebook.SetPageText(c, '* '+f)
            self.root.redrawvisible(self)
        if e:
            e.Skip()

    def MakeClean(self, e=None):
        if self.dirty:
            self.dirty = 0
            f = self.filename
            if f == ' ':
                f = '<untitled %i>'%self.NEWDOCUMENT
            c = 0
            for i in self.notebook:
                if i == self:
                    break
                c += 1
            self.notebook.SetPageText(c, f)
            self.SetSavePoint()
            self.root.redrawvisible(self)
        if e:
            e.Skip()


    def nada(self, e):
        pass

    def do(self, funct, dirty=1):
        if dirty: self.MakeDirty(None)
        funct(self)
        self.root.redrawvisible(self)

    def Cut(self):      self.do(wxStyledTextCtrl.Cut)
    def Paste(self):    self.do(wxStyledTextCtrl.Paste)
    def DeleteSelection(self):   self.do(wxStyledTextCtrl.DeleteBack)
    def Undo(self):     self.do(wxStyledTextCtrl.Undo)
    def Redo(self):     self.do(wxStyledTextCtrl.Redo)

#--------- Ahh, the style change code...isn't it great?  Not really. ---------
    def changeStyle(self, stylefile, language):
        try:
            #from StyleSupport import initSTC
            ## from STCStyleEditor import initSTC
            from StyleSetter import initSTC
            initSTC(self, stylefile, language)
            ## self.SetLexer(wxSTC_LEX_NULL)
            self.lexer = language
        except:
            
            #self.root.exceptDialog("Style Change failed, assuming plain text")
            self.root.SetStatusText("Style Change failed for %s, assuming plain text"%language)
            self.root.exceptDialog()
#----------------- Defaults, in case the other code was bad. -----------------
            #for some default font styles

            self.SetLexer(wxSTC_LEX_NULL)
            self.lexer = 'text'

            ### Python styles
            ##
            ### White space
            ##self.StyleSetSpec(wxSTC_P_DEFAULT, "fore:#000000,face:%(helv)s,size:%(size)d" % faces)
            ### Comment
            ##self.StyleSetSpec(wxSTC_P_COMMENTLINE, "fore:#007F00,face:%(mono)s,back:#E0FFE0,size:%(size)d" % faces)
            ### Number
            ##self.StyleSetSpec(wxSTC_P_NUMBER, "fore:#007F7F,face:%(times)s,size:%(size)d" % faces)
            ### String
            ##self.StyleSetSpec(wxSTC_P_STRING, "fore:#7F007F,face:%(times)s,size:%(size)d" % faces)
            ### Single quoted string
            ##self.StyleSetSpec(wxSTC_P_CHARACTER, "fore:#7F007F,face:%(times)s,size:%(size)d" % faces)
            ### Keyword
            ##self.StyleSetSpec(wxSTC_P_WORD, "fore:#F0B000,face:%(mono)s,size:%(size)d,bold" % faces)
            ### Triple quotes
            ##self.StyleSetSpec(wxSTC_P_TRIPLE, "fore:#603000,face:%(times)s,back:#FFFFE0,size:%(size)d" % faces)
            ### Triple double quotes
            ##self.StyleSetSpec(wxSTC_P_TRIPLEDOUBLE, "fore:#603000,face:%(times)s,back:#FFFFE0,size:%(size)d" % faces)
            ### Class name definition
            ##self.StyleSetSpec(wxSTC_P_CLASSNAME, "fore:#0000FF,face:%(times)s,size:%(size)d,bold" % faces)
            ### Function or method name definition
            ##self.StyleSetSpec(wxSTC_P_DEFNAME, "fore:#0000FF,face:%(times)s,size:%(size)d,bold" % faces)
            ### Operators
            ##self.StyleSetSpec(wxSTC_P_OPERATOR, "face:%(times)s,size:%(size)d" % faces)
            ### Identifiers
            ##self.StyleSetSpec(wxSTC_P_IDENTIFIER, "fore:#000000,face:%(helv)s,size:%(size)d" % faces)
            ### Comment-blocks
            ##self.StyleSetSpec(wxSTC_P_COMMENTBLOCK, "fore:#7F7F7F,face:%(times)s,size:%(size)d" % faces)
            ### End of line where string is not closed
            ##self.StyleSetSpec(wxSTC_P_STRINGEOL, "fore:#000000,face:%(mono)s,back:#E0C0E0,eol,size:%(size)d" % faces)
            ##
            ##self.SetCaretForeground("BLACK")
            ##
            ### prototype for registering some images for use in the AutoComplete box.
            ###self.RegisterImage(1, images.getSmilesBitmap())

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
    def CanEdit(self):
        return 1

#-------------- end of copied code from wxStyledTextCtrl_2 demo --------------
#(really I copied alot more, but that part I didn't modify at all, I
#wanted to understand it, but it just worked, so there was no need)

#------------------------- Ahh, the tabbed notebook --------------------------
class MyNB(wxNotebook):
    def __init__(self, root, id, parent):
        #the left-tab, while being nice, turns the text sideways, ick.
        wxNotebook.__init__(self, parent, id, style=
                            wxNB_TOP
                            #wxNB_BOTTOM
                            #wxNB_LEFT
                            #wxNB_RIGHT
                            )

        self.root = root
        self.AssignImageList(IMGLIST2)

        #for some reason, the notebook needs the next line...the text control
        #doesn't.
        EVT_KEY_DOWN(self, self.root.OnKeyPressed)
        EVT_NOTEBOOK_PAGE_CHANGED(self, self.GetId(), self.OnPageChanged)
        self.SetDropTarget(FileDropTarget(self.root))
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
                owin.tree1.Hide()
                owin.tree2.Hide()
            if new > -1:
                self.root.dragger._SelectItem(new)
                win = self.GetPage(new).GetWindow1()
                #fix for dealing with current paths.
                
                if win.dirname:
                    try:
                        os.chdir(win.dirname)
                    except:
                        pass
                self.updateChecks(win)
                #width = self.GetClientSize()[0]
                #split = win.parent
                #if win.GetWrapMode() == wxSTC_WRAP_NONE:
                #    self.parent.SetStatusText("", 1)
                #else:
                #    self.parent.SetStatusText("WRAP",1)
                self.root.OnDocumentChange(win, None)
                win.tree1.Show()
                win.tree2.Show()

                _, flags = CARET_OPTION_TO_ID[caret_option]
                win.SetXCaretPolicy(flags, caret_slop*caret_multiplier)
                win.SetYCaretPolicy(flags, caret_slop)

            self.root.timer.Start(10, wxTIMER_ONE_SHOT)
            if event:
                event.Skip()
            wxCallAfter(win.SetFocus)
            wxCallAfter(self.root.updateWindowTitle)
        finally:
            self.calling = 0
    
    def updateChecks(self, win):
        if UNICODE:
            self.root.SetStatusText(win.enc, 2)
            if self.root.HAS_RADIO:
                self.root.menubar.Check(ENCODINGS[win.enc], 1)
        if self.root.HAS_RADIO:
            self.root.menubar.Check(lexers2[win.lexer], 1)
            self.root.menubar.Check(LL_RMAPPING[win.GetEdgeMode()][1], 1)
        for m,cid in ((0, NUM), (1, MARGIN)):
            self.root.menubar.Check(cid, bool(win.GetMarginWidth(m)))
        self.root.menubar.Check(INDENTGUIDE, win.GetIndentationGuides())
        self.root.menubar.Check(USETABS, win.GetUseTabs())
        self.root.menubar.Check(AUTO, win.showautocomp)
        self.root.menubar.Check(WRAPL, win.GetWrapMode() != wxSTC_WRAP_NONE)
        self.root.menubar.Check(S_WHITE, win.GetViewWhiteSpace())
        ## self.root.menubar.Check(SORTBY, win.tree.tree.SORTTREE)
        self.root.menubar.Check(LE_RMAPPING[win.GetEOLMode()][1], 1)
        self.root.menubar.Check(SAVE_CURSOR, win.save_cursor)
        self.root.menubar.SetHelpString(IDR, "Indent region %i spaces"%win.GetIndent())
        self.root.menubar.SetHelpString(DDR, "Indent region %i spaces"%win.GetIndent())

#----------------- This deals with the tab swapping support. -----------------
    if 0:
        pass
    ## def swapPages(self, p1, p2, moveleft):
        ## mn = min(p1,p2)
        ## mx = max(p1,p2)
        ## if not (moveleft or (p1-p2==1)):
            ## mn, mx = mx, mn
        ## page = self.GetPage(mn)
        ## text = self.GetPageText(mn)[:]
        ## self.RemovePage(mn)
        ## self.InsertPage(mx, page, text, 1)

    def RemovePage(self, index):
        self.root.dragger._RemoveItem(index)
        wxNotebook.RemovePage(self, index)

    def DeletePage(self, index):
        self.root.dragger._RemoveItem(index)
        page = self.GetPage(index)
        stc = page.GetWindow1()
        stc.tree1.Hide()
        stc.tree1.Destroy()
        stc.tree2.Hide()
        stc.tree2.Destroy()
        wxNotebook.DeletePage(self, index)

    def AddPage(self, page, text, switch=0):
        which = EXT_TO_IMG.get(extns.get(text.split('.')[-1].lower(), 0), 0)
        self.root.dragger._AddItem(text)
        wxNotebook.AddPage(self, page, text, switch, which)
        if switch or self.GetPageCount() == 1:
            ## self.root.OnDocumentChange(page.GetWindow1())
            self.root.dragger._SelectItem(self.GetPageCount()-1)

    def InsertPage(self, posn, page, text, switch=0):
        which = EXT_TO_IMG.get(extns.get(text.split('.')[-1].lower(), 0), 0)
        self.root.dragger._InsertItem(posn, text)
        wxNotebook.InsertPage(self, posn, page, text, switch, which)
        if self.GetSelection() == posn:
            self.root.OnDocumentChange(page.GetWindow1())
        
    def SetPageText(self, posn, text):
        self.root.dragger._RenameItem(posn, text)
        wxNotebook.SetPageText(self, posn, text)

class MyLC(wxTreeCtrl):
    class FileDropTarget(wxFileDropTarget):
        def __init__(self, parent, root):
            wxFileDropTarget.__init__(self)
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

            if i == -1:
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
        tID = wxNewId()
        wxTreeCtrl.__init__(self, parent, tID, style=wxTR_HIDE_ROOT|\
                            wxTR_NO_LINES|wxTR_NO_BUTTONS)

        self.root = root
        self.rootnode = self.AddRoot("Unseen Root")
        self.SetDropTarget(self.FileDropTarget(self, root))
        self.AssignImageList(IMGLIST1)

        ## EVT_TREE_ITEM_ACTIVATED(self, tID, self.OnTreeItemActivated)
        EVT_TREE_BEGIN_DRAG(self, tID, self.OnTreeBeginDrag)
        EVT_TREE_SEL_CHANGED(self, tID, self.OnTreeSelectionChanged)

    def getAllRectangles(self):
        count = self.GetChildrenCount(self.rootnode)
        lst = []
        while len(lst) < count:
            if len(lst) == 0:
                (item, cookie) = self.GetFirstChild(self.rootnode)
            else:
                (item, cookie) = self.GetNextChild(self.rootnode, cookie)
            lst.append((item, self.GetBoundingRect(item)))
        return lst

    def OnTreeItemActivated(self, event):
        item = event.GetItem()
        lst = self.getAllRectangles()
        posn = -1
        for i, (itemi, toss) in enumerate(lst):
            if item == itemi:
                posn = i
                break

        if posn == -1:
            print "BAH2!"
            event.Skip()

        self.root.control.SetSelection(posn)

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

        a = self.root.control.GetPage(posn).GetWindow1()
        data = os.path.join(a.dirname, a.filename).encode('ascii')
        if data == ' ':
            data = '<untitled %i>'%a.NEWDOCUMENT
        d = wxFileDataObject()
        d.AddFile(data)
        ## print d.GetFilenames()
        a = wxDropSource(self)
        a.SetData(d)
        a.DoDragDrop(wxDrag_AllowMove|wxDrag_CopyOnly)

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
        which = EXT_TO_IMG.get(extns.get(label.split('.')[-1].lower(), 0), 0)
        self.AppendItem(self.rootnode, label, which)

    def _InsertItem(self, index, label):
        if index == self.GetChildrenCount(self.rootnode, False):
            self._AddItem(label)
        else:
            which = EXT_TO_IMG.get(extns.get(label.split('.')[-1].lower(), 0), 0)
            self.InsertItemBefore(self.rootnode, index, label, which)

    def _SelectItem(self, index):
        chlist = self.getAllRectangles()
        if index < len(chlist):
            self.SelectItem(chlist[index][0])
        
    def _RenameItem(self, index, label):
        self.SetItemText(self.getAllRectangles()[index][0], label)

class FileDropTarget(wxFileDropTarget):
    def __init__(self, root):
        wxFileDropTarget.__init__(self)
        self.root = root
    def OnDropFiles(self, x, y, filenames):
        self.root.OnDrop(filenames)

class TextDropTarget(wxTextDropTarget):
    def __init__(self, parent):
        wxTextDropTarget.__init__(self)
        self.parent = parent

    def OnDropText(self, x, y, text):
        self.parent.OnDropText(text)
        #This is so that you can keep your document unchanged while adding
        #code snippets.
        return False

#I use a tree control embedded in a panel so that the control expands to
#use the full amount of space.
class hierCodeTreePanel(wxPanel):
    class TreeCtrl(wxTreeCtrl):
        def __init__(self, parent, tid):
            wxTreeCtrl.__init__(self, parent, tid, style=wxTR_DEFAULT_STYLE|wxTR_HAS_BUTTONS|wxTR_HIDE_ROOT)

            isz = (16,16)
            il = wxImageList(isz[0], isz[1])
            self.images = [wxArtProvider_GetBitmap(wxART_FOLDER, wxART_OTHER, isz),
                           wxArtProvider_GetBitmap(wxART_FILE_OPEN, wxART_OTHER, isz),
                           wxArtProvider_GetBitmap(wxART_NORMAL_FILE, wxART_OTHER, isz)]
            for i in self.images:
                il.Add(i)
            self.SetImageList(il)
            self.il = il

        def OnCompareItems(self, item1, item2):
            if self.SORTTREE:
                return cmp(self.GetItemData(item1).GetData(),\
                           self.GetItemData(item2).GetData())
            else:
                return cmp(self.GetItemData(item1).GetData()[1],\
                           self.GetItemData(item2).GetData()[1])

    def __init__(self, root, parent):
        # Use the WANTS_CHARS style so the panel doesn't eat the Return key.
        wxPanel.__init__(self, parent, -1, style=wxWANTS_CHARS)
        self.parent = parent
        EVT_SIZE(self, self.OnSize)

        self.root = root

        tID = wxNewId()

        self.tree = self.TreeCtrl(self, tID)
        self.tree.troot = self.tree.AddRoot("Unseen Root")

        #self.tree.Expand(self.root)
        EVT_LEFT_DCLICK(self, self.OnLeftDClick)
        EVT_TREE_ITEM_ACTIVATED(self, tID, self.OnActivate)

    def new_hierarchy(self, hier):
        self.tree.DeleteAllItems()
        root = [self.tree.troot]
        stk = [hier[:]]
        blue = wxColour(0, 0, 200)
        red = wxColour(200, 0, 0)
        green = wxColour(0, 200, 0)
        D = {'cl':blue,
             'de':red,
             'cd':green,
             '\\l':red,
             '\\s':blue}
        while stk:
            cur = stk.pop()
            while cur:
                name, line_no, leading, children = cur.pop()
                item_no = self.tree.AppendItem(root[-1], name)
                self.tree.SetPyData(item_no, line_no)
                self.tree.SetItemTextColour(item_no, D.get(name[:2], blue))
                icons = 1
                if children:
                    if icons:
                        self.tree.SetItemImage(item_no, 0, wxTreeItemIcon_Normal)
                        self.tree.SetItemImage(item_no, 1, wxTreeItemIcon_Expanded)
                    stk.append(cur)
                    root.append(item_no)
                    cur = children[:]
                elif icons:
                    self.tree.SetItemImage(item_no, 2, wxTreeItemIcon_Normal)
                    self.tree.SetItemImage(item_no, 2, wxTreeItemIcon_Selected)
            self.tree.SortChildren(root[-1])
            root.pop()

    def OnSize(self, event):
        w,h = self.parent.GetClientSizeTuple()
        self.tree.SetDimensions(0, 0, w, h)
        self.parent.sizer.Layout()

    def OnLeftDClick(self, event):
        #pity this doesn't do what it should.
        num, win = self.root.getNumWin(event)
        win.SetFocus()

    def OnActivate(self, event):
        num, win = self.root.getNumWin(event)
        dat = self.tree.GetItemData(event.GetItem()).GetData()
        if dat == None:
            return event.Skip()
        ln = dat[1]-1
        #print ln
        #print dir(win)
        linepos = win.GetLineEndPosition(ln)
        win.EnsureVisible(ln)
        win.SetSelection(linepos-len(win.GetLine(ln))+len(win.format), linepos)
        win.ScrollToColumn(0)
        win.SetFocus()

    def Show(self):
        wxPanel.Show(self, True)
        try:
            self.parent.sizer.Add(self)
        except:
            pass
        self.OnSize(None)
    def Hide(self):
        wxPanel.Hide(self)
        try:
            self.parent.sizer.Detach(self)
        except:
            pass

class TriggerDialog(wxDialog):
    class TriggerListCtrl(wxListCtrl, wxTextEditMixin):
        pass
    def __init__(self, parent, stc, dct):
        wxDialog.__init__(self, parent, -1, "Set your Triggers",
                          style=wxDEFAULT_DIALOG_STYLE|wxRESIZE_BORDER,
                          size=(800, 400))
        self.stc = stc
        self.parent = parent
        self.dct = dct
        EVT_CLOSE(self, self.OnClose)
        
        def addbutton(sizer, name, fcn, id):
            it = wxButton(self, id, name)
            sizer.Add(it, 0, wxRIGHT, border=5)
            EVT_BUTTON(self, id, fcn)
        
        
        sizer = wxBoxSizer(wxVERTICAL)
        
        #description/help text
        sizer.Add(wxStaticText(self, -1, '''\
                                When editing a document, any time you type the string in the 'enter' column,
                                the string in the 'left' column replaces it, and the string in the 'right'
                                column is inserted to the right of the cursor.
                                
                                See the help for example uses.
                                
                                One may want to use such functionality for single or double quotes: '', ""
                                parens or square/curly/pointy braces: (), [], {}, <>
                                or even html tag expansion: ahref->"<a href='http://", "'></a>"
                                
                                Double-click to edit an entry in-place.
                                
                                If one entry in the 'enter' column is a suffix of another, the suffix item
                                will be removed.  Watch the log for such entries.
                                
                                NOTE: If any of your entries begins with a single or double quote, and is a
                                valid Python string definition, then it will be interpreted as the string
                                defined (allowing for escaped tabs, line endings, unicode characters, etc.).'''.replace(32*' ', '')
                               ), 0, wxLEFT|wxRIGHT, border=5)
        
        #wxListCtrl with editor
        self.list = self.TriggerListCtrl(self, -1, style=wxLC_REPORT|wxBORDER_NONE)
        wxTextEditMixin.__init__(self.list)
        self.list.InsertColumn(0, "enter");self.list.SetColumnWidth(0, 160)
        self.list.InsertColumn(1, "left");self.list.SetColumnWidth(1, 80)
        self.list.InsertColumn(2, "right");self.list.SetColumnWidth(2, 80)
        self.ResetData(dct)
        
        sizer.Add(self.list, 2, flag=wxGROW|wxALL, border=5)
        
        buttons = wxBoxSizer(wxHORIZONTAL)
        #new/delete
        addbutton(buttons, "New Trigger", self.OnNew, wxNewId())
        addbutton(buttons, "Delete Trigger", self.OnDelete, wxNewId())
        buttons.Add(wxStaticText(self, -1, '     '), 1, wxGROW)
        #OK/cancel
        addbutton(buttons, "OK", self.OnOK, wxOK)
        addbutton(buttons, "Cancel", self.OnCancel, wxCANCEL)
        sizer.Add(buttons, 0, wxALIGN_CENTER|wxLEFT, border=5)
        
        sizer.Fit(self)
        self.SetSizer(sizer)

    def ResetData(self, data):
        def reconstruct(suf, x):
            if type(x) is tuple:
                yield suf, x[0], x[1]
            elif type(x) is dict:
                for key,value in x.iteritems():
                    for i,j,k in reconstruct(key+suf, value):
                        yield i,j,k
        
        self.list.DeleteAllItems()
        for x in reconstruct('', data):
            x_ = []
            for L in x:
                try:
                    L = str(L)
                except:
                    pass
                if not isinstance(L, unicode):
                    Lx = L.encode('string-escape')
                    if Lx != L:
                        L = repr(L)
                x_.append(L)
            i,j,k = x_
            indx = self.list.InsertStringItem(65536, 'X')
            self.list.SetStringItem(indx, 0, i)
            self.list.SetStringItem(indx, 1, j)
            self.list.SetStringItem(indx, 2, k)

    def OnNew(self, evt):
        index = self.list.InsertStringItem(65536, 'X')
        self.list.SetStringItem(index, 0, 'X')
        self.list.SetStringItem(index, 1, 'X')
        self.list.SetStringItem(index, 2, 'X')

    def OnDelete(self, evt):
        selected = self.list.GetNextItem(-1, state=wxLIST_STATE_SELECTED)
        if selected != -1:
            self.list.DeleteItem(selected)

    def OnClose(self, evt):
        self.OnCancel(evt)

    def OnOK(self, evt):
        d = {}
        for row in xrange(self.list.GetItemCount()):
            #handle string escapes
            item = [self.list.GetItem(row, 0).GetText(),
                    self.list.GetItem(row, 1).GetText(),
                    self.list.GetItem(row, 2).GetText()]
            item_ = []
            for i in item:
                if i and i[0] in ['"', "'"]:
                    try:
                        i = [j for j in compiler.parse(str(i)).getChildren()[:1] if isinstance(j, basestring)][0]
                    except Exception, e:
                        pass
                item_.append(i)
            
            p, l, r = item_
            
            if not p:
                if len(l) or len(r):
                    print "null trigger has nonnull replacements (%r, %r)"%(l,r)
                continue
            if len(l) + len(r) == 0:
                print "nonnull trigger %r has null replacements"%p
            pr = None
            x = d
            good = 1
            for le,ch in enumerate(p[::-1]):
                n = x.get(ch, None)
                if type(n) is tuple:
                    if p[-le-1:] == p:
                        print "duplicate trigger %r with replacements (%r, %r), and is now removed"%(p, l, r)
                        break
                    print "trigger %r with replacements (%r, %r) is a suffix of %r, and is now removed"%(p[-le-1:], n[0], n[1], p)
                    n = None
                
                if n is None:
                    n = x[ch] = {}
                
                pr, x = x, n
            else:
                if len(x) != 0:
                    print "trigger %r with replacements (%r, %r) is a suffix of some entry, and is now removed"%(p, l, r)
                    continue
                pr[p[0]] = (l,r)
        
        self.stc.triggers = d
        self.Destroy()

    def OnCancel(self, evt):
        self.Destroy()

class KeySink(wxWindow):
    def __init__(self, parent, defa, curr):
        wxWindow.__init__(self, parent, -1, style=wxWANTS_CHARS)
        self.SetBackgroundColour(wxBLUE)
        self.haveFocus = False
        self.defa = defa
        self.curr = curr


        EVT_PAINT(self, self.OnPaint)
        EVT_SET_FOCUS(self, self.OnSetFocus)
        EVT_KILL_FOCUS(self, self.OnKillFocus)
        EVT_MOUSE_EVENTS(self, self.OnMouse)
        EVT_KEY_DOWN(self, self.OnKey)

    def OnPaint(self, evt):
        dc = wxPaintDC(self)
        rect = self.GetClientRect()
        dc.SetTextForeground(wxWHITE)
        dc.DrawLabel("Click here and enter your key combination.\n"
                     "Default: %s  Current: %s"%(self.defa, self.curr),
                     rect, wxALIGN_CENTER | wxALIGN_TOP)
        if self.haveFocus:
            dc.SetTextForeground(wxGREEN)
            dc.DrawLabel("Have Focus", rect, wxALIGN_RIGHT | wxALIGN_BOTTOM)
        else:
            dc.SetTextForeground(wxRED)
            dc.DrawLabel("Need Focus!", rect, wxALIGN_RIGHT | wxALIGN_BOTTOM)

    def OnSetFocus(self, evt):
        self.haveFocus = True
        self.Refresh()

    def OnKillFocus(self, evt):
        self.haveFocus = False
        self.Refresh()

    def OnMouse(self, evt):
        if evt.ButtonDown():
            self.SetFocus()

    def OnKey(self, evt):
        self.GetParent().text.SetValue(GetKeyPress(evt))

class GetKeyDialog(wxDialog):
    def __init__(self, parent, defa, curr):
        wxDialog.__init__(self, parent, -1, "Enter key combination",
                          style=wxDEFAULT_DIALOG_STYLE|wxRESIZE_BORDER,
                          size=(320, 240))
        self.parent = parent

        self.keysink = KeySink(self, defa, curr)

        self.text = wxTextCtrl(self, -1, curr, style=wxTE_READONLY|wxTE_LEFT)

        buttons = wxBoxSizer(wxHORIZONTAL)
        ok = wxButton(self, wxOK, "OK")
        cancel = wxButton(self, wxCANCEL, "Cancel")
        buttons.Add(ok, 0)
        buttons.Add(cancel, 0)

        sizer = wxBoxSizer(wxVERTICAL)
        sizer.Add(self.keysink, 1, wxGROW)
        sizer.Add(self.text, 0, wxGROW)
        sizer.Add(buttons, 0, wxALIGN_RIGHT)

        self.SetSizer(sizer)
        EVT_BUTTON(self, wxOK, self.OnOK)
        EVT_BUTTON(self, wxCANCEL, self.OnCancel)
        EVT_CLOSE(self, self.OnClose)

    def OnClose(self, evt):
        self.OnCancel(evt)

    def OnOK(self, evt):
        self.parent.accelerator = self.text.GetValue()
        self.Destroy()

    def OnCancel(self, evt):
        self.parent.accelerator = ""
        self.Destroy()

class MenuItemDialog(wxDialog):
    class VirtualMenu(wxPanel):
        class virtualMenu(wxListCtrl, wxListCtrlAutoWidthMixin):
            def __init__(self, parent):
                wxListCtrl.__init__(self, parent, -1,
                                    style=wxLC_REPORT|wxLC_VIRTUAL|wxLC_HRULES|wxLC_VRULES|wxLC_SINGLE_SEL)
                wxListCtrlAutoWidthMixin.__init__(self)

                self.parent = parent
                self.sel = None

                self.InsertColumn(0, "Default Menu Hierarchy")
                self.InsertColumn(1, "Current Name")
                self.InsertColumn(2, "Default Hotkey")
                self.InsertColumn(3, "Current Hotkey")
                self.SetColumnWidth(0, 250)
                self.SetColumnWidth(1, 150)
                self.SetColumnWidth(2, 100)

                self.items = []
                self.SetItemCount(0)

                EVT_LIST_ITEM_SELECTED(self, self.GetId(), self.OnItemSelected)
                EVT_LIST_ITEM_ACTIVATED(self, self.GetId(), self.OnItemActivated)

            def OnItemActivated(self, event):
                inum = event.GetIndex()
                item = self.items[inum]
                dlg = wxTextEntryDialog(self,
                                        "Enter the new name of the menu item\n"\
                                        "Default: %s  Current: %s"%(item[0].split('->')[-1], item[1]),\
                                        "What should the item be called?")
                dlg.SetValue(item[1])
                rslt = dlg.ShowModal()
                if rslt == wxID_OK:
                    name = dlg.GetValue()
                else:
                    name = None
                dlg.Destroy()
                if not name:
                    return
                if item[0].find('->') == -1 or not item[4]:
                    self.items[inum] = (item[0], name, '', '', 0)
                    return self.RefreshItem(inum)
                
                dlg = GetKeyDialog(self, item[2], item[3])
                dlg.ShowModal()
                
                x = (item[0], name, item[2], self.accelerator, 1)
                if x[:-1] != self.items[inum][:4]:
                    self.items[inum] = x
                    self.RefreshItem(inum)

            def getColumnText(self, index, col):
                return self.items[index][col]

            def OnGetItemText(self, item, col):
                return self.items[item][col]

            def OnGetItemImage(self, item):
                return -1

            def OnGetItemAttr(self, item):
                return None

            def OnItemSelected(self, evt):
                self.sel = evt.GetIndex()

        def __init__(self, parent):
            wxPanel.__init__(self, parent, -1, style=wxWANTS_CHARS)
            self.vm = self.virtualMenu(self)
            self.refresh(MENULIST)

            self.parent = parent

            EVT_SIZE(self, self.OnSize)

        def refresh(self, items):
            self.vm.items = []
            self.vm.SetItemCount(0)
            self.vm.items = items
            self.vm.SetItemCount(len(items))
            if self.vm.sel is not None:
                self.vm.EnsureVisible(self.vm.sel)

        def OnSize(self, event):
            w,h = self.GetClientSizeTuple()
            self.vm.SetDimensions(0, 0, w, h)

    def __init__(self, parent, root):
        wxDialog.__init__(self, parent, -1, "Menu item names and hotkey bindings.",
                          size=(640,480), style=wxRESIZE_BORDER|wxDEFAULT_DIALOG_STYLE)

        self.root = root
        self.vmu = self.VirtualMenu(self)
        sizer = wxBoxSizer(wxVERTICAL)

        sizer.Add(wxStaticText(self, -1,
                               "Double click on an entry to change the name and/or hotkey.  Most any hotkey should work fine.  Give it a try.\n"
                               "Name changes with accelerators should work fine, as long as there are no accelerator key collisions."))
        sizer.Add(self.vmu, 1, wxGROW)

        s2 = wxBoxSizer(wxHORIZONTAL)

        ok = wxButton(self, wxOK, "OK")
        clear = wxButton(self, wxNewId(), "Clear Hotkey")
        revert = wxButton(self, wxNewId(), "Revert Name and Hotkey")
        cancel = wxButton(self, wxCANCEL, "Cancel")

        s2.Add(ok)
        s2.Add(clear)
        s2.Add(revert)
        s2.Add(cancel)
        sizer.Add(s2, 0, wxALIGN_RIGHT)

        self.SetSizer(sizer)
        self.SetAutoLayout(True)

        EVT_BUTTON(self, wxOK, self.OnOK)
        EVT_BUTTON(self, clear.GetId(), self.OnClear)
        EVT_BUTTON(self, revert.GetId(), self.OnRevert)
        EVT_BUTTON(self, wxCANCEL, self.OnCancel)

    def OnOK(self, evt):
        global MENUPREF
        global MENULIST
        nmu = {}
        changed = 0
        for hier, cn, da, ca, hk in self.vmu.vm.items:
            if MENUPREF[hier] != (cn, ca):
                changed = 1
            nmu[hier] = (cn, ca)
        if changed:
            MENUPREF.clear()
            MENUPREF.update(nmu)
            MENULIST[:] = self.vmu.vm.items
            self.root.dialog("You must restart in order for your\n"
                             "menu item changes to go into effect.",
                             "Restart Required")
        self.Destroy()

    def OnClear(self, evt):
        IL = self.vmu.vm
        items = IL.items
        indx = IL.sel
        items[indx] = items[indx][:3] + ('', items[indx][4])
        IL.RefreshItem(indx)

    def OnRevert(self, evt):
        IL = self.vmu.vm
        items = IL.items
        indx = IL.sel
        item = items[indx]
        items[indx] = (item[0], item[0].split('->')[-1], item[2], item[2], item[4])
        IL.RefreshItem(indx)

    def OnCancel(self, evt):
        self.Destroy()


class SplitterWindow(wxSplitterWindow):
    if 1:
        swap = 0
    def SplitVertically(self, win1, win2, sashPosition=0, swap=0):
        self.swap = swap
        if swap:
            win1, win2, sashPosition = win2, win1, -sashPosition
        wxSplitterWindow.SplitVertically(self, win1, win2, sashPosition)
    def SplitHorizontally(self, win1, win2, sashPosition=0, swap=0):
        self.swap = swap
        if swap:
            win1, win2, sashPosition = win2, win1, -sashPosition
        wxSplitterWindow.SplitHorizontally(self, win1, win2, sashPosition)
    def Unsplit(self, which=None):
        if which is None:
            which = self.GetWindow2()
        wxSplitterWindow.Unsplit(self, which)
        self.swap = 0
    def GetWindow1(self):
        if self.IsSplit() and self.swap:
            x = wxSplitterWindow.GetWindow2(self)
        else:
            x = wxSplitterWindow.GetWindow1(self)
        return x
    def GetWindow2(self):
        if self.IsSplit() and self.swap:
            x = wxSplitterWindow.GetWindow1(self)
        else:
            x = wxSplitterWindow.GetWindow2(self)
        return x
    def SetSashPosition(self, position, redraw = 1):
        if self.swap:
            position = -position
        return wxSplitterWindow.SetSashPosition(self, position, redraw)

#--------------------------- And the main...*sigh* ---------------------------
import wx
VS = wx.VERSION_STRING
del wx

def main():
    if single_instance.send_documents(
    [os.path.abspath(os.path.join(os.getcwd(), i))
    for i in sys.argv[1:] if i != '--last']):
        return
    
    global IMGLIST1, IMGLIST2, root
    app = wxPySimpleApp()
    IMGLIST1 = wxImageList(16, 16)
    IMGLIST2 = wxImageList(16, 16)
    for il in (IMGLIST1, IMGLIST2):
        for icf in ('icons/blank.ico', 'icons/py.ico'):
            img = wxImageFromBitmap(wxBitmap(icf)) 
            img.Rescale(16,16) 
            bmp = wxBitmapFromImage(img) 
            il.AddIcon(wxIconFromBitmap(bmp)) 

    opn=0
    if len(sys.argv)>1 and (sys.argv[1] == '--last'):
        opn=1
    filehistory.root = root = app.frame = MainWindow(None, -1, "PyPE", sys.argv[1+opn:])
    root.updateWindowTitle()
    app.SetTopWindow(app.frame)
    app.frame.Show(1)
    if opn:
        app.frame.OnOpenPrevDocs(None)
    app.frame.SendSizeEvent()
    app.MainLoop()

if __name__ == '__main__':
    main()
