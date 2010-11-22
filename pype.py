#!/usr/bin/env python

#------------ User-changable settings are available in the menus -------------
from __future__ import generators
from __version__ import *

#------------------------ Startup/restart information ------------------------
import sys, os
if sys.platform == 'linux2' and 'DISPLAY' not in os.environ:
    raise SystemError('DISPLAY not set when importing or running pype')

if not hasattr(sys, 'frozen'):
    v = '2.6'
    import wxversion
    if '--unicode' in sys.argv:
        wxversion.ensureMinimal(v+'-unicode', optionsRequired=True)
    elif '--ansi' in sys.argv:
        wxversion.ensureMinimal(v+'-ansi', optionsRequired=True)
    else:
        wxversion.ensureMinimal(v)
DEBUG = '--debug' in sys.argv
USE_THREAD = '--nothread' not in sys.argv

PRINTMACROS = 0

def _restart(orig_path=os.getcwd(), orig_sysargv=sys.argv[:]):
    os.chdir(orig_path)
    args = [sys.executable] + orig_sysargv
    if len(spawnargs) == 1:
        _ = args.pop(0)
    
    os.execvp(args[0], args + ['--last'])

sys.argv = [i for i in sys.argv if i not in ('--ansi', '--unicode', '--debug', '--nothread', '--macros')]

#-------------- Create reference to this module in __builtins__ --------------
if isinstance(__builtins__, dict):
    __builtins__['_pype'] = sys.modules[__name__]
else:
    __builtins__._pype = sys.modules[__name__]
#------------------------------ System Imports -------------------------------
import stat
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
import Queue
import threading
import wx
import wx.gizmos
if DEBUG:
    from wx.py import crust

current_path = os.getcwd()
EFFECTUAL_NORMCASE = os.path.normcase('AbCdEf') == 'abcdef'
UNICODE = wxUSE_UNICODE

#--------------------------- configuration import ----------------------------
from configuration import *

#---------------------------- Event Declarations -----------------------------

class cancelled(Exception):
    '''test docstring'''
    def __init__(self, *args, **kwargs):
        '''another test docstring'''
        Exception.__init__(self, *args, **kwargs)
    
class pass_keyboard(cancelled): pass

def isdirty(win):
    if win.dirty:
        return True

    fn = win.root.getAlmostAbsolute(win.filename, win.dirname)
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
from plugins import documents
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
from plugins import help
from plugins import keydialog
from plugins import codetree
from plugins import filtertable
from plugins import triggerdialog
from plugins.window_management import docstate, _choicebook
from plugins import methodhelper
from plugins import lineabstraction
from plugins import macro

## from plugins import project

for i in [logger, findbar, lru, filehistory, browser, workspace, todo,
          findinfiles, shell, textrepr, spellcheck, keydialog]:
    i.cancelled = cancelled
    i.isdirty = isdirty

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
    keyMap = {}
    for name in dir(wx):
        if name.startswith('WXK_'):
            key = getattr(wx, name)
            keyMap[key] = name[4:]
    _keys = dict.fromkeys(keyMap.iteritems())
    for i in ["SHIFT", "ALT", "CONTROL", "MENU"]:
        key = getattr(wx, "WXK_"+i)
        keyMap[key] = ''
    del key

    def _decode_key(keycode):
        if keycode >= 256:
            return unichr(keycode)
        else: #keycode < 256:
            return chr(keycode)
    
    def GetKeyPress(evt):
        keycode = evt.GetKeyCode()
        keyname = keyMap.get(keycode, None)
        if keyname is None:
            if "unicode" in wx.PlatformInfo:
                keycode = evt.GetUnicodeKey()
                if keycode <= 127:
                    keycode = evt.GetKeyCode()
                keyname = unichr(evt.GetUnicodeKey())
                
            elif keycode < 256:
                if keycode == 0:
                    keyname = "NUL"
                elif keycode < 27:
                    keyname = chr(ord('A') + keycode-1)
                else:
                    keyname = chr(keycode)
            else:
                keyname = "(%s)unknown" % keycode
    
        modifiers = ""
        for mod, ch in [(evt.ControlDown(), 'Ctrl+'),
                        (evt.AltDown(),     'Alt+'),
                        (evt.ShiftDown(),   'Shift+'),
                        (evt.MetaDown(),    'Meta+')]:
            if mod:
                modifiers += ch
        
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
        ## print menu.__class__, wxMenuItem, wxMenuItemPtr, wxMenu, wxMenuPtr
        if isinstance(menu, (wxMenuBar, wxMenuBarPtr)):
            for i in xrange(menu.GetMenuCount()):
                r = menu.GetMenu(i)
                if r.FindItemById(id):
                    return "%s->%s"%(menu.GetLabelTop(i), recmenu(r, id))
        elif isinstance(menu, (wxMenu, wxMenuPtr)):
            ITEMS = menu.GetMenuItems()
            for i in ITEMS:
                a = recmenu(i, id)
                if a:
                    return a
            return ''
        elif isinstance(menu, (wxMenuItem, wxMenuItemPtr)):
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
        raise Exception("Tried adding a non-menu to a menu?  Contact the author.")
    
    def GETACC(X):
        if len(X) == 3:
            return X
        return X[0], X[1], X[1]
    
    def menuAdd(root, menu, name, desc, funct, id, kind=wxITEM_NORMAL):

        a = wxMenuItem(menu, id, 'TEMPORARYNAME', desc, kind)
        menu.AppendItem(a)
        EVT_MENU(root, id, funct)

        ns, oacc = _spl(name)
        hier = recmenu(menuBar, id)[:-13] + ns
        if hier in MENUPREF:
            name, acc, acc2 = GETACC(MENUPREF[hier])
        else:
            if hier in OLD_MENUPREF:
                name, acc, acc2 = MENUPREF[hier] = GETACC(OLD_MENUPREF[hier])
            else:
                name, acc, acc2 = MENUPREF[hier] = GETACC((ns, oacc))

        MENULIST.append((hier, name, oacc, acc, kind in [wxITEM_NORMAL, wxITEM_CHECK], acc2))
        ## if type(acc) != type(acc2):
            ## acc2 = acc2.decode('latin-1')
        ## if acc != acc2:
            ## print "mismatched hotkey: %r %r"%(acc, acc2)

        if acc or acc2:
            HOTKEY_TO_ID[acc2] = id

        menuBar.SetLabel(id, '%s\t%s'%(name, acc))
        menuBar.SetHelpString(id, desc)

    def menuAddM(parent, menu, name, help=''):
        if isinstance(parent, wxMenu) or isinstance(parent, wxMenuPtr):
            id = wxNewId()
            parent.AppendMenu(id, "TEMPORARYNAME", menu, help)
            hier = recmenu(menuBar, id) + name
            name, toss, toss2 = MENUPREF[hier] = GETACC(MENUPREF.get(hier, (name, '')))

            menuBar.SetLabel(id, name)
            menuBar.SetHelpString(id, help)
        else:
            hier = name
            name, toss, toss2 = MENUPREF[hier] = GETACC(MENUPREF.get(hier, (name, '')))

            parent.Append(menu, name)

        MENULIST.append((hier, name, '', toss, 0, toss2))

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
    assoc = [(wxNewId(), wxNewId(), 'pyrex',  wxSTC_LEX_PYTHON, wxNewId(), wxNewId(), "Pyrex"),
             #made Python second to override the lexer2lang option
             (wxNewId(), wxNewId(), 'python', wxSTC_LEX_PYTHON, wxNewId(), wxNewId(), "Python"),
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
    ASSOC.insert(1, ASSOC.pop(0))
    
    del assoc

#checkbox ids
if 1:
    AUTO = wxNewId()
    NUM = wxNewId()
    MARGIN = wxNewId()
    USETABS = wxNewId()
    INDENTGUIDE = wxNewId()
    WRAPL = wxNewId()
    SLOPPY = wxNewId()
    SMARTPASTE = wxNewId()
    SAVE_CURSOR = wxNewId()
    HIGHLIGHT_LINE = wxNewId()
    S_WHITE = wxNewId()
    DND_ID = wxNewId()
    DB_ID = wxNewId()
    IT_ID = wxNewId()
    LB_ID = wxNewId()
    WIDE_ID = wxNewId()
    TALL_ID = wxNewId()
    SINGLE_ID = wxNewId()
    USEBOM_ID = wxNewId()
    ONE_TAB = wxNewId()
    TD_ID = wxNewId()
    FINDBAR_BELOW_EDITOR = wxNewId()
    NO_FINDBAR_HISTORY = wxNewId()
    CLEAR_FINDBAR_HISTORY = wxNewId()
    ZI = wxNewId()
    
    TRIGGER = wxNewId()
    
    REC_MACRO = wxNewId()
    

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
    
    #caret width option
    
    CARET_W_OPTION_TO_W = dict([(wxNewId(), i) for i in (1,2,3)])
    CARET_W_WIDTH_TO_O = dict([(j,i) for i,j in CARET_W_OPTION_TO_W.iteritems()])
    
    #title display ids
    
    TITLE_ID_TO_OPTIONS = {
        wxNewId()           : (0, "%(pype)s",                       "No file information"),
        wxNewId()           : (1, "%(pype)s - %(fn)s",              "File name after title"),
        wxNewId()           : (2, "%(fn)s - %(pype)s",              "File name before title"),
        wxNewId()           : (3, "%(pype)s - %(fn)s - [%(long)s]", "File and full path after title"),
        wxNewId()           : (4, "%(fn)s - [%(long)s] - %(pype)s", "File and full path before title"),
    }
    
    TITLE_OPTION_TO_ID = dict([(j[0], (i, j[1], j[2])) for i,j in TITLE_ID_TO_OPTIONS.iteritems()])
    
    #for determining what to display in the Documents tab.
    DOCUMENT_LIST_OPTIONS = {
        wxNewId() : (1, "Filename"),
        wxNewId() : (3, "Filename, Path"),
        wxNewId() : (2, "Path"),
        wxNewId() : (0, "Path, Filename")
    }
    
    DOCUMENT_LIST_OPTION_TO_ID = dict([(j[0], i) for i,j in DOCUMENT_LIST_OPTIONS.items()])
    
    #for determining what to do when double-clicking on a macro.
    MACRO_CLICK_OPTIONS = {
        wxNewId() : (0, "do nothing"),
        wxNewId() : (1, "open for editing"),
        wxNewId() : (2, "run macro")
    }
    
    MACRO_CLICK_TO_ID = dict([(j[0], i) for i,j in MACRO_CLICK_OPTIONS.iteritems()])
    
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
def GDI(name):
    if USE_DOC_ICONS:
        return EXT_TO_IMG.get(extns.get(name.split('.')[-1].lower(), 0), 0)
    return -1
#

def GetClipboardText():
    a = wxClipboard()
    if not a.Open():
        return
    b = wxTextDataObject()
    if not a.GetData(b):
        return
    a.Close()
    return b.GetText()

RESET = {'cursorposn':0,
         'BM':[],
         'FOLD':[]}

#threaded parser
if 1:
    parse_queue = Queue.Queue()
    from wx.lib.newevent import NewEvent
    
    DoneParsing, EVT_DONE_PARSING = NewEvent()
    
    def parse(lang, source, le, which, x, slowparse=0):
        source = source.replace('\r\n', '\n').replace('\r', '\n')
        le = '\n'
        if lang in ('python', 'pyrex'):
            if slowparse:
                try:
                    a = fast_parser(source, le, which, x)
                    return a
                except:
                    traceback.print_exc()
                    pass
            return faster_parser(source, le, which, x)
        elif lang == 'tex':
            return latex_parser(source, le, which, x)
        elif lang == 'cpp':
            return c_parser(source, le, which, x)
        elif lang in ('xml', 'html'):
            return ml_parser(source, le, which, x)
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
    if typ is cancelled or typ is pass_keyboard:
        return
    return sys_excepthook(typ, inst, trace)

sys.excepthook = my_excepthook

def veto(*args):
    args[-1].Veto()

#---------------------- Frame that contains everything -----------------------
class MainWindow(wxFrame):
    def __init__(self,parent,id,title,fnames):
        wxFrame.__init__(self,parent,id, title, size = ( 1024, 600 ),
                         style=wxDEFAULT_FRAME_STYLE|wxNO_FULL_REPAINT_ON_RESIZE)
        self.starting = 1
        self.redirect = methodhelper.MethodHelper(self)
        
#------------------------------- configuration -------------------------------
        if 1:
            self.SetIcon(getIcon())
            self.FINDSHOWN = 0
            path = os.path.join(homedir, 'menus.txt')
            if UNICODE:
                p = os.path.join(homedir, 'menus.u.txt')
                if os.path.exists(p):
                    path = p
            print "Loading menus from", path
            try:    OLD_MENUPREF.update(self.readAndEvalFile(path))
            except: pass
            
            single_instance.callback = self.OnDrop
            
            #recent menu relocated to load configuration early on.
            recentmenu = wxMenu()
#--------------------------- cmt-001 - 08/06/2003 ----------------------------
#----------------- Adds opened file history to the File menu -----------------
        if 1:
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
            ## typ = wxITEM_RADIO
            typ = wxITEM_CHECK
            self.HAS_RADIO = 1
        except:
            typ = wxITEM_NORMAL
            self.HAS_RADIO = 0

        #EVT_IDLE(self, self.SetPos)
        #a = wxNewId()
        #self.T = wxTimer(self, a)
        #EVT_TIMER(self, a, self.SetPos)
        #self.T.Start(100)
        
#------------------------------- window layout -------------------------------
        if 1:
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
    
            self.control = documents.MyNB(self, -1, self)
    
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
            
            self.dragger = documents.MyLC(self.RIGHTNB, self)
            
            if DEBUG:
                self.crust = crust.Crust(self.RIGHTNB, rootObject=app,
                    rootLabel='main', execStartupScript=False)
                self.RIGHTNB.AddPage(self.crust, "DEBUG")
            
            y = [('Name', 'leftt'), ('Line','rightt'), ('Filter', 'filterl'), ('Todo','todot')]
            if ONE_TAB_:
                self.single_ctrl = wxChoicebook(self.RIGHTNB, -1)
                self.RIGHTNB.AddPage(self.single_ctrl, "Tools")
            for name,i in y:
                if ONE_TAB_:
                    ctrl = self.single_ctrl
                elif TODOBOTTOM and name=='Todo':
                    ctrl = self.BOTTOMNB
                else:
                    ctrl = self.RIGHTNB
                x = _choicebook(ctrl, -1)
                ctrl.AddPage(x, name)
                setattr(self, i, x)
            
            self.macropage = macro.macroPanel(self.RIGHTNB, self)
            self.RIGHTNB.AddPage(self.macropage, "Macros")
            
            self.BOTTOMNB.AddPage(logger.logger(self.BOTTOMNB), 'Log')
            ## self.BOTTOMNB.AddPage(findinfiles.FindInFiles(self.BOTTOMNB, self), "Find in Files")
            self.BOTTOMNB.AddPage(findinfiles.FindInFiles(self.BOTTOMNB, self), "Search")
            self.BOTTOMNB.AddPage(spellcheck.SpellCheck(self.BOTTOMNB, self), "Spell Check")
            ## self.shell = shell.Shell(self.BOTTOMNB, self, self.config.get('shellprefs', {}))
            ## self.BOTTOMNB.AddPage(self.shell, "Shell")
            if UNICODE:
                self.BOTTOMNB.AddPage(textrepr.TextRepr(self.BOTTOMNB, self), "repr(text)")
            self.BOTTOMNB.AddPage(help.MyHtmlWindow(self.BOTTOMNB), "Help")
    
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
        if 1:
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
            menuAdd(self, filemenu, "&Close\tCtrl+W",       "Close the file in this tab", self.OnClose, wxNewId())
            workspace.WorkspaceMenu(filemenu, self, workspaces, workspace_order)
            menuAdd(self, filemenu, "Restart",              "Restart PyPE", self.OnRestart, wxNewId())
            menuAdd(self, filemenu, "E&xit\tAlt+F4",        "Terminate the program", self.OnExit, wxNewId())

#--------------------------------- Edit Menu ---------------------------------
        if 1:
            editmenu= wxMenu()
            menuAddM(menuBar, editmenu, "&Edit")
            menuAdd(self, editmenu, "Undo\tCtrl+Z",         "Undo last modifications", self.OnUndo, wxID_UNDO)
            menuAdd(self, editmenu, "Redo\tCtrl+Y",         "Redo last modifications", self.OnRedo, wxID_REDO)
            editmenu.AppendSeparator()
            menuAdd(self, editmenu, "Select All\tCtrl+A",   "Select all text", self.OnSelectAll, wxNewId())
            menuAdd(self, editmenu, "Start/End Selection",  "Will allow you to set selection start and end positions without holding shift", self.redirect.OnSelectToggle, wxNewId())
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
        if 1:
            transformmenu= wxMenu()
            menuAddM(menuBar, transformmenu, "&Transforms")
    
            menuAdd(self, transformmenu, "Indent Region\tCtrl+]", "Indent region", self.redirect.OnIndent, IDR)
            menuAdd(self, transformmenu, "Dedent Region\tCtrl+[", "Dedent region", self.redirect.OnDedent, DDR)
            menuAdd(self, transformmenu, "Wrap Selected Text\tAlt+W", "Wrap selected text to a specified width", self.redirect.OnWrap, wxNewId())
            transformmenu.AppendSeparator()
            menuAdd(self, transformmenu, "Insert Comment\tCtrl+I", "Insert a centered comment", self.redirect.OnInsertComment, wxNewId())
            menuAdd(self, transformmenu, "Comment Selection\tAlt+8", "Comment selected lines", self.redirect.OnCommentSelection, wxNewId())
            menuAdd(self, transformmenu, "Uncomment Selection\tAlt+9", "Uncomment selected lines", self.redirect.OnUncommentSelection, wxNewId())
            transformmenu.AppendSeparator()
            menuAdd(self, transformmenu, "Wrap try/except", "Wrap the selected code in a try/except clause", self.redirect.WrapExcept, wxNewId())
            menuAdd(self, transformmenu, "Wrap try/finally", "Wrap the selected code in a try/finally clause", self.redirect.WrapFinally, wxNewId())
            menuAdd(self, transformmenu, "Wrap try/except/finally", "Wrap the selected code in a try/except/finally clause", self.redirect.WrapExceptFinally, wxNewId())
            transformmenu.AppendSeparator()
            menuAdd(self, transformmenu, "Perform Trigger", "Performs a trigger epansion if possible", self.redirect.OnTriggerExpansion, TRIGGER)

#--------------------------------- View Menu ---------------------------------
        if 1:
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
            menuAdd(self, viewmenu, "Jump forward", "Advance the cursor to the next quote/bracket", self.redirect.OnJumpF, wxNewId())
            menuAdd(self, viewmenu, "Jump backward", "Advance the cursor to the previous quote/bracket", self.redirect.OnJumpB, wxNewId())
            viewmenu.AppendSeparator()
            menuAdd(self, viewmenu, "Toggle Bookmark\tCtrl+M", "Create/remove bookmark for this line", self.OnToggleBookmark, pypeID_TOGGLE_BOOKMARK)
            menuAdd(self, viewmenu, "Next Bookmark\tF2", "Hop to the next bookmark in this file", self.OnNextBookmark, pypeID_NEXT_BOOKMARK)
            menuAdd(self, viewmenu, "Previous Bookmark\tShift+F2", "Hop to the previous bookmark in this file", self.OnPreviousBookmark, pypeID_PRIOR_BOOKMARK)
            viewmenu.AppendSeparator()
            menuAdd(self, viewmenu, "Find Definition", "Shows the filter tool and tries to find the current word in the definitions", self.OnFindDefn, wxNewId())

#------------------------------- Document menu -------------------------------
        if 1:
        
            setmenu= wxMenu()
            menuAddM(menuBar, setmenu, "&Document")
            ## menuAdd(self, setmenu, "Use Snippets (req restart)", "Enable or disable the use of snippets, requires restart for change to take effect", self.OnSnipToggle, SNIPT, wxITEM_CHECK)
            ## setmenu.AppendSeparator()
    
            #------------------------------ Style subenu ---------------------
            stylemenu= wxMenu()
            menuAddM(setmenu, stylemenu, "Syntax Highlighting", "Change the syntax highlighting for the currently open document")
            for i in ASSOC:
                name, mid = i[6], i[0]
                st = "Highlight for %s syntax"%name
                if name == 'Text':
                    st = "No Syntax Highlighting"
                
                menuAdd(self, stylemenu, name, st, self.OnStyleChange, mid, typ)
    
            #---------------------------- Encodings submenu ------------------
            if UNICODE:
                encmenu= wxMenu()
                menuAddM(setmenu, encmenu, "Encodings", "Change text encoding")
                menuAdd(self, encmenu, 'ascii', "Change encoding for the current file to ascii (will use utf-8 if unicode characters found)", self.OnEncChange, ENCODINGS['ascii'], typ)
                menuAdd(self, encmenu, 'other', "Will use the encoding specified in your encoding declaration, reverting to ascii if not found, and utf-8 as necessary", self.OnEncChange, ENCODINGS['other'], typ)
                for bom, enc in BOM[:-2]:
                    menuAdd(self, encmenu, enc, "Change encoding for the current file to %s"%enc, self.OnEncChange, ENCODINGS[enc], typ)
    
            #--------------------------- Line ending menu --------------------
            endingmenu = wxMenu()
            menuAddM(setmenu, endingmenu, "Line Ending", "Change the line endings on the current document")
            
            x = LE_RMAPPING.values()
            x.sort()
            for _, idn, name, helpt in x:
                menuAdd(self, endingmenu, name, helpt, self.OnLineEndChange, idn, typ)
            #
            setmenu.AppendSeparator()
            menuAdd(self, setmenu, "Show Autocomplete", "Show the autocomplete dropdown while typing", self.OnAutoCompleteToggle, AUTO, wxITEM_CHECK)
            menuAdd(self, setmenu, "Show line numbers", "Show or hide the line numbers on the current document", self.OnNumberToggle, NUM, wxITEM_CHECK)
            menuAdd(self, setmenu, "Show margin", "Show or hide the bookmark signifier margin on the current document", self.OnMarginToggle, MARGIN, wxITEM_CHECK)
            menuAdd(self, setmenu, "Show Indentation Guide", "Show or hide gray indentation guides in indentation", self.OnIndentGuideToggle, INDENTGUIDE, wxITEM_CHECK)
            menuAdd(self, setmenu, "Show Whitespace", "Show or hide 'whitespace' characters", self.OnWhitespaceToggle, S_WHITE, wxITEM_CHECK)
            menuAdd(self, setmenu, "Save Position", "Remember or forget the last position of the cursor when the current document is closed", self.OnSavePositionToggle, SAVE_CURSOR, wxITEM_CHECK)
            menuAdd(self, setmenu, "Highlight Current line", "When checked, will change the background color of the current line", self.HightlightLineToggle, HIGHLIGHT_LINE, wxITEM_CHECK)
            setmenu.AppendSeparator()
            menuAdd(self, setmenu, "Refresh\tF5", "Refresh the browsable source tree, autocomplete listing, and the tooltips (always accurate, but sometimes slow)", self.OnRefresh, wxNewId())
            menuAdd(self, setmenu, "Run Macro", "Run the currently selected macro on the current document", self.macropage.OnPlay, wxNewId())
            setmenu.AppendSeparator()
            menuAdd(self, setmenu, "Expand all", "Expand all folded code through the entire document", self.OnExpandAll, wxNewId())
            menuAdd(self, setmenu, "Fold all", "Fold all expanded code through the entire document", self.OnFoldAll, wxNewId())
            menuAdd(self, setmenu, "Use Tabs", "New indentation will include tabs", self.OnSetTabToggle, USETABS, wxITEM_CHECK)
            menuAdd(self, setmenu, "Wrap Long Lines", "Visually continue long lines to the next line", self.OnWrapL, WRAPL, wxITEM_CHECK)
            menuAdd(self, setmenu, "Sloppy Cut/Copy", "Will select all partially selected lines during cut/copy.", self.OnSloppy, SLOPPY, wxITEM_CHECK)
            menuAdd(self, setmenu, "Smart Paste", "Will auto-indent pastes that are multi-line", self.OnSmartPaste, SMARTPASTE, wxITEM_CHECK)
            setmenu.AppendSeparator()
            menuAdd(self, setmenu, "Set Triggers", "Sets trigger expansions for the current document", self.OnSetTriggers, wxNewId())
            menuAdd(self, setmenu, "Set Indent Width", "Set the number of spaces per indentation level", self.OnSetIndent, wxNewId())
            menuAdd(self, setmenu, "Set Tab Width", "Set the visual width of tabs in the current open document", self.OnSetTabWidth, wxNewId())
            menuAdd(self, setmenu, "Set Long Line Column", "Set the column number for the long line indicator", self.OnSetLongLinePosition, wxNewId())
    
            #---------------------------- Long line submenu ------------------
            longlinemenu = wxMenu()
            menuAddM(setmenu, longlinemenu, "Set Long Line Indicator", "Change the mode that signifies long lines")
            
            x = LL_RMAPPING.values()
            x.sort()
            for _, idn, name, helpt in x:
                menuAdd(self, longlinemenu, name, helpt, self.OnSetLongLineMode, idn, typ)

#------------------------------- Options Menu --------------------------------
        if 1:
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
            #-------------------------- Default Style submenu ----------------
            stylemenu2 = wxMenu()
            menuAddM(optionsmenu, stylemenu2, "Default Highlighting", "Set the default syntax highlighting for new or unknown documents")
            for i in ASSOC:
                name, mid = i[6], i[1]
                st = "All new or unknown documents will be highlighted as %s"%name
                menuAdd(self, stylemenu2, name, st, self.OnDefaultStyleChange, mid, typ)
    
            optionsmenu.AppendSeparator()
            menuAdd(self, optionsmenu, "Enable File Drops", "Enable drag and drop file support onto the text portion of the editor", self.OnDNDToggle, DND_ID, wxITEM_CHECK)
            optionsmenu.AppendSeparator()
            menuAdd(self, optionsmenu, "Use Icons", "When checked, the editor uses filetype-specific icons next to file names", self.OnIconToggle, IT_ID, wxITEM_CHECK)
            menuAdd(self, optionsmenu, "Editor on top", "When checked, the editor is above the Todos, Log, etc., otherwise it is below (requires restart)", self.OnLogBarToggle, LB_ID, wxITEM_CHECK)
            menuAdd(self, optionsmenu, "Editor on left", "When checked, the editor is left of the source trees, document list, etc., otherwise it is to the right (requires restart)", self.OnDocBarToggle, DB_ID, wxITEM_CHECK)
            menuAdd(self, optionsmenu, "Show Wide Tools", "Shows or hides the tabbed tools that are above or below the editor", self.OnShowWideToggle, WIDE_ID, wxITEM_CHECK)
            menuAdd(self, optionsmenu, "Show Tall Tools", "Shows or hides the tabbed tools that are right or left of the editor", self.OnShowTallToggle, TALL_ID, wxITEM_CHECK)
            menuAdd(self, optionsmenu, "Wide Todo", "When checked, the todo list will be near the Log tab, when unchecked, will be near the Documenst tab (requires restart)", self.OnTodoToggle, TD_ID, wxITEM_CHECK)
            menuAdd(self, optionsmenu, "One Tab", "When checked, the name, line, filter, and todo lists all share a tab (requires restart)", self.OnOneTabToggle, ONE_TAB, wxITEM_CHECK)
            menuAdd(self, optionsmenu, "One PyPE", "When checked, will listen on port 9999 for filenames to open", self.OnSingleToggle, SINGLE_ID, wxITEM_CHECK)
            if UNICODE:
                menuAdd(self, optionsmenu, "Always Write BOM", "If checked, will write BOM when coding: directive is found, otherwise not", self.OnBOMToggle, USEBOM_ID, wxITEM_CHECK)

            toolbarOptionsMenu = wxMenu()
            menuAddM(optionsmenu, toolbarOptionsMenu, "Toolbar", "When checked, will show a toolbar (requires restart)")
            x = TB_RMAPPING.values()
            x.sort()
            for _, idn, name, helpt in x:
                menuAdd(self, toolbarOptionsMenu, name, helpt, self.OnToolBar, idn, typ)

            doptmenu = wxMenu()
            menuAddM(optionsmenu, doptmenu, "Documents List Options", "Change the filename/path layout in the Documents tab")
            for value in (1,3,2,0):
                iid = DOCUMENT_LIST_OPTION_TO_ID[value]
                desc = DOCUMENT_LIST_OPTIONS[iid][1]
                menuAdd(self, doptmenu, desc, "Make the Documents list look like: %s"%desc, self.OnChangeDocumentsOptions, iid, typ)
            
            moptmenu = wxMenu()
            menuAddM(optionsmenu, moptmenu, "Macro Options", "Change the behavior of macros during double-click")
            for value in xrange(3):
                iid = MACRO_CLICK_TO_ID[value]
                desc = MACRO_CLICK_OPTIONS[iid][1]
                menuAdd(self, moptmenu, desc, "When double clicking on a macro: %s"%desc, self.OnChangeMacroOptions, iid, typ)
            
            optionsmenu.AppendSeparator()
            caretmenu = wxMenu()
            menuAddM(optionsmenu, caretmenu, "Caret Tracking", "Set how your caret behaves while it is moving around")
            
            x = [(j[2], i, j[3], j[4]) for i,j in CARET_ID_TO_OPTIONS.iteritems()]
            x.sort()
            for _, idn, name, helpt in x:
                menuAdd(self, caretmenu, name, helpt, self.OnCaret, idn, typ)
            
            menuAdd(self, optionsmenu, "Set Caret M value", "Set the number of lines of unapproachable margin, the M value referenced in Caret Options", self.OnCaretM, wxNewId())
            menuAdd(self, optionsmenu, "Set Caret N value", "Set the multiplier, the N value referenced in Caret Options", self.OnCaretN, wxNewId())
            
            caretmenu2 = wxMenu()
            menuAddM(optionsmenu, caretmenu2, "Caret Width", "Set how wide your caret is to make it more or less visible")
            for i in (1,2,3):
                menuAdd(self, caretmenu2, "%i pixels"%i, "Set your caret to be %i pixels wide."%i, self.OnCaretWidth, CARET_W_WIDTH_TO_O[i], typ)
            
            menuAdd(self, optionsmenu, "Set Line Color", "The color of the current line when 'Highlight Current Line' is enabled", self.OnLineColor, wxNewId())
            
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
        
        if 1:
            helpmenu= wxMenu()
            menuAddM(menuBar, helpmenu, "&Help")
            menuAdd(self, helpmenu, "About...", "About this piece of software", self.OnAbout, wxID_ABOUT)
            helpmenu.AppendSeparator()
            menuAdd(self, helpmenu, "PyPE Help\tF1", "View the help", self.OnHelp, wxID_HELP)

#------------------------ A ...few... state variables ------------------------
        if 1:
            self.Show(true)
            self.dirname = '.'
            self.closing = 0
            self.openfiles = {}
            self.realfn = {}
            self.dpm = 0
            self.menubar.Check(AUTO, showautocomp)
            self.menubar.Check(WRAPL, wrapmode != wxSTC_WRAP_NONE)
            self.menubar.Check(DND_ID, dnd_file)
            self.menubar.Check(IT_ID, USE_DOC_ICONS)
            self.menubar.Check(LB_ID, logbarlocn)
            self.menubar.Check(DB_ID, docbarlocn)
            self.menubar.Check(WIDE_ID, SHOWWIDE)
            self.menubar.Check(TALL_ID, SHOWTALL)
            self.menubar.Check(SINGLE_ID, single_pype_instance)
            if UNICODE:
                self.menubar.Check(USEBOM_ID, always_write_bom)
            self.menubar.Check(TD_ID, TODOBOTTOM)
            self.menubar.Check(USETABS, use_tabs)
            self.menubar.Check(INDENTGUIDE, indent_guide)
            self.menubar.Check(lexers3[DEFAULTLEXER], 1)
            self.menubar.Check(SAVE_CURSOR, save_cursor)
            self.menubar.Check(FINDBAR_BELOW_EDITOR, findbar_location)
            self.menubar.Check(NO_FINDBAR_HISTORY, not no_findbar_history)
            self.menubar.Check(CARET_W_WIDTH_TO_O[CARET_WIDTH], 1)
            self.menubar.FindItemById(CLEAR_FINDBAR_HISTORY).Enable(not no_findbar_history)
            self.menubar.Check(DOCUMENT_LIST_OPTION_TO_ID[document_options], 1)

#------------------------ Drag and drop file support -------------------------
        self.SetDropTarget(FileDropTarget(self))

        #set up some events
        if 1:
            EVT_CLOSE(self, self.OnExit)
            EVT_SIZE(self, self.OnSize)
            EVT_ACTIVATE(self, self.OnActivation)
            EVT_KEY_DOWN(self, self.OnKeyPressed)
            self.starting = 0
            if self.control.GetPageCount() > 0:
                stc = self.getNumWin()[1]
                self.OnDocumentChange(stc)

        #set up some timers
        if 1:
            tid = wxNewId()
            self.timer = wxTimer(self, tid)
            EVT_TIMER(self, tid, self.ex_size)
            tid = wxNewId()
            self.timer2 = wxTimer(self, tid)
            EVT_TIMER(self, tid, self.single_instance_poller)
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
        wxCallAfter(self.control.updateChecks, None)

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
                stc.docstate.Update(h1, todo)

                self.SetStatusText(("Browsable source tree, autocomplete, tooltips and todo"
                                    " updated for %s in %.1f seconds.")%(stc.filename, time.time()-start))

            self.updateWindowTitle()

    def doneParsing(self, evt):
        stc = evt.stc
        
        if not stc:
            return
        
        stc.refresh = 0
    
        stc.cached = tpl = evt.tpl
        
        h1, stc.kw, stc.tooltips, todo = tpl
        stc.kw.sort()
        stc.kw = ' '.join(stc.kw)
        ## ex1 = copy.deepcopy(h1)
        stc.docstate.Update(h1, todo)
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
            fn = stc.getshort()
            long = stc.getlong()
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
        except cancelled:
            pass

    def single_instance_poller(self, evt=None):
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
        cwd = current_path
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
                    self.closeOpen(fn, dn)
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
                ## 'triggers':{},
               'findbarprefs':{},
                     'sloppy':0,
                 'smartpaste':0,
                   'showline':0}
        for _i in ASSOC:
            doc_def[_i[2]] = dict(dct)
            if _i[2] in ('xml', 'html'):
                doc_def['indent'] = 2
            doc_def[_i[2]]['triggers'] = {}
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
                            ('USE_DOC_ICONS', 1),
                            ('CARET_WIDTH', 1),
                            ('ONE_TAB_', 1),
                            ('always_write_bom', 1),
                            ('document_options', 1),
                            ('macro_doubleclick', 0),
                            ('COLOUR', '#d0d0d0'),
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
                LASTOPEN.append((self.getAlmostAbsolute(win.filename, win.dirname), win.GetSaveState()))


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
        self.config['USE_DOC_ICONS'] = USE_DOC_ICONS
        ## self.config['shellprefs'] = self.shell.save_prefs()
        self.config['findbar_location'] = findbar_location
        ## if self.config['usesnippets'] and (not self.restart):
            ## self.config['display2code'] = self.snippet.display2code
            ## self.config['displayorder'] = self.snippet.displayorder
        self.config['lastpath'] = self.config.get('lp', current_path)
        self.config['CARET_WIDTH'] = CARET_WIDTH
        self.config['ONE_TAB_'] = ONE_TAB_
        self.config['always_write_bom'] = always_write_bom
        self.config['document_options'] = document_options
        self.config['macro_doubleclick'] = macro_doubleclick
        self.config['COLOUR'] = COLOUR
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
        for i in xrange(self.control.GetPageCount()):
            win = self.control.GetPage(i).GetWindow1()
            if newf:
                if os.path.normcase(win.getshort()) == path:
                    return i
            elif os.path.normcase(win.getlong()) == path:
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

        dlg = wxFileDialog(self, "Save file as...", current_path, "", "All files (*.*)|*.*", wxSAVE|wxOVERWRITE_PROMPT)
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

            if USE_DOC_ICONS:
                self.control.SetPageImage(wnum, GDI(fn))
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
        wd = self.config.get('lastpath', current_path)
        dlg = wxFileDialog(self, "Choose a/some file(s)...", wd, "", wildcard, wxOPEN|wxMULTIPLE|wxHIDE_READONLY)
        if dlg.ShowModal() == wxID_OK:
            self.OnDrop(dlg.GetPaths())
            self.config['lp'] = dlg.GetDirectory()
        dlg.Destroy()

    def FindModule(self, mod):
        fndmod = mod.split('.')
        lf = len(fndmod)
        pth = sys.path[:]
        pth[1:1] = [current_path]
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
            FN = self.getAlmostAbsolute(fn, d)
            f = open(FN, 'rb')
            txt = f.read()
            f.close()
        else:
            FN = ''
            txt = ''
        
        split = SplitterWindow(self.control, wxNewId(), style=wxSP_NOBORDER)
        split.SetMinimumPaneSize(0)
        EVT_SPLITTER_SASH_POS_CHANGING(self, split.GetId(), veto)
        
        ftype = extns.get(fn.split('.')[-1].lower(), 'python')
        ## if ftype in document_defaults:
            ## print "found filetype-specific defaults", ftype
        ## else:
            ## print "could not find", ftype
        state = dict(document_defaults.get(ftype, DOCUMENT_DEFAULTS))
        
        if not shell:
            nwin = PythonSTC(self.control, wxNewId(), split)
        else:
            state = dict(state)
            state['wrapmode'] = 1
            state['whitespace'] = 0
            nwin = interpreter.MyShell(split, wxNewId(), self, None, shell&1)

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
                _ = self.lastused[FN]
                __ = _.pop('triggers', None)
                state.update(_)
                del _, __, self.lastused[FN]
            ## else:
                ## pass

        else:
            nwin.mod = None
            nwin.format = eol
            nwin.SetText(txt)

        ## print 2
        if not ((d == '') and (fn == ' ')):
            self.fileHistory.AddFileToHistory(os.path.join(d, fn))
        
        if 'checksum' in state:
            if md5.new(txt).hexdigest() != state['checksum']:
                ## print "mismatched checksum"
                state.update(RESET)
        else:
            ## print "no checksum", fn
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
        nwin.docstate = docstate(self, nwin)
        ## print 4
        split.Initialize(nwin)
        ## print 5
        self.control.AddPage(split, nwin.getshort(), switch)
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
            FN = self.getAlmostAbsolute(win.filename, win.dirname)
            fil = open(FN, 'rb')
            txt = fil.read()
            fil.close()
            win.BeginUndoAction()
            try:
                win.SetText(txt, 0)
            finally:
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
        
        fn = self.getAlmostAbsolute(win.filename, win.dirname)
        
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

    def OnRestart(self, e):
        self.OnExit(e)
        _restart()

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
                else:
                    self.curdocstates[self.getAlmostAbsolute(win.filename, win.dirname)] = win.GetSaveState()
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
    def OneCmd(self, funct_name, evt):
        wnum, win = self.getNumWin(evt)
        ff = self.FindFocus()
        if ff != win:
            if isinstance(ff, (wxComboBox, wxTextCtrl)):
                if isinstance(ff, wxComboBox):
                    gm, sm = ff.GetMark, ff.SetMark
                else:
                    gm, sm = ff.GetSelection, ff.SetSelection
                if funct_name == 'DeleteSelection':
                    return ff.Remove(*gm())
                elif funct_name == 'SelectAll':
                    return sm(0, ff.GetLastPosition())
                elif sys.platform == 'win32':
                    if hasattr(ff, 'Can'+funct_name) and getattr(ff, 'Can'+funct_name)():
                        return getattr(ff, funct_name)()
                    return
                else:
                    return getattr(ff, funct_name)()
            return evt.Skip()
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
        
    def OnFindDefn(self, e):
        num, win = self.getNumWin(e)
        
        if hasattr(self, 'single_ctrl'):
            x = self.single_ctrl
        else:
            x = self.RIGHTNB
        
        x.SetSelection(2)
        
        gcp = win.GetCurrentPos()
        st = win.WordStartPosition(gcp, 1)
        end = win.WordEndPosition(gcp, 1)
        
        f = win.docstate.filter
        f.cs.SetValue(1)
        f.filter.SetValue(win.GetTextRange(st, end))
        f.how.SetValue('exact')
        f.update()
        f.filter.SetFocus()
    
#--------------------------- Document Menu Methods ---------------------------

    def OnStyleChange(self,e):
        wnum, win = self.getNumWin(e)
        lang = lexers[e.GetId()]
        win.changeStyle(stylefile, lang)
        win.triggers = document_defaults[lang]['triggers']
        wxCallAfter(self.control.updateChecks, win)

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
        wxCallAfter(self.control.updateChecks, win)

    def OnLineEndChange(self, e):
        n, win = self.getNumWin(e)
        endid = e.GetId()
        newend = LE_MAPPING[endid][0]
        oldend = win.GetEOLMode()
        if oldend != newend:
            win.format = fmt_Rmode[newend]
            win.ConvertEOLs(newend)
            win.SetEOLMode(newend)
        wxCallAfter(self.control.updateChecks, win)

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
    
    def HightlightLineToggle(self, e):
        n, win = self.getNumWin(e)
        win.SetCaretLineVisible(not win.GetCaretLineVisible())
    
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
    
    def OnSloppy(self, e):
        wnum, win = self.getNumWin(e)
        win.sloppy = (win.sloppy + 1) % 2
    
    def OnSmartPaste(self, e):
        wnum, win = self.getNumWin(e)
        win.smartpaste = (win.smartpaste + 1) % 2

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
        ## print win.triggers
        a = triggerdialog.TriggerDialog(self, win, win.triggers)
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
        wxCallAfter(self.control.updateChecks, win)
#--------------------------- Options Menu Methods ----------------------------

    def OnSaveLang(self, e):
        mid = e.GetId()
        lang, desc = SOURCE_ID_TO_OPTIONS.get(mid, ('python', ''))
        n, win = self.getNumWin()
        dct = win.GetSaveState()
        del dct['BM']
        del dct['FOLD']
        del dct['checksum']
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
        wxCallAfter(self.control.updateChecks, None)
    
    def OnSaveSettings(self, e):
        #unused right now.
        n, win = self.getNumWin()
        dct = win.GetSaveState()
        del dct['BM']
        del dct['FOLD']
        del dct['checksum']

        globals().update(dct)
        self.config['DOCUMENT_DEFAULTS'] = dct

    def OnDNDToggle(self, e):
        global dnd_file
        dnd_file = not dnd_file
        
    def OnIconToggle(self, e):
        global USE_DOC_ICONS
        USE_DOC_ICONS = not USE_DOC_ICONS

    def OnLogBarToggle(self, e):
        global logbarlocn
        logbarlocn = not logbarlocn 

    def OnDocBarToggle(self, e):
        global docbarlocn
        docbarlocn = not docbarlocn
    
    def OnShowWideToggle(self, e):
        global SHOWWIDE
        SHOWWIDE = not SHOWWIDE
        if SHOWWIDE:
            self.BOTTOM.Show()
        else:
            self.BOTTOM.Hide()
        self.OnSize(None)
        
    def OnShowTallToggle(self, e):
        global SHOWTALL
        SHOWTALL = not SHOWTALL
        if SHOWTALL:
            self.RIGHT.Show()
        else:
            self.RIGHT.Hide()
        self.OnSize(None)
    
    def OnTodoToggle(self, e):
        global TODOBOTTOM
        TODOBOTTOM = not TODOBOTTOM
    def OnOneTabToggle(self, e):
        global ONE_TAB_
        ONE_TAB_ = not ONE_TAB_

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
    
    def OnBOMToggle(self, e):
        global always_write_bom
        always_write_bom = not always_write_bom
    
    def OnToolBar(self, e):
        global TOOLBAR
        TOOLBAR = TB_MAPPING[e.GetId()][0]
        self.SetStatusText("To apply your changed toolbar settings, restart PyPE.")
        wxCallAfter(self.control.updateChecks, None)
        
    def OnCaret(self, e):
        global caret_option
        i = e.GetId()
        caret_option, flags = CARET_ID_TO_OPTIONS[i][:2]
        wxCallAfter(self.control.updateChecks, None)
        self.SharedCaret()

    def OnCaretM(self, e):
        global caret_slop
        caret_slop = self.getInt("Set Caret M Value", "", caret_slop)
        self.SharedCaret()

    def OnCaretN(self, e):
        global caret_multiplier
        caret_multiplier = self.getInt("Set Caret N Value", "", caret_multiplier)
        self.SharedCaret()
    
    def OnCaretWidth(self, e):
        global CARET_WIDTH
        CARET_WIDTH = CARET_W_OPTION_TO_W.get(e.GetId(), 1)
        for i in CARET_W_OPTION_TO_W:
            self.menubar.Check(i, 0)
        self.menubar.Check(e.GetId(), 1)
        
        num, win = self.getNumWin(e)
        win.SetCaretWidth(CARET_WIDTH)
    
    def OnLineColor(self, e):
        global COLOUR
        data = wx.ColourData()
        data.SetChooseFull(True)
        data.SetColour(COLOUR)
        dlg = wx.ColourDialog(self, data)
        changed = dlg.ShowModal() == wx.ID_OK
        
        if changed:
            c = dlg.GetColourData().GetColour()
            COLOUR = '#%02x%02x%02x'%(c.Red(), c.Green(), c.Blue())
        dlg.Destroy()
        
        self.getNumWin()[1].SetCaretLineBack(COLOUR)

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
        keydialog.MenuItemDialog(self, self).ShowModal()
    
    def OnChangeTitle(self, e):
        global title_option
        i = e.GetId()
        title_option, _, _ = TITLE_ID_TO_OPTIONS[i]
        self.updateWindowTitle()
        wxCallAfter(self.control.updateChecks, None)
        
    def OnChangeDocumentsOptions(self, e):
        global document_options
        i = e.GetId()
        document_options = DOCUMENT_LIST_OPTIONS[i][0]
        self.dragger.setupcolumns()
        self.dragger._Refresh()
        wxCallAfter(self.control.updateChecks, None)
    
    def OnChangeMacroOptions(self, e):
        global macro_doubleclick
        i = e.GetId()
        macro_doubleclick = MACRO_CLICK_OPTIONS[i][0]
        wxCallAfter(self.control.updateChecks, None)
    
    def OnSavePreferences(self, e):
        self.saveHistory()
        
#----------------------------- Help Menu Methods -----------------------------
    def OnAbout(self, e):
        txt = """
        PyPE was written to scratch an itch.  I (Josiah Carlson), was looking for
        an editor for Python that had the features I wanted.  I couldn't find one,
        so I wrote PyPE.

        PyPE %s (Python Programmers Editor)
        http://come.to/josiah
        PyPE is copyright 2003-2006 Josiah Carlson.
        Contributions are copyright their respective authors.

        This software is licensed under the GPL (GNU General Public License) version 2
        as it appears here: http://www.gnu.org/copyleft/gpl.html
        It is also included with this software as gpl.txt.

        If you do not also receive a copy of gpl.txt with your version of this
        software, please inform the me of the violation at the web page near the top
        of this document."""%VERSION
        self.dialog(txt.replace('        ', ''), "About...")

    def OnHelp(self, e):
        if not SHOWWIDE:
            self.OnShowWideToggle(None)
        self.BOTTOMNB.SetSelection(self.BOTTOMNB.GetPageCount()-1)
        
        def fixsize():
            h = self.GetClientSizeTuple()[1]
            self.BOTTOM.SetDefaultSize((BIG, max(h//2, self.BOTTOM.GetSize()[1])))
            
            wxLayoutAlgorithm().LayoutWindow(self, self.control)
            self.control.Refresh()
            
            self.ex_size()
        
        wxCallAfter(fixsize)
        
#-------------------------- Hot Key support madness --------------------------
    def keyboardShortcut(self, keypressed, evt=None):
        menuid = HOTKEY_TO_ID[keypressed]
        wxPostEvent(self, wxMenuEvent(wxEVT_COMMAND_MENU_SELECTED, menuid))
        
    def OnKeyPressed(self, event):
        showpress=0
        
        keypressed = GetKeyPress(event)
        
        if showpress: print "keypressed", keypressed
        
        if keypressed in HOTKEY_TO_ID:
            return self.keyboardShortcut(keypressed, event)
        if self.macropage.RunMacro(keypressed):
            return

        key = event.KeyCode()
        wnum = self.control.GetSelection()
        pagecount = self.control.GetPageCount()
        if wnum > -1:
            win = self.control.GetPage(wnum).GetWindow1()

        if pagecount:
            if (key==13):
                #when 'enter' is pressed, indentation needs to happen.
                if win.AutoCompActive():
                    return win.AutoCompComplete()
                if win.CallTipActive():
                    win.CallTipCancel()
                win._autoindent()
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
                    elif win.showautocomp and bool(win.kw):
                        if keypressed.split('+')[-1] in _keys:
                            return
                        if keypressed.endswith('+') and not keypressed.endswith('++'):
                            return
                        wxCallAfter(self._ac, win)
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
    
    def _ac(self, win):
        cur, colpos, word = self.getLeftFunct(win)
        if not word:
            return win.AutoCompCancel()

        words = [i for i in win.kw.split() if i.startswith(word)]
        if len(words) == 0:
            return win.AutoCompCancel()
        if len(words) == 1 and words[-1] == word:
            return win.AutoCompCancel()

        words = ' '.join(words)
        win.AutoCompSetIgnoreCase(False)
        win.AutoCompShow(colpos-cur, words)
        

#------------- Ahh, Styled Text Control, you make this possible. -------------
#the following table maps from event numbers to method names in the STC macro
#recording
message_lookup_table = {
    2013:'SelectAll',
    2177:'Cut',
    2178:'Copy',
    2179:'Paste',
    2180:'Clear',
    2300:'LineDown',
    2301:'LineDownExtend',
    2302:'LineUp',
    2303:'LineUpExtend',
    2304:'CharLeft',
    2305:'CharLeftExtend',
    2306:'CharRight',
    2307:'CharRightExtend',
    2308:'WordLeft',
    2309:'WordLeftExtend',
    2310:'WordRight',
    2311:'WordRightExtend',
    2312:'Home',
    2313:'HomeExtend',
    2314:'LineEnd',
    2315:'LineEndExtend',
    2316:'DocumentStart',
    2317:'DocumentStartExtend',
    2318:'DocumentEnd',
    2319:'DocumentEndExtend',
    2320:'PageUp',
    2321:'PageUpExtend',
    2322:'PageDown',
    2323:'PageDownExtend',
    2324:'EditToggleOvertype',
    2325:'Cancel',
    2326:'DeleteBack',
    2327:'Tab',
    2328:'BackTab',
    2329:'NewLine',
    2330:'FormFeed',
    2331:'VCHome',
    2332:'VCHomeExtend',
    2333:'ZoomIn',
    2334:'ZoomOut',
    2335:'DelWordLeft',
    2336:'DelWordRight',
    2337:'LineCut',
    2338:'LineDelete',
    2339:'LineTranspose',
    2340:'LowerCase',
    2341:'UpperCase',
    2342:'LineScrollDown',
    2343:'LineScrollUp',
    2344:'DeleteBackNotLine',
    2345:'HomeDisplay',
    2346:'HomeDisplayExtend',
    2347:'LineEndDisplay',
    2348:'LineEndDisplayExtend'
}
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

        self.hierarchy = []
        self.kw = []
        self.tooltips = {}
        self.ignore = {}
        self.lines = lineabstraction.LineAbstraction(self)

        self.parent = parent
        self.notebook = notebook #should also be equal to self.parent.parent
        self.root = self.notebook.root
        self.sloppy = 0
        self.smartpaste = 0
        self.dirty = 0
        self.refresh = 0
        self.lexer = 'text'
        self.selep = None
        self.recording = 0
        self.macro = []

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
        self.SetPasteConvertEndings(1)

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
        EVT_STC_CHANGE(self, ID, self.key_up)
        #unavailable in 2.5.1.2, didn't work in previous versions of wxPython
        # EVT_STC_POSCHANGED(self, ID, self.pos)
        EVT_STC_SAVEPOINTREACHED(self, ID, self.MakeClean)
        EVT_STC_SAVEPOINTLEFT(self, ID, self.MakeDirty)
        EVT_STC_NEEDSHOWN(self, ID, self.OnNeedShown)
        self.Bind(EVT_STC_MACRORECORD, self.GotEvent)
        self.SetModEventMask(wxSTC_MOD_INSERTTEXT|wxSTC_MOD_DELETETEXT|wxSTC_PERFORMED_USER|wxSTC_PERFORMED_UNDO|wxSTC_PERFORMED_REDO)

        if REM_SWAP:
            self.CmdKeyClear(ord('T'), wxSTC_SCMOD_CTRL)

        self.CmdKeyClear(ord('Z'), wxSTC_SCMOD_CTRL)
        self.CmdKeyClear(ord('Y'), wxSTC_SCMOD_CTRL)
        self.CmdKeyClear(ord('X'), wxSTC_SCMOD_CTRL)
        self.CmdKeyClear(ord('C'), wxSTC_SCMOD_CTRL)
        self.CmdKeyClear(ord('V'), wxSTC_SCMOD_CTRL)
        self.CmdKeyClear(ord('A'), wxSTC_SCMOD_CTRL)
    
    def getshort(self):
        if self.dirname:
            return self.filename
        return '<untitled %i>'%self.NEWDOCUMENT
    
    def getlong(self):
        if self.dirname:
            return os.path.join(self.dirname, self.filename)
        return ''
    
    def MacroToggle(self, e):
        self.recording = not self.recording
        if self.recording:
            self.macro = []
            self.StartRecord()
        else:
            self.StopRecord()
            self.root.SetStatusText("Recorded %s steps for the macro"%len(self.macro))
    
    def StopRecord(self):
        wxStyledTextCtrl.StopRecord(self)
        #macro: merge all character 2170 events together
        macro = []
        last = []
        x = len(self.macro)
        for i in self.macro:
            if i[0] != 2170 or (i[0] == 2170 and isinstance(i[-1], (int, long))):
                if last:
                    macro.append((2170, 0, ''.join(last)))
                    last = []
                macro.append(i)
            else:
                last.append(i[-1])
        if last:
            macro.append((2170, 0, ''.join(last)))
        if len(macro) < x:
            self.macro = macro
            if PRINTMACROS: print "Reduced macro from %i to %i steps"%(x, len(macro))
    
    def _macro_to_source(self):
        mlt = message_lookup_table
        z = ['def macro(self):']
        for i in self.macro:
            m,w,l = i
            if m in mlt:
                z.append('    self.%s()'%mlt[m])
            elif m is None:
                z.append('    self.%s(%s)'%(l, w))
            elif isinstance(m, basestring):
                if l == None:
                    z.append("    self.root.keyboardShortcut(%r)"%m)
                else:
                    z.append("    #the following shouldn't happen: %r"%(i,))
                    z.append("    root.Dent(None, %i)"%l)
            elif m == 2170:
                if isinstance(l, basestring):
                    z.append("    self.ReplaceSelection(%r)"%l)
                else:
                    z.append("    #this event shouldn't happen: %r"%(i,))
            else:
                z.append("    #this event shouldn't happen: %r"%(i,))
        return '\n'.join(z)
    
    def InterpretTrigger(self, tr, strict=0):
        self.BeginUndoAction()
        try:
            if not strict:
                tr = tr.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '%L')
            
            posn = p = self.GetSelection()[0]
            todos = tr.split('%C')
            for y, todo in enumerate(todos):
                if '\n' in todo:
                    ts = todo.split('%L')
                    for x, line in enumerate(ts):
                        self.ReplaceSelection(line)
                        if x != len(ts)-1:
                            self._autoindent()
                else:
                    self.ReplaceSelection(todo)
                if y != len(todos)-1:
                    posn = self.GetSelection()[0]
            
            if posn != p:
                self.SetSelection(posn, posn)
        finally:
            self.EndUndoAction()
    
    def _tdisable(self, fcn, *args, **kwargs):
        _, self.recording = self.recording, 0
        try:
            return fcn(*args, **kwargs)
        finally:
            self.recording = _
    
    def GotEvent(self, e):
        if self.recording:
            x = (e.GetMessage(), e.GetWParam(), e.GetLParam())
            if x[0] in message_lookup_table:
                self.macro.append(x)
            elif x[0] != 2170:
                print "Unhandled event, please report to the author", x
            
    def PlayMacro(self):
        mlt = message_lookup_table
        ## self.BeginUndoAction()
        
        #macro: z represents generated code based on method name
        z = ['def macro(self):']
        for i in self.macro:
            m,w,l = i
            ## print i,
            if m in mlt:
                method = getattr(self, mlt[m])
                z.append('    self.%s()'%mlt[m])
                method()
            elif m is None:
                z.append('    self.%s(%s)'%(l, w))
                getattr(self, l)(w)
            elif isinstance(m, basestring):
                if l == None:
                    z.append("    self.root.keyboardShortcut(%r)"%m)
                    self.root.keyboardShortcut(m)
                else:
                    print "shouldn't happen!", i
                    z.append("    root.Dent(None, %i)"%l)
                    self.root.Dent(None, l)
            elif m == 2170:
                if isinstance(l, basestring):
                    z.append("    self.ReplaceSelection(%r)"%l)
                    self.ReplaceSelection(l)
                else:
                    print "shouldn't happen!", i
            else:
                print "Unhandled event:",i
            wxYield()
            time.sleep(.01)
        ## self.EndUndoAction()
        print "Performed %s steps of the macro!"%len(self.macro)
        if PRINTMACROS: print '\n'.join(z)

    def save(self, e):
        #print "save reached"
        self.key_up(e)

    def savel(self, e):
        #print "save left"
        self.key_up(e)

    def key_up(self, e):
        if self.GetModify(): self.MakeDirty()
        else:                self.MakeClean()
    
    def pos_ch(self, e):
        if self.root.control.GetCurrentPage() == self.GetParent():
            if not hasattr(self, 'lines'):
                return
            l = self.lines
            self.root.SetStatusText("L%i C%i"%(l.curlinei+1, l.curlinep), 1)
        if e:
            e.Skip()

    def added(self, e):
        if self.recording:
            if e:
                self.macro.append((2170, 0, _decode_key(e.GetKey())))
            ## print "got key", repr(self.macro[-1][-1]), e.GetKey()
        
        expanded = 0
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
                elif isinstance(tr, (str, unicode)):
                    if e:
                        self.macro.append((None, 1, 'added'))
                    
                    self.SetSelection(p, p+c)
                    self.ReplaceSelection('')
                    self.InterpretTrigger(tr)
                    
                    expanded = 1
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
        self._tdisable(self.SetSelection, p, p)
        
    def OnJumpF(self, e):
        self.jump(1)
            
    def OnJumpB(self, e):
        self.jump(-1)
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
                ## 'triggers':self.triggers,
                'whitespace':self.GetViewWhiteSpace(),
                'sloppy':self.sloppy,
                'smartpaste':self.smartpaste,
                'checksum':md5.new(self.GetText()).hexdigest(),
                'showline':self.GetCaretLineVisible()
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
        self.triggers = saved['triggers']
        self.sloppy = saved['sloppy']
        self.smartpaste = saved['smartpaste']
        self.SetCaretLineVisible(saved['showline'])
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
        self.enc = actual = 'ascii'
        if UNICODE:
            for bom, enc in BOM:
                if txt[:len(bom)] == bom:
                    self.enc = actual = enc
                    txt = txt[len(bom):]
                    ## print "chose", enc
                    break
            twolines = txt.split(self.format, 2)[:2]
            foundcoding = 0
            for line in twolines:
                x = re.search('coding[=:]\s*([-\w.]+)', line)
                if not x:
                    continue
                x = x.group(1).lower()
                ## print "ENCODING:", x
                if x in ADDBOM:
                    if actual != 'ascii' and actual != x:
                        #BOM did not match coding: directive.
                        #We are going to decode based on the BOM, but claim
                        #whatever
                        self.enc = x
                    else:
                        self.enc = actual = x
                else:
                    self.enc = x
                    if actual == 'ascii':
                        actual = x
                foundcoding = 1
                break
            
            while 1:
                try:
                    txt = txt.decode(actual)
                except Exception, why:
                    
                    if self.enc != actual:
                        self.root.dialog(('''\
                            You have declared %r as your encoding, but
                            your document included a BOM for %r.
                            PyPE was not able to decode your document as
                            %r due to:
                            %s
                            PyPE will now attempt to decode your document as
                            %r.'''%(self.enc, actual, actual, why, self.enc)).replace(28*' ', ''),
                            "%r decoding error"%actual)
                        actual = self.enc
                        continue
                    
                    if foundcoding:
                        self.root.dialog(('''\
                            You have used %r as your encoding
                            declaration, but PyPE was unable to decode
                            your document due to:
                            %s
                            PyPE will load your document as ASCII.
                            Depending on the content of your file, this
                            may cause data loss if you save the opened
                            version.  You do so at your own risk, and
                            have now been warned.
                            
                            To prevent loss or corruption of data, it
                            is suggested that you close the document,
                            do not save.  Then try to open the document
                            with the application you originally created
                            it with.  If PyPE was the original creator
                            and only editor of the document, please
                            contact the author and submit a bug report.'''%(actual, why)).replace(28*' ', ''),
                            "%r decoding error"%actual)
                    else: #foundbom
                        self.root.dialog(('''\
                            While attempting to decode your document
                            as %r based on the BOM included with it,
                            there  was a unicode decoding error:
                            %s
                            PyPE will load your document as ASCII.
                            Depending on the content of your file, this
                            may cause data loss if you save the opened
                            version.  You do so at your own risk, and
                            have now been warned.
                            
                            To prevent loss or corruption of data, it
                            is suggested that you close the document,
                            do not save.  Then try to open the document
                            with the application you originally created
                            it with.  If PyPE was the original creator
                            and only editor of the document, please
                            contact the author and submit a bug report.'''%(actual, why)).replace(28*' ', ''),
                            "Unicode decoding error.")
                        
                    self.enc = 'ascii'
                break
            
            if self.enc not in ADDBOM:
                self.enc = 'other'

        wxStyledTextCtrl.SetText(self, txt)
        self.ConvertEOLs(fmt_mode[self.format])
        self.opened = 1
        if emptyundo:
            self.EmptyUndoBuffer()
            self.SetSavePoint()

    def GetText(self):
        self.ConvertEOLs(fmt_mode[self.format])
        if UNICODE:
            txt = otxt = wxStyledTextCtrl.GetText(self)
            twolines = txt.split(self.format, 2)[:2]
            x = None
            #pull the encoding
            for line in twolines:
                x = re.search('coding[=:]\s*([-\w.]+)', line)
                if not x:
                    continue
                x = str(x.group(1).lower())
                break
            
            #try self.enc, the discovered coding, ascii, then utf-8 in that order
            why = None
            z = {}
            for i in [j for j in (self.enc, x, 'ascii', 'utf-8') if j and j != 'other']:
                if i in z:
                    continue
                z[i] = None
                try:
                    txt = otxt.encode(i)
                except UnicodeEncodeError, wh:
                    if why is None:
                        why = wh
                else:
                    if (self.enc != 'other' and self.enc != i) or \
                       (self.enc == 'other' and x != i):
                        y = os.path.join(self.dirname, self.filename)
                        if self.root.dialog(('''\
                                While trying to save the file named:
                                    %s
                                PyPE was not able to encode the file as specified
                                in the encoding declaration or the Document -> Encoding
                                option:
                                    %r
                                Due to:
                                    %s
                                Would you like for PyPE to instead use %r as an encoding?
                                '''%(y, x, why, i)).replace(32*' ', ''),
                                "Continue with alternate encoding?", wxYES_NO) != wxID_YES:
                            raise cancelled
                        self.root.SetStatusText("Using %r encoding for %s"%(i, y))
                    
                    ## print 'SAVED ENCODING:', i
                    if (always_write_bom and i == x) or (i != x):
                        ## print "added BOM for", i
                        txt = ADDBOM.get(i, '') + txt
                    return txt
            #this exception should never be raised
            raise Exception, "You should contact the author of this software."
        return wxStyledTextCtrl.GetText(self)

#----- Takes care of the little '*' modified next to the open file name ------
    def MakeDirty(self, e=None):
        if (not self.dirty) and self.opened:
            self.dirty = 1
            f = self.getshort()
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
            f = self.getshort()
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
        if dirty:
            self.MakeDirty(None)
        funct(self)
        self.root.redrawvisible(self)
    def SelectLines(self, force=0):
        x,y = self.GetSelection()
        if not force and x==y:
            return
        
        x,y = self.lines.selectedlinesi
        
        if y-x > 1 or force:
            self.lines.selectedlinesi = x,y
    
    def Cut(self):
        if self.sloppy and not self.SelectionIsRectangle():
            self.SelectLines()
        self.do(wxStyledTextCtrl.Cut)
    def Copy(self):
        if self.sloppy and not self.SelectionIsRectangle():
            self.SelectLines()
        self.do(wxStyledTextCtrl.Copy, 0)
    def Paste(self):
        if self.recording:
            self.macro.append((2179, 0, 0))
        while self.smartpaste:
            x,y = self.GetSelection()
            if x != y:
                break
            d = GetClipboardText()
            if d is None or '\n' not in d:
                break
            
            self.BeginUndoAction()
            #create a new line using the auto-indent stuff
            try:
                curline = self.LineFromPosition(x)
                x = self.GetLineEndPosition(curline)
                self.SetSelection(x,x)
                if self.GetLineIndentation(curline)+self.PositionFromLine(curline) != x:
                    self._tdisable(self._autoindent, self)
                
                #sanitize the information to be pasted
                lines = d.replace('\r\n', '\n').replace('\r', '\n').split('\n')
                
                #find the leading indentation for the clipboard text
                tabwidth = self.GetTabWidth()
                repl = tabwidth*' '
                x = []
                z = len(d)
                for line in lines:
                    leading_whitespace = line[:len(line)-len(line.lstrip())]
                    rest = line[len(leading_whitespace):]
                    leading_whitespace = leading_whitespace.replace('\t', repl)
                    llw = len(leading_whitespace)
                    if not rest.strip():
                        llw = z
                    x.append((llw, leading_whitespace, rest))
                
                #reindent the clipboard text
                base = self.GetLineIndentation(self.LineFromPosition(self.GetSelection()[0]))*' '
                min_i = min(x)[0]
                usetabs = self.GetUseTabs()
                out = []
                for y, (li, lw, lr) in enumerate(x):
                    lw = lw[min_i:]
                    if y:
                        ## print "non-first line", lr
                        lw = base + lw
                    if usetabs:
                        lw = lw.replace(repl, '\t')
                    out.append(lw+lr)
                
                x = self.format.join(out)
                #insert the clipboard text
                self.ReplaceSelection(x)
            finally:
                self.EndUndoAction()
            return
                
        self.do(wxStyledTextCtrl.Paste)
    def DeleteSelection(self):   self.do(wxStyledTextCtrl.DeleteBack)
    def Undo(self):     self.do(wxStyledTextCtrl.Undo)
    def Redo(self):     self.do(wxStyledTextCtrl.Redo)
    def CanEdit(self):
        return 1
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
        self.pos_ch(None)

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
#(really I copied a lot more, but that part I didn't modify at all, I
#wanted to understand it, but it just worked, so there was no need)

#----------------------------- from Paul McNett ------------------------------
    def OnNeedShown(self, evt):
        """ Called when the user deletes a hidden header line."""
        # We expand the previously folded text, but it may be better
        # to delete the text instead, since the user asked for it.
        # There are two bits of information in the event; the position
        # and the length. I think we could easily clear the text based
        # on this information, but for now I'll keep it just displaying
        # the previously hidden text. --pkm 2006-04-04.
        o = evt.GetEventObject()
        position = evt.GetPosition()
        ## length = evt.GetLength()
        line = o.LineFromPosition(position)
        o.Expand(line, True)

#-------------------------- Transforms Menu Methods --------------------------
    def OnWrap(self, e):
        valu = self.root.getInt('Wrap to how many columns?', '', col_line)
        
        self.MakeDirty()
        self.SelectLines(1)
        x,y = self.GetSelection()
        if x==y:
            return
        print repr(self.GetSelectedText())
        lnstart = self.LineFromPosition(x)
        lnend = self.LineFromPosition(y-1)

        paragraphs = []
        lines = []
        for ln in xrange(lnstart, lnend+1):
            lin = self.GetLine(ln)
            if not lin.strip():
                if lines:
                    paragraphs.append(self.format.join(textwrap.wrap(' '.join(lines), valu)))
                paragraphs.append(lin.rstrip('\r\n'))
                lines = []
            else:
                lines.append(lin.strip())
        if lines:
            paragraphs.append(self.format.join(textwrap.wrap(' '.join(lines), valu)))
        paragraphs.append('')
        self.ReplaceSelection(self.format.join(paragraphs))

    def Dent(self, e, incr):
        incr *= self.GetIndent()
        x,y = self.GetSelection()
        if x==y:
            lnstart = self.GetCurrentLine()
            lnend = lnstart
            if incr < 0:
                a = self.GetLineIndentation(lnstart)%(abs(incr))
                if a:
                    incr = -a
            pos = self.GetCurrentPos()
            col = self.GetColumn(pos)
            linestart = pos-col
            a = max(linestart+col+incr, linestart)
        else:
            lnstart = self.LineFromPosition(x)
            lnend = self.LineFromPosition(y-1)
        self.BeginUndoAction()
        try:
            for ln in xrange(lnstart, lnend+1):
                count = self.GetLineIndentation(ln)
                m = (count+incr)
                m += cmp(0, incr)*(m%incr)
                m = max(m, 0)
                self.SetLineIndentation(ln, m)
            if x==y:
                pos = pos + (m-count) - min(0, col + (m-count))
                self.SetSelection(pos, pos)
            else:
                p = 0
                if lnstart != 0:
                    p = self.GetLineEndPosition(lnstart-1) + len(self.format)
                self.SetSelection(p, self.GetLineEndPosition(lnend))
        finally:
            self.EndUndoAction()

    def OnIndent(self, e):
        self.Dent(e, 1)
    def OnDedent(self, e):
        self.Dent(e, -1)
    def OnInsertComment(self, e):
        dlg = wxTextEntryDialog(self, '', 'Enter a comment.', '')
        resp = dlg.ShowModal()
        valu = dlg.GetValue()
        dlg.Destroy()
        if resp != wxID_OK:
            raise cancelled
            
        _lexer = self.GetLexer()
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
        a = self.GetEdgeColumn() - len(c) - len(d) - 2 - k
        b = a*'-'
        st = '%s%s %s %s%s%s'%(c, b[:a/2], valu, b[a/2:], d, self.format)
        lin = self.GetCurrentLine()
        if lin>0:
            self.InsertText(self.GetLineEndPosition(lin-1)+len(self.format), st)
        else:
            self.InsertText(0, st)
        self.MakeDirty()

    def OnCommentSelection(self, e):
        sel = self.GetSelection()
        start = self.LineFromPosition(sel[0])
        end = self.LineFromPosition(sel[1])
        if end > start and self.GetColumn(sel[1]) == 0:
            end = end - 1
        self.MakeDirty()
        self.BeginUndoAction()
        try:
            _lexer = self.GetLexer()
            for lineNumber in range(start, end + 1):
                firstChar = self.GetLineIndentPosition(lineNumber)
                lastChar = self.GetLineEndPosition(lineNumber)
                ranga = self.GetTextRange(firstChar,lastChar)
                if len(ranga.strip()) != 0:
                    if _lexer == wxSTC_LEX_CPP:
                        self.InsertText(firstChar, '// ')
                    elif self.GetLexer() in (wxSTC_LEX_HTML, wxSTC_LEX_XML):
                        self.InsertText(lastChar, ' -->')
                        self.InsertText(firstChar, '<!-- ')
                    elif _lexer == wxSTC_LEX_LATEX:
                        self.InsertText(firstChar, '%')
                    else:
                        self.InsertText(firstChar, '## ')
            self.SetCurrentPos(self.PositionFromLine(start))
            self.SetAnchor(self.GetLineEndPosition(end))
        finally:
            self.EndUndoAction()

    def OnUncommentSelection(self, e):
        sel = self.GetSelection()
        start = self.LineFromPosition(sel[0])
        end = self.LineFromPosition(sel[1])
        if end > start and self.GetColumn(sel[1]) == 0:
            end = end - 1
        self.MakeDirty()
        self.BeginUndoAction()
        try:
            _lexer = self.GetLexer()
            for lineNumber in range(start, end + 1):
                firstChar = self.GetLineIndentPosition(lineNumber)
                lastChar = self.GetLineEndPosition(lineNumber)
                texta = self.GetTextRange(firstChar,lastChar)
                lengtha = 0
                rangeb = None
                if len(texta.strip()) != 0:
                    if _lexer == wxSTC_LEX_CPP:
                        if texta.startswith('// '):
                            lengtha = 3
                        elif texta.startswith('//'):
                            lengtha = 2
                    elif self.GetLexer() in (wxSTC_LEX_HTML, wxSTC_LEX_XML):
                        if texta.startswith('<!-- '):
                            lengtha = 5
                        elif texta.startswith('<!--'):
                            lengtha = 4
                        
                        if lengtha:
                            if texta.endswith(' -->'):
                                rangeb = (lastChar-4, lastChar)
                            elif texta.endswith('-->'):
                                rangeb = (lastChar-3, lastChar)
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
                        self.SetSelection(*rangeb)
                        self.ReplaceSelection("")
                    
                    self.SetSelection(firstChar,firstChar+lengtha)
                    self.ReplaceSelection("")
    
            self.SetCurrentPos(self.PositionFromLine(start))
            self.SetAnchor(self.GetLineEndPosition(end))
        finally:
            self.EndUndoAction()

    def WrapFE(self, e, tail):
        x,y = self.GetSelection()
        if x==y:
            lnstart = self.GetCurrentLine()
            lnend = lnstart
        else:
            lnstart = self.LineFromPosition(x)
            lnend = self.LineFromPosition(y-1)
        
        for linenum in xrange(lnstart, lnend+1):
            line = self.GetLine(linenum)
            if not line.strip():
                continue
            x = self.GetLineIndentation(linenum)
            break
        else:
            self.root.SetStatusText("Could not find anything to wrap with try: %s:!"%tail)
            return
        
        self.BeginUndoAction()
        try:
            self.OnIndent(e)

            #find the indentation level for the except/finally clause
            xp = x+self.GetIndent()
            xp -= xp%self.GetIndent()
            
            #get some line and selection information
            ss, es = self.GetSelection()
            lnstart = self.LineFromPosition(ss)
            lnend = self.LineFromPosition(es)
            
            #insert the except/finally
            self.SetSelection(es, es)
            self.ReplaceSelection(self.format + tail + ':' + self.format)
            self.SetLineIndentation(lnend+1, x)
            self.SetLineIndentation(lnend+2, xp)
            
            #insert the try
            self.SetSelection(ss, ss)
            self.ReplaceSelection('try:' + self.format)
            self.SetLineIndentation(lnstart, x)
            
            #relocate the cursor
            p = 0
            if lnstart != 0:
                p = self.GetLineEndPosition(lnstart-1) + len(self.format)
            self.SetSelection(p, self.GetLineEndPosition(lnend+3))
        finally:
            self.EndUndoAction()
        
    def WrapFinally(self, e):
        self.WrapFE(e, 'finally')
        
    def WrapExcept(self, e):
        self.WrapFE(e, 'except')
        
    def WrapExceptFinally(self, e):
        self.BeginUndoAction()
        try:
            self.WrapFE(e, 'except')
            self.WrapFE(e, 'finally')
        finally:
            self.EndUndoAction()

    def OnTriggerExpansion(self, e):
        self.added(None)
    
    def style(self):
        return lexer2lang[self.GetLexer()]
        
    def _autoindent(self, ignore=None):
        if self.recording:
            self.macro.append((None, 0, '_autoindent'))
        #will indent the current line to be equivalent to the line above
        #unless a language-specific indent cue is present
    
        #get information about the current cursor position
        linenum = self.GetCurrentLine()
        pos = self.GetCurrentPos()
        col = self.GetColumn(pos)
        linestart = self.PositionFromLine(linenum)
        line = self.GetLine(linenum)[:pos-linestart]
    
        #get info about the current line's indentation
        ind = self.GetLineIndentation(linenum)                    
        
        xtra = 0
        
        lang = self.style()
        
        if col <= ind:
            xtra = None
            if self.GetUseTabs():
                self.ReplaceSelection(self.format+(col*' ').replace(self.GetTabWidth()*' ', '\t'))
            else:
                self.ReplaceSelection(self.format+(col*' '))
        elif not pos:
            xtra = None
            self.ReplaceSelection(self.format)
        
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
            x[2] -= first==2
            xtra = x[1]-x[2]
            if line.split()[:1] == ['return']:
                xtra -= 1
        
        elif lang in ('xml', 'html'):
            ## print "trying", lang
            ls = line.split('<')
            for i in xrange(len(ls)-1, -1, -1):
                lsi = ls[i]
                lsis = lsi.strip()
                lsil = lsi.lower()
                c = 0
                for i in no_ends:
                    if lsil.startswith(i):
                        c = 1
                        break
                if c:
                    continue
                
                if '/>' in lsi or '/ >' in lsi:
                    continue
                elif lsi[:1] == '/':
                    xtra -= 1
                elif lsis: 
                    xtra += 1
            #we are limiting ourselves to 1 indent/dedent per step
            xtra = min(max(xtra, -1), 1)
        
        elif lang == 'tex':
            ## print "trying", lang, line.strip()
            if line.lstrip().startswith('\\begin'):
                xtra = 1
            #end doesn't make sense, as it should be on the same indent level
            #as the begin.
            ## elif line.lstrip()[:4] == '\\end':
                ## xtra = -1
        
        #insert other indentation per language here.
        
        else: #if language is python
            ## print "indent on return for python"
            colon = ord(':')
            
            if (line.find(':')>-1):
                for i in xrange(linestart, min(pos, self.GetTextLength())):
                    styl = self.GetStyleAt(i)
                    #print styl, self.GetCharAt(i)
                    if not xtra:
                        if (styl==10) and (self.GetCharAt(i) == colon):
                            xtra = 1
                    elif (styl == 1):
                        #it is a comment, ignore the character
                        pass
                    elif (styl == 0) and (self.GetCharAt(i) in [ord(i) for i in ' \t\r\n']):
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
                                'for', 'try', 'except', 'finally', 'with', 'cdef']:
                            a = line.find(i)
                            if (a > -1):
                                found.append(a)
                        #print 'fnd', found
                        if found: found = min(found)
                        else:     found = -1
                        if (found > -1) and\
                        (self.GetStyleAt(self.GetLineEndPosition(linenum)-len(line)+found)==5) and\
                        (self.GetLineIndentation(linenum) == found):
                            ind = self.GetLineIndentation(linenum)
                            break
                        linenum -= 1
                        line = self.GetLine(linenum)
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
                            if self.GetStyleAt(start+linestart-1)==10:
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
        #the indent level of the opening, but that would require checking
        #multiple previous items for the opening item.
        #single-line dedent.
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
            a = max(ind+xtra*self.GetIndent(), 0)*' '
            
            if self.GetUseTabs():
                a = a.replace(self.GetTabWidth()*' ', '\t')
            ## self._tdisable(self.ReplaceSelection, self.format+a)
            self.ReplaceSelection(self.format+a)
    
    def OnSelectToggle(self, e):
        if self.selep is None:
            self.selep = self.GetCurrentPos()
        else:
            self.SetAnchor(self.selep)
            self.selep = None
    
    def _AddTextWAttr(self, start, end, text, attr):
        ## attr = attr % 3
        self.SetTargetStart(start)
        self.SetTargetEnd(end)
        self.ReplaceTarget(text)
        self.StartStyling(start, wxSTC_INDIC0_MASK)
        self.SetStyling(len(text), wxSTC_INDIC0_MASK)
        self.IndicatorSetStyle(wxSTC_INDIC0_MASK, wx.stc.STC_INDIC_BOX)
        self.IndicatorSetForeground(wxSTC_INDIC0_MASK, wx.RED)
    

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

VS = wx.VERSION_STRING

def main():
    docs = [os.path.abspath(os.path.join(current_path, i))
            for i in sys.argv[1:]]
    if single_instance.send_documents(docs):
        return
    
    global IMGLIST1, IMGLIST2, root, app
    app = wxPySimpleApp()
    IMGLIST1 = wxImageList(16, 16)
    IMGLIST2 = wxImageList(16, 16)
    for il in (IMGLIST1, IMGLIST2):
        for icf in ('icons/blank.ico', 'icons/py.ico'):
            icf = os.path.join(runpath, icf)
            img = wxImageFromBitmap(wxBitmap(icf)) 
            img.Rescale(16,16) 
            bmp = wxBitmapFromImage(img) 
            il.AddIcon(wxIconFromBitmap(bmp)) 

    opn=0
    if len(sys.argv)>1 and ('--last' in sys.argv):
        opn=1
    filehistory.root = root = app.frame = MainWindow(None, -1, "PyPE", docs)
    root.updateWindowTitle()
    app.SetTopWindow(app.frame)
    app.frame.Show(1)
    if opn:
        app.frame.OnOpenPrevDocs(None)
    app.frame.SendSizeEvent()
    app.MainLoop()

if __name__ == '__main__':
    main()
