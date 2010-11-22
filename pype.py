#!/usr/bin/env python

#------------ User-changable settings are available in the menus -------------
from __version__ import *

#------------------------ Startup/restart information ------------------------
import sys, os

if sys.platform == 'linux2' and 'DISPLAY' not in os.environ:
    raise SystemError('DISPLAY not set when importing or running pype')

if not hasattr(sys, 'frozen'):
    v = '2.8'
    import wxversion
    if '--unicode' in sys.argv:
        wxversion.ensureMinimal(v+'-unicode', optionsRequired=True)
    elif '--ansi' in sys.argv:
        wxversion.ensureMinimal(v+'-ansi', optionsRequired=True)
    else:
        wxversion.ensureMinimal(v)

DEBUG = '--debug' in sys.argv
_standalone = '--standalone' in sys.argv
USE_THREAD = 1#'--nothread' not in sys.argv

PRINTMACROS = 0
#get font size modifications
for i in sys.argv:
    if i.startswith('--fontsize='):
        try:
            FONTSIZE = int(i[11:])
        except:
            pass
        else:
            break

for i in sys.argv:
    if i.startswith('--port='):
        try:
            PORTNUM = int(i[11:])
        except:
            pass
        else:
            break

for i in sys.argv:
    if i.startswith('--font='):
        FONT = i[7:].replace('_', ' ').replace('-', ' ')
        break

USE_NEW = '--use_old_parser' not in sys.argv

def _restart(orig_path=os.getcwd(), orig_sysargv=sys.argv[:]):
    os.chdir(orig_path)
    args = [sys.executable] + orig_sysargv
    if len(spawnargs) == 1:
        _ = args.pop(0)

    os.execvp(args[0], args + ['--last'])

def keep(i):
    if i in ('--ansi', '--unicode', '--debug', '--nothread', '--macros', '--standalone'):
        return 0
    if i.startswith('--font=') or i.startswith('--fontsize=') or i.startswith('--port='):
        return 0
    return 1

sys.argv = [i for i in sys.argv if keep(i)]
#-------------- Create reference to this module in __builtins__ --------------
if isinstance(__builtins__, dict):
    __builtins__['_pype'] = sys.modules[__name__]
    __builtins__['USE_NEW'] = USE_NEW
else:
    __builtins__._pype = sys.modules[__name__]
    __builtins__.USE_NEW = USE_NEW
#------------------------------ System Imports -------------------------------
import bisect
import cStringIO
import fnmatch
import keyword
import imp
import md5
import pprint
import Queue
import random
import re
import stat
import string
import textwrap
import threading
import time
import traceback

#-------------------------------- wx imports ---------------------------------
import wx
if wx.VERSION[:4] == (2, 6, 3, 3) and not wx.USE_UNICODE:
    raise SystemError('''
    This version of wxPython (2.6.3.3 ansi) has known issues with pasting.  If you
    must use wxPython 2.6.3.3, please use wxPython 2.6.3.3 unicode and pass the
    --unicode command line option.
    '''.replace('    ', ''))

import wx.gizmos
import wx.lib.newevent

from wx import aui
_style = aui.AUI_NB_SCROLL_BUTTONS|aui.AUI_NB_TOP
from wx import stc
wxstc = stc
from wx.lib.dialogs import ScrolledMessageDialog
from wx.lib.mixins import listctrl
from wx.lib.rcsizer import RowColSizer
if DEBUG:
    try:
        from wx.py import crust
    except:
        print "Debugging console not available, try to source version of PyPE"

current_path = os.getcwd()
EFFECTUAL_NORMCASE = os.path.normcase('AbCdEf') == 'abcdef'
UNICODE = wx.USE_UNICODE

#--------------------- configuration and plugins imports ---------------------
from configuration import *

MAX_SAVE_STATE_DOC_SIZE = 0x400000 #2**22 bytes, a little over a 4 megs
MAX_SAVE_STATE_LINE_COUNT = 20000  #anything more than 4 megs or 20k lines

#change the standard font size
import StyleSetter
if 'FONTSIZE' in globals() or 'FONT' in globals():
    StyleSetter.fs = globals().get('FONTSIZE', StyleSetter.fs)
    StyleSetter.cn = globals().get('FONT', StyleSetter.cn)
    StyleSetter.update_faces()

from plugins import browser
from plugins import codetree
from plugins import documents
from plugins import filehistory
from plugins import filtertable
from plugins import findbar
from plugins import findinfiles
from plugins import help
from plugins import interpreter
from plugins import keydialog
from plugins import lineabstraction
from plugins import logger
from plugins import lru
from plugins import macro
from plugins import methodhelper
from plugins import parsers
from plugins import scheduler
from plugins import shell
from plugins import single_instance
if 'PORTNUM' in globals():
    single_instance.port = PORTNUM
from plugins import spellcheck
from plugins import textrepr
from plugins import todo
from plugins import triggerdialog
from plugins import window_management
from plugins.window_management import docstate, _choicebook
from plugins import workspace

#---------------------------- Event Declarations -----------------------------

class cancelled(Exception):
    pass

class pass_keyboard(cancelled):
    pass

def isdirty(win):
    if not isinstance(win, PythonSTC):
        return False
    if win.dirty:
        return True

    fn = win.root.getAlmostAbsolute(win.filename, win.dirname)
    dirty = 0
    if win.mod != None:
        try:
            mod = os.stat(fn)[8]
            dirty += mod != win.mod
        except:
            dirty += bool(win.dirname.strip())
    if dirty:
        win.MakeDirty()
    return bool(dirty)

for i in [logger, findbar, lru, filehistory, browser, workspace, todo,
          findinfiles, shell, textrepr, spellcheck, keydialog]:
    i.cancelled = cancelled
    i.isdirty = isdirty

#some definitions
if 1:
    STRINGPRINTABLE = dict.fromkeys(map(ord, string.printable))

    IDR = wx.NewId()
    DDR = wx.NewId()

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

    def GetKeyCode(evt):
        if 'unicode' in wx.PlatformInfo:
            return evt.GetUnicodeKey()
        return evt.GetKeyCode()
    if isinstance(__builtins__, dict):
        __builtins__['GetKeyCode'] = GetKeyCode
    else:
        __builtins__.GetKeyCode = GetKeyCode


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
        ## print menu.__class__, wx.MenuItem, wx.Menu,
        if isinstance(menu, wx.MenuBar):
            for i in xrange(menu.GetMenuCount()):
                r = menu.GetMenu(i)
                if r.FindItemById(id):
                    return "%s->%s"%(menu.GetLabelTop(i), recmenu(r, id))
        elif isinstance(menu, wx.Menu):
            ITEMS = menu.GetMenuItems()
            for i in ITEMS:
                a = recmenu(i, id)
                if a:
                    return a
            return ''
        elif isinstance(menu, wx.MenuItem):
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

    def menuAdd(root, menu, name, desc, funct, id, kind=wx.ITEM_NORMAL):

        a = wx.MenuItem(menu, id, 'TEMPORARYNAME', desc, kind)
        menu.AppendItem(a)
        wx.EVT_MENU(root, id, funct)

        ns, oacc = _spl(name)
        hier = recmenu(menuBar, id)[:-13] + ns
        if hier in MENUPREF:
            name, acc, acc2 = GETACC(MENUPREF[hier])
        else:
            if hier in OLD_MENUPREF:
                name, acc, acc2 = MENUPREF[hier] = GETACC(OLD_MENUPREF[hier])
            else:
                name, acc, acc2 = MENUPREF[hier] = GETACC((ns, oacc))

        MENULIST.append((hier, name, oacc, acc, kind in [wx.ITEM_NORMAL, wx.ITEM_CHECK], acc2))
        ## if type(acc) != type(acc2):
            ## acc2 = acc2.decode('latin-1')
        ## if acc != acc2:
            ## print "mismatched hotkey: %r %r"%(acc, acc2)

        if acc or acc2:
            HOTKEY_TO_ID[acc2] = id

        menuBar.SetLabel(id, '%s\t%s'%(name, acc))
        menuBar.SetHelpString(id, desc)

    def menuAddM(parent, menu, name, help=''):
        if isinstance(parent, wx.Menu):
            id = wx.NewId()
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
        image = wx.ImageFromStream(stream)
        bitmap = wx.BitmapFromImage(image)
        icon = wx.EmptyIcon()
        icon.CopyFromBitmap(bitmap)
        return icon

    NEWDOCUMENT = 0L

#document styling events
if 1:
    #style ids
    #         _S     0   _DS    1      2            3           _DD    4   _DD2   5      6
    ASSOC = [(wx.NewId(), wx.NewId(), 'pyrex',  stc.STC_LEX_PYTHON, wx.NewId(), wx.NewId(), "Pyrex"),
             #made Python second to override the lexer2lang option
             (wx.NewId(), wx.NewId(), 'python', stc.STC_LEX_PYTHON, wx.NewId(), wx.NewId(), "Python"),
             (wx.NewId(), wx.NewId(), 'html',   stc.STC_LEX_HTML,   wx.NewId(), wx.NewId(), "HTML"),
             (wx.NewId(), wx.NewId(), 'xml',    stc.STC_LEX_XML,    wx.NewId(), wx.NewId(), "XML"),
             (wx.NewId(), wx.NewId(), 'cpp',    stc.STC_LEX_CPP,    wx.NewId(), wx.NewId(), "C/C++"),
             (wx.NewId(), wx.NewId(), 'text',   stc.STC_LEX_NULL,   wx.NewId(), wx.NewId(), "Text"),
             (wx.NewId(), wx.NewId(), 'tex',    stc.STC_LEX_LATEX,  wx.NewId(), wx.NewId(), "TeX/LaTeX")]

    SITO = [i[4] for i in ASSOC]
    SITO2 = [i[5] for i in ASSOC]
    ## PY_S,   PYX_S,   HT_S,   XM_S,   CC_S,   TX_S,   TEX_S   = [i[0] for i in ASSOC]
    ## PY_DS,  PYX_DS,  HT_DS,  XM_DS,  CC_DS,  TX_DS,  TEX_DS  = [i[1] for i in ASSOC]
    ## PY_DD,  PYX_DD,  HT_DD,  XM_DD,  CC_DD,  TX_DD,  TEX_DD  = SITO
    ## PY_DD2, PYX_DD2, HT_DD2, XM_DD2, CC_DD2, TX_DD2, TEX_DD2 = SITO2

    lexers =      dict([(i[0],i[2]) for i in ASSOC])
    lexers2 =     dict([(i[2],i[0]) for i in ASSOC])
    lexers.update(dict([(i[1],i[2]) for i in ASSOC]))
    lexers3 =     dict([(i[2],i[1]) for i in ASSOC])
    lexer2lang =  dict([(i[3],i[2]) for i in ASSOC])

    SOURCE_ID_TO_OPTIONS  = dict([(i[4], (i[2], i[6])) for i in ASSOC])
    SOURCE_ID_TO_OPTIONS2 = dict([(i[5], (i[2], i[6])) for i in ASSOC])
    ASSOC.insert(1, ASSOC.pop(0))

#checkbox ids
if 1:
    AUTO = wx.NewId()
    FETCH_M = wx.NewId()
    NUM = wx.NewId()
    MARGIN = wx.NewId()
    USETABS = wx.NewId()
    INDENTGUIDE = wx.NewId()
    WRAPL = wx.NewId()
    SLOPPY = wx.NewId()
    SMARTPASTE = wx.NewId()
    SAVE_CURSOR = wx.NewId()
    HIGHLIGHT_LINE = wx.NewId()
    IMAGE_BUTTONS = wx.NewId()
    S_WHITE = wx.NewId()
    S_LEND = wx.NewId()
    DND_ID = wx.NewId()
    DB_ID = wx.NewId()
    IT_ID = wx.NewId()
    METH_C_ID = wx.NewId()
    LB_ID = wx.NewId()
    WIDE_ID = wx.NewId()
    TALL_ID = wx.NewId()
    SINGLE_ID = wx.NewId()
    USEBOM_ID = wx.NewId()
    ONE_TAB = wx.NewId()
    TD_ID = wx.NewId()
    STRICT_TODO_ID = wx.NewId()
    FINDBAR_BELOW_EDITOR = wx.NewId()
    NO_FINDBAR_HISTORY = wx.NewId()
    CLEAR_FINDBAR_HISTORY = wx.NewId()
    ZI = wx.NewId()
    SHOW_RECENT = wx.NewId()
    SHOW_SEARCH = wx.NewId()
    SHOW_MIST = wx.NewId()

    TRIGGER = wx.NewId()

    REC_MACRO = wx.NewId()


    #toolbar ids

    TB_MAPPING = {
        wx.NewId(): (0, 'Hide', "Don't show the toolbar (requires restart)"),
        wx.NewId(): (1, 'Top',  "Show the toolbar accross the top horizontally (requires restart)"),
        wx.NewId(): (2, 'Left', "Show the toolbar along the left side vertically (requires restart)")
    }
    TB_RMAPPING = dict([(j[0], (j[0], i, j[1], j[2])) for i,j in TB_MAPPING.iteritems()])

    #line ending ids
    LE_MAPPING = {
        wx.NewId():(stc.STC_EOL_CRLF, 0, "CRLF (windows)", "Change the line endings for the current document to CRLF/Windows line endings"),
        wx.NewId():(stc.STC_EOL_LF,   1, "LF (*nix)",      "Change the line endings for the current document to LF/*nix line endings"),
        wx.NewId():(stc.STC_EOL_CR,   2, "CR (mac)",       "Change the line endings for the current document to CR/Macintosh line endings")
    }
    LE_RMAPPING = dict([(j[0], (j[1], i, j[2], j[3])) for i,j in LE_MAPPING.iteritems()])

    #long line indicator ids
    LL_MAPPING = {
        wx.NewId():(stc.STC_EDGE_BACKGROUND, 0, "Background", "Long lines will have a different background color beyond the column limit"),
        wx.NewId():(stc.STC_EDGE_LINE,       1, "Line", "Long lines will have a vertical line at the column limit"),
        wx.NewId():(stc.STC_EDGE_NONE,       2, "None", "Show no long line indicator")
    }

    LL_RMAPPING = dict([(j[0],(j[1], i, j[2], j[3])) for i,j in LL_MAPPING.iteritems()])

    #cursor behavior ids
    CARET_ID_TO_OPTIONS = {
        wx.NewId()        : (0, stc.STC_CARET_EVEN|stc.STC_CARET_SLOP|stc.STC_CARET_STRICT, 1, "Margin Respecting", "Caret is at least M lines from the top and bottom, N*M pixels from the right and left"),
        wx.NewId()        : (1, stc.STC_CARET_EVEN|stc.STC_CARET_STRICT, 4, "Centered", "Caret is centered on the display, if possible"),
        wx.NewId()        : (2, stc.STC_CARET_STRICT, 3, "Top Attached", "Caret is always on the top line, if possible"),
        wx.NewId()        : (3, stc.STC_CARET_SLOP|stc.STC_CARET_STRICT, 2, "Margin Attached", "Caret is always M lines from the top, and N*M pixels from the right, if possible"),
        wx.NewId()        : (4, stc.STC_CARET_EVEN, 0, "PyPE Classic", "Caret is at least 1 line from the top and bottom, 10 pixels from the right and left"),
    }

    CARET_OPTION_TO_ID = dict([(j[0], (i, j[1])) for i,j in CARET_ID_TO_OPTIONS.iteritems()])

    #caret width option

    CARET_W_OPTION_TO_W = dict([(wx.NewId(), i) for i in (1,2,3)])
    CARET_W_WIDTH_TO_O = dict([(j,i) for i,j in CARET_W_OPTION_TO_W.iteritems()])

    #title display ids

    TITLE_ID_TO_OPTIONS = {
        wx.NewId()           : (0, "%(pype)s",                       "No file information"),
        wx.NewId()           : (1, "%(pype)s - %(fn)s",              "File name after title"),
        wx.NewId()           : (2, "%(fn)s - %(pype)s",              "File name before title"),
        wx.NewId()           : (3, "%(pype)s - %(fn)s - [%(long)s]", "File and full path after title"),
        wx.NewId()           : (4, "%(fn)s - [%(long)s] - %(pype)s", "File and full path before title"),
    }

    TITLE_OPTION_TO_ID = dict([(j[0], (i, j[1], j[2])) for i,j in TITLE_ID_TO_OPTIONS.iteritems()])

    #for determining what to display in the Documents tab.
    DOCUMENT_LIST_OPTIONS = {
        wx.NewId() : (1, "Filename"),
        wx.NewId() : (3, "Filename, Path"),
        wx.NewId() : (2, "Path"),
        wx.NewId() : (0, "Path, Filename")
    }

    DOCUMENT_LIST_OPTION_TO_ID = dict([(j[0], i) for i,j in DOCUMENT_LIST_OPTIONS.items()])

    DOCUMENT_LIST_OPTIONS2 = {
        wx.NewId() : (1, "Filename"),
        wx.NewId() : (3, "Filename, Path"),
        wx.NewId() : (2, "Path"),
        wx.NewId() : (0, "Path, Filename")
    }

    DOCUMENT_LIST_OPTION_TO_ID2 = dict([(j[0], i) for i,j in DOCUMENT_LIST_OPTIONS2.items()])


    #for determining what to do when double-clicking on a macro.
    MACRO_CLICK_OPTIONS = {
        wx.NewId() : (0, "do nothing"),
        wx.NewId() : (1, "open for editing"),
        wx.NewId() : (2, "run macro")
    }

    MACRO_CLICK_TO_ID = dict([(j[0], i) for i,j in MACRO_CLICK_OPTIONS.iteritems()])

    PYTHON_INTERPRETER_CHOICES = []

    #for determining what kind of indicator to show in shell output.
    SHELL_OUTPUT_OPTIONS = {
        wx.NewId(): (0, "no indicator", stc.STC_INDIC_HIDDEN),
        wx.NewId(): (1, "plain underline", stc.STC_INDIC_PLAIN),
        wx.NewId(): (2, "squiggle underline", stc.STC_INDIC_SQUIGGLE),
        wx.NewId(): (3, "TT underline", stc.STC_INDIC_TT),
        wx.NewId(): (4, "box outline", stc.STC_INDIC_BOX)
    }

    try:
        SHELL_OUTPUT_OPTIONS[wx.NewId()] = (5, "round box outline", stc.STC_INDIC_ROUNDBOX)
    except:
        pass

    SHELL_NUM_TO_ID = dict([(j,i) for i,(j,k,l) in SHELL_OUTPUT_OPTIONS.iteritems()])
    SHELL_NUM_TO_INDIC = dict([(j,l) for i,(j,k,l) in SHELL_OUTPUT_OPTIONS.iteritems()])

    #for determining how often to check syntax
    SYNTAX_CHECK_DELAY_L = [
        (wx.NewId(), -1, "never"),
        (wx.NewId(), 0, "at most every 5 seconds"),
        (wx.NewId(), 1, "at most every 20 seconds"),
        (wx.NewId(), 2, "at most every 2 minutes")
    ]

    SYNTAX_CHECK_DELAY_NUM_TO_ID = dict([(j,i) for i,j,k in SYNTAX_CHECK_DELAY_L])
    SYNTAX_CHECK_DELAY_ID_TO_NUM = dict([(i,j) for i,j,k in SYNTAX_CHECK_DELAY_L])

    #for determining how often to "refresh" automatically
    REFRESH_DELAY_L = [(wx.NewId(), j, k) for i,j,k in SYNTAX_CHECK_DELAY_L]
    REFRESH_DELAY_NUM_TO_ID = dict([(j,i) for i,j,k in REFRESH_DELAY_L])
    REFRESH_DELAY_ID_TO_NUM = dict([(i,j) for i,j,k in REFRESH_DELAY_L])

    _MULT = (5, 20, 120, 5)
    _MULT2 = (5, 5, 5, 5)

    #for turning tools on or off
    TOOLS_ENABLE_L = [
        (wx.NewId(), 'Name', 'source tree ordered by name', 'leftt', 'tree1'),
        (wx.NewId(), 'Line', 'source tree ordered by line number', 'rightt', 'tree2'),
        (wx.NewId(), 'Filter', 'filterable definition list', 'filterl', 'filter'),
        (wx.NewId(), 'Todo', 'todo listing', 'todot', 'todo'),
        ## (wx.NewId(), 'Tags', 'tagged definition filter', 'taglist', 'sourcetags'),
        ## (wx.NewId(), 'TagM', 'definition tag manager', 'tagmanage', 'tagger'),
        (wx.NewId(), 'Global Filter', 'global filterable definition list', 'ignore', 'ignore'),
    ]

    TOOLS_ENABLE = dict([(j[0], i) for i,j in enumerate(TOOLS_ENABLE_L)])
    TOOLS_ENABLE_LKP = dict([(i[3], i[4]) for i in TOOLS_ENABLE_L])

    #bookmark support
    BOOKMARKNUMBER = 1
    BOOKMARKSYMBOL = stc.STC_MARK_CIRCLE
    BOOKMARKMASK = 2


#unicode BOM stuff
if 1:
    BOM = [('+/v8-', 'utf-7'),
          ('\xef\xbb\xbf', 'utf-8'),
          ('\xfe\xff', 'utf-16-be'),
          ('\xff\xfe', 'utf-16-le'),
          ('', 'ascii'),
          ('', 'other')]
    try:
        _ = u'\ufeff'.encode('utf-32')
    except:
        pass
    else:
        BOM.insert(2, ('\xff\xfe\0\0', 'utf-32-le'))
        BOM.insert(3, ('\0\0\xfe\xff', 'utf-32-be'))

    ADDBOM = {}
    ENCODINGS = {}
    for i,j in BOM:
        ADDBOM[j] = i
        ENCODINGS[j] = wx.NewId()
    del i;del j;

#font stuff
if 1:
    cn = 'Courier New'
    if wx.Platform == '__WXMSW__':
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
        win = wx.SashLayoutWindow(
                parent, id, wx.DefaultPosition, size,
                wx.NO_BORDER|wx.SW_3D
                )
        win.SetDefaultSize(size)
        win.SetOrientation(orientation)
        win.SetAlignment(alignment)
        ## win.SetBackgroundColour(wx.Colour(127, 0, 0))
        win.SetSashVisible(sash, True)
        ## win.SetMinimumSizeX(30)
        return win

    #subwindow ids
    ID_WINDOW_BOTTOM = wx.NewId()
    ID_WINDOW_RIGHT = wx.NewId()

    #subwindow constants
    SMALL = 10
    BIG = 10000

    DB_LOC = {0:(wx.LAYOUT_LEFT, wx.SASH_RIGHT),
              1:(wx.LAYOUT_RIGHT, wx.SASH_LEFT)}

    LB_LOC = {0:(wx.LAYOUT_TOP, wx.SASH_BOTTOM),
              1:(wx.LAYOUT_BOTTOM, wx.SASH_TOP)}

#findbar ids
if 1:

    pypeID_DELETE = wx.NewId()
    pypeID_FINDBAR = wx.NewId()
    pypeID_REPLACEBAR = wx.NewId()
    pypeID_TOGGLE_BOOKMARK = wx.NewId()
    pypeID_NEXT_BOOKMARK = wx.NewId()
    pypeID_PRIOR_BOOKMARK = wx.NewId()

#extension to image map
EXT_TO_IMG = {'python':1, 'pyrex':1}
def GDI(name):
    if USE_DOC_ICONS:
        ext = name.split('.')[-1].lower()
        if ext in ('spt', 'tmpl'):
            return 0
        return EXT_TO_IMG.get(extns.get(ext, 0), 0)
    return -1
#

def get_filetype(fn):
    return extns.get(fn.split('.')[-1].lower(), 'python')

def GetClipboardText():
    success = False
    do = wx.TextDataObject()
    if wx.TheClipboard.Open():
        success = wx.TheClipboard.GetData(do)
        wx.TheClipboard.Close()

    if success:
        return do.GetText()
    return None

def SetClipboardText(txt):
    do = wx.TextDataObject()
    do.SetText(txt)
    if wx.TheClipboard.Open():
        wx.TheClipboard.SetData(do)
        wx.TheClipboard.Close()
        return 1
    return 0

RESET = {'cursor_posn':0,
         'BM':[],
         'FOLD':[]}

#threaded parser
if 1:
    parse_queue = Queue.Queue()
    _cheetah_re = re.compile('#(extends|block|end if|end block|end def)')

    DoneParsing, EVT_DONE_PARSING = wx.lib.newevent.NewEvent()

    def _parse(lang, source, le, which, x, slowparse=0):
        source = source.replace('\r\n', '\n').replace('\r', '\n')
        le = '\n'
        if lang in ('python', 'pyrex'):
            if _cheetah_re.search(source):
                return parsers.cheetah_parser(source, le, which, x)
            
            elif slowparse:
                try:
                    return parsers.fast_parser(source, le, which, x)
                except:
                    traceback.print_exc()
                    pass
                    
            return parsers.faster_parser(source, le, which, x)
        elif lang == 'tex':
            return parsers.latex_parser(source, le, which, x)
        elif lang == 'cpp':
            return parsers.c_parser(source, le, which, x)
        elif lang in ('xml', 'html'):
            return parsers.ml_parser(source, le, which, x)
        else:
            return [], [], {}, []

    def parse(lang, source, le, which, x, slowparse=0):
        r = _parse(lang, source, le, which, x, slowparse)
        r2 = [] #parsers._get_tags(r[0], r[-1])
        return r + (r2,)

    def parse_thread(frame, startthread=1):
        if startthread:
            a = threading.Thread(target=parse_thread, args=(frame,0))
            a.start()
            return
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
                wx.PostEvent(frame, DoneParsing(stc=stc, tpl=tpl, delta=t))
            except:
                # the main frame has closed
                break

    file_mods_to_check = Queue.Queue()
    def check_files(frame, startthread=1):
        if startthread:
            x = threading.Thread(target=check_files, args=(frame, 0))
            x.start()
            return
        lastcheck = None
        while 1:
            request_time, files_to_check = file_mods_to_check.get()
            while not file_mods_to_check.empty():
                # if the current list isn't the last list, get a more
                # up-to-date list
                request_time, files_to_check = file_mods_to_check.get()
            if files_to_check is None:
                break
            curcheck = time.time()
            if not lastcheck:
                lastcheck = time.time()-61
            if request_time and curcheck - lastcheck < 60:
                # don't re-check more than once a minute
                continue
            for f in files_to_check:
                fn = f[0]
                try:
                    f.append(os.stat(fn)[8])
                except:
                    f.append(None)
                    f.append(None)
                else:
                    try:
                        f.append(md5.new(open(fn, 'rb').read()).digest())
                    except:
                        f[-1:] = [None, None]
            lastcheck = curcheck
            try:
                if request_time and time.time()-request_time > 30:
                    # it took us more than 30 seconds to check...
                    # the check probably isn't valid.
                    # we'll wait for another check request
                    continue
                wx.CallAfter(frame.CheckedDocMods, files_to_check)
            except:
                # the main frame has closed
                break

sys_excepthook = sys.excepthook

def my_excepthook(typ, inst, trace):
    if typ is cancelled or typ is pass_keyboard:
        return
    return sys_excepthook(typ, inst, trace)

sys.excepthook = my_excepthook

def veto(*args):
    args[-1].Veto()

start_use = time.time()
end_use = time.time()

def _to_str(i):
    if isinstance(i, unicode):
        return i.encode('utf-8')
    else:
        return i

def do_nothing(*args):
    return

NULLDOC = None

def auto_thaw(method):
    def wrapper(self, *args, **kwargs):
        self.Freeze()
        try:
            return method(self, *args, **kwargs)
        finally:
            self.Thaw()
        wx.Yield()
    wrapper.__name__ = method.__name__
    return wrapper

#---------------------- Frame that contains everything -----------------------
class MainWindow(wx.Frame):
    def __init__(self,parent,id,title,fnames):
        wx.Frame.__init__(self,parent,id, title, size = ( 1024, 600 ),
                         style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE)
        self.starting = 1
        self.redirect = methodhelper.MethodHelper(self)
        global root
        root = self

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
            try:    OLD_MENUPREF.update(unrepr(open(path, 'r').read()))
            except: pass

            single_instance.callback = self.OnDrop

            #recent menu relocated to load configuration early on.
            recentmenu = wx.Menu()
#--------------------------- cmt-001 - 08/06/2003 ----------------------------
#----------------- Adds opened file history to the File menu -----------------
        if 1:
            self.fileHistory = wx.FileHistory()
            self.fileHistory.UseMenu(recentmenu)
            self.configPath = homedir
            self.loadHistory()
            self.Maximize(LASTWINDOWSTATE)
            self.SetSize(LASTSIZE)
            self.SetPosition(LASTPOSITION)
            wx.Yield()
            self.restart = 0
            self.restartt = 0
            wx.EVT_MENU_RANGE(self, wx.ID_FILE1, wx.ID_FILE9, self.OnFileHistory)
            self.lastused = lru.lastused(128+len(lastopen), LASTUSED)
            self.curdocstates = {}

            window_management.enabled = dict.fromkeys([i for i in window_management.possible if i not in disabled_tools])
#------------------------- end cmt-001 - 08/06/2003 --------------------------
        self.toparse = []
        self.parsing = 0

        try:
            ## typ = wx.ITEM_RADIO
            typ = wx.ITEM_CHECK
            self.HAS_RADIO = 1
        except:
            typ = wx.ITEM_NORMAL
            self.HAS_RADIO = 0

#------------------------------- window layout -------------------------------
        if 1:
            self.sb = wx.StatusBar(self, -1)
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

            # Setting up the menu


            ## bottom = makeSubWindow(self, ID_WINDOW_BOTTOM, (BIG, SASH1),
                                ## wx.LAYOUT_HORIZONTAL,
                                ## *LB_LOC[logbarlocn])

            ## right = makeSubWindow(self, ID_WINDOW_RIGHT, (SASH2, BIG),
                                ## wx.LAYOUT_VERTICAL,
                                ## *DB_LOC[docbarlocn])

            bottom = self.client2 = SplitterWindow(self, -1, style=wx.SP_NOBORDER)

            right = self.client = SplitterWindow(bottom, -1, style=wx.SP_NOBORDER)
            self.control = documents.MyNB(self, -1, self.client)


            self.BOTTOM = bottom
            self.RIGHT = right

            ## self.BOTTOMNB = wx.Notebook(bottom, -1)
            self.BOTTOMNB = aui.AuiNotebook(bottom, -1, style=_style)
            ## self.RIGHTNB = wx.Notebook(right, -1)
            self.RIGHTNB = aui.AuiNotebook(right, -1, style=_style)
            bottom.SplitHorizontally(right, self.BOTTOMNB, -SASH1, not logbarlocn)
            wx.Yield()
            right.SplitVertically(self.control, self.RIGHTNB, -SASH2, not docbarlocn)
            wx.Yield()
            ## self.RIGHTNB.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, browser.ChangedPage)
            self.RIGHTNB.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, browser.ChangedPage)

            self.docpanel, self.dragger = documents._MyLC(self.RIGHTNB, self)

            if DEBUG:
                self.crust = crust.Crust(self.RIGHTNB, rootObject=app,
                    rootLabel='main', execStartupScript=False)
                self.RIGHTNB.AddPage(self.crust, "DEBUG")

            y = [('Name', 'leftt'), ('Line','rightt'), ('Filter', 'filterl'), ('Todo','todot')]#, ('Tags', 'taglist'), ('TagM', 'tagmanage')]
            if ONE_TAB_:
                self.single_ctrl = wx.Choicebook(self.RIGHTNB, -1)
                self.RIGHTNB.AddPage(self.single_ctrl, "Tools")
            for name,i in y:
                if ONE_TAB_:
                    ctrl = self.single_ctrl
                elif TODOBOTTOM and name == 'Todo':
                    ctrl = self.BOTTOMNB
                else:
                    ctrl = self.RIGHTNB
                x = _choicebook(ctrl, -1)
                if TOOLS_ENABLE_LKP[i] in window_management.enabled:
                    ctrl.AddPage(x, name)
                setattr(self, i, x)

            self.gf = filtertable.GlobalFilter(self.RIGHTNB, self)
            self.gfp = self.RIGHTNB.GetPageCount()
            if global_filter_table:
                self.RIGHTNB.AddPage(self.gf, "GlobalF")
            else:
                self.gf.Hide()

            self.macropage = macro.macroPanel(self.RIGHTNB, self)
            self.RIGHTNB.AddPage(self.macropage, "Macros")

            self.BOTTOMNB.AddPage(logger.logger(self.BOTTOMNB), 'Log')
            ## self.BOTTOMNB.AddPage(findinfiles.FindInFiles(self.BOTTOMNB, self), "Find in Files")
            self.findinfiles = findinfiles.FindInFiles(self.BOTTOMNB, self)
            self.BOTTOMNB.AddPage(self.findinfiles, "Search")
            self.BOTTOMNB.AddPage(spellcheck.SpellCheck(self.BOTTOMNB, self), "Spell Check")
            ## self.shell = shell.Shell(self.BOTTOMNB, self, self.config.get('shellprefs', {}))
            ## self.BOTTOMNB.AddPage(self.shell, "Shell")
            if UNICODE:
                self.BOTTOMNB.AddPage(textrepr.TextRepr(self.BOTTOMNB, self), "repr(text)")
            self.BOTTOMNB.AddPage(help.MyHtmlWindow(self.BOTTOMNB), "Help")

            self.RIGHTNB.AddPage(self.docpanel, 'Documents')
            self.pathmarks = browser.FilesystemBrowser(self.RIGHTNB, self, pathmarksn)
            self.RIGHTNB.AddPage(self.pathmarks, "Browse...")
            self.altview = View(self.BOTTOMNB, wx.NewId(), self.BOTTOMNB)
            self.BOTTOMNB.AddPage(self.altview, "Split")
            self.altview2 = View(self.RIGHTNB, wx.NewId(), self.RIGHTNB)
            self.RIGHTNB.AddPage(self.altview2, "Split")
            global NULLDOC
            NULLDOC = self.altview.GetDocPointer()
            self.altview.AddRefDocument(NULLDOC)

#------------------------- Insert menus into Menubar -------------------------
        global menuBar
        menuBar = wx.MenuBar()

        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
        self.menubar = menuBar

#--------------------------------- File Menu ---------------------------------
        if 1:
            filemenu= wx.Menu()
            menuAddM(menuBar, filemenu, "&File")
            menuAdd(self, filemenu, "&New\tCtrl+N",         "New file", self.OnNew, wx.ID_NEW)
            menuAdd(self, filemenu, "&Open\tCtrl+O",        "Open a file", self.OnOpen, wx.ID_OPEN)
            menuAdd(self, filemenu, "Open &Module\tAlt+M",  "Open a module for editing using the same path search as import would", self.OnOpenModule, wx.NewId())
            menuAdd(self, filemenu, "Open &Last\t",         "Open all the documents that were opening before last program exit", self.OnOpenPrevDocs, wx.NewId())
            menuAddM(filemenu, recentmenu, "Open Recent")
            filemenu.AppendSeparator()
            menuAdd(self, filemenu, "&Save\tCtrl+S",        "Save a file", self.OnSave, wx.ID_SAVE)
            menuAdd(self, filemenu, "Save &As",             "Save a file as...", self.OnSaveAs, wx.ID_SAVEAS)
            menuAdd(self, filemenu, "Sa&ve All",            "Save all open files...", self.OnSaveAll, wx.NewId())
            menuAdd(self, filemenu, "Save Copy As",         "Save a copy of the current file as...", self.OnSaveCopyAs, wx.NewId())
            filemenu.AppendSeparator()
            menuAdd(self, filemenu, "New Python Shell",     "Opens a Python shell in a new tab", self.OnNewPythonShell, wx.NewId())
            menuAdd(self, filemenu, "New Command Shell",    "Opens a command line shell in a new tab", self.OnNewCommandShell, wx.NewId())
            menuAdd(self, filemenu, "Run Current File",     "Runs the current file", self.OnRunCurrentFile, wx.NewId())
            menuAdd(self, filemenu, "Run Current File -i",  "Runs the current file, passing -i to the command line for Python documents", self.OnRunCurrentFileI, wx.NewId())
            menuAdd(self, filemenu, "Run Selected Code",    "Runs the currently selected code in a Python shell", self.OnRunSelected, wx.NewId())
            filemenu.AppendSeparator()
            menuAdd(self, filemenu, "Add Module Search Path", "Add a path to search during subsequent 'Open Module' executions", self.AddSearchPath, wx.NewId())
            menuAdd(self, filemenu, "&Reload",              "Reload the current document from disk", self.OnReload, wx.ID_REVERT)
            menuAdd(self, filemenu, "Check Mods\tShift+F5", "Check to see if any files have been modified", self.OnCheckMods, wx.NewId())
            menuAdd(self, filemenu, "&Close\tCtrl+W",       "Close the file in this tab", self.OnClose, wx.ID_CLOSE)
            workspace.WorkspaceMenu(filemenu, self, workspaces, workspace_order)
            menuAdd(self, filemenu, "Restart",              "Restart PyPE", self.OnRestart, wx.NewId())
            menuAdd(self, filemenu, "E&xit\tAlt+F4",        "Terminate the program", self.OnExit, wx.NewId())

#--------------------------------- Edit Menu ---------------------------------
        if 1:
            editmenu= wx.Menu()
            menuAddM(menuBar, editmenu, "&Edit")
            menuAdd(self, editmenu, "Undo\tCtrl+Z",         "Undo last modifications", self.OnUndo, wx.ID_UNDO)
            menuAdd(self, editmenu, "Redo\tCtrl+Y",         "Redo last modifications", self.OnRedo, wx.ID_REDO)
            editmenu.AppendSeparator()
            menuAdd(self, editmenu, "Select All\tCtrl+A",   "Select all text", self.OnSelectAll, wx.NewId())
            menuAdd(self, editmenu, "Start/End Selection",  "Will allow you to set selection start and end positions without holding shift", self.redirect.OnSelectToggle, wx.NewId())
            menuAdd(self, editmenu, "Cut\tCtrl+X",          "Cut selected text", self.OnCut, wx.ID_CUT)
            menuAdd(self, editmenu, "Copy\tCtrl+C",         "Copy selected text", self.OnCopy, wx.ID_COPY)
            menuAdd(self, editmenu, "Paste\tCtrl+V",        "Paste clipboard text", self.OnPaste, wx.ID_PASTE)
            menuAdd(self, editmenu, "Delete",               "Delete selected text", self.OnDeleteSelection, pypeID_DELETE)
            editmenu.AppendSeparator()
            menuAdd(self, editmenu, "PasteAndDown",         "Paste clipboard text and move cursor down", self.OnPasteAndDown, wx.NewId())
            menuAdd(self, editmenu, "Paste Rectangular",    "Paste clipboard text as a rectangle", self.OnPasteRectangular, wx.NewId())
            menuAdd(self, editmenu, "Delete Right",         "Delete from caret to end of line", self.OnDeleteRight, wx.NewId())
            menuAdd(self, editmenu, "Delete Line",          "Delete current line", self.OnDeleteLine, wx.NewId())
            editmenu.AppendSeparator()
            menuAdd(self, editmenu, "Show Find Bar\tCtrl+F", "Shows the find bar at the bottom of the editor", self.OnShowFindbar, pypeID_FINDBAR)
            menuAdd(self, editmenu, "Show Replace Bar\tCtrl+R", "Shows the replace bar at the bottom of the editor", self.OnShowReplacebar, pypeID_REPLACEBAR)
            menuAdd(self, editmenu, "Find again\tF3",        "Finds the text in the find bar again", self.OnFindAgain, wx.NewId())
            ## editmenu.AppendSeparator()
            ## if self.config['usesnippets']:
                ## menuAdd(self, editmenu, "Insert Snippet\tCtrl+return", "Insert the currently selected snippet into the document", self.snippet.OnListBoxDClick, wx.NewId())

#------------------------------ Transform Menu -------------------------------
        if 1:
            transformmenu= wx.Menu()
            menuAddM(menuBar, transformmenu, "&Transforms")

            menuAdd(self, transformmenu, "Indent Region\tCtrl+]", "Indent region", self.redirect.OnIndent, IDR)
            menuAdd(self, transformmenu, "Dedent Region\tCtrl+[", "Dedent region", self.redirect.OnDedent, DDR)
            menuAdd(self, transformmenu, "Wrap Selected Text\tAlt+W", "Wrap selected text to a specified width", self.redirect.OnWrap, wx.NewId())
            transformmenu.AppendSeparator()
            menuAdd(self, transformmenu, "Insert Comment\tCtrl+I", "Insert a centered comment", self.redirect.OnInsertComment, wx.NewId())
            menuAdd(self, transformmenu, "Comment Selection\tAlt+8", "Comment selected lines", self.redirect.OnCommentSelection, wx.NewId())
            menuAdd(self, transformmenu, "Uncomment Selection\tAlt+9", "Uncomment selected lines", self.redirect.OnUncommentSelection, wx.NewId())
            transformmenu.AppendSeparator()
            menuAdd(self, transformmenu, "Wrap try/except", "Wrap the selected code in a try/except clause", self.redirect.WrapExcept, wx.NewId())
            menuAdd(self, transformmenu, "Wrap try/finally", "Wrap the selected code in a try/finally clause", self.redirect.WrapFinally, wx.NewId())
            menuAdd(self, transformmenu, "Wrap try/except/finally", "Wrap the selected code in a try/except/finally clause", self.redirect.WrapExceptFinally, wx.NewId())
            transformmenu.AppendSeparator()
            menuAdd(self, transformmenu, "Tabs to Spaces", "Convert leading tabs to spaces", self.redirect.convertLeadingTabsToSpaces, wx.NewId())
            menuAdd(self, transformmenu, "Spaces to Tabs", "Convert leading spaces to tabs", self.redirect.convertLeadingSpacesToTabs, wx.NewId())
            transformmenu.AppendSeparator()
            menuAdd(self, transformmenu, "Perform Trigger", "Performs a trigger expansion if possible", self.redirect.OnTriggerExpansion, TRIGGER)

#--------------------------------- View Menu ---------------------------------
        if 1:
            viewmenu= wx.Menu()
            menuAddM(menuBar, viewmenu,"&View")
            menuAdd(self, viewmenu, "Previous Tab\tAlt+,", "View the tab to the left of the one you are currently", self.OnLeft, wx.NewId())
            menuAdd(self, viewmenu, "Next Tab\tAlt+.", "View the tab to the right of the one you are currently", self.OnRight, wx.NewId())
            viewmenu.AppendSeparator()
            menuAdd(self, viewmenu, "Zoom In\tCtrl++", "Make the text in the editing component bigger", self.OnZoom, ZI)
            menuAdd(self, viewmenu, "Zoom Out\tCtrl+-", "Make the text in the editing component smaller", self.OnZoom, wx.NewId())
            viewmenu.AppendSeparator()
            menuAdd(self, viewmenu, "Go to line number\tAlt+G", "Advance to the given line in the currently open document", self.OnGoto, wx.NewId())
            menuAdd(self, viewmenu, "Go to position", "Advance to the given position in the currently open document", self.OnGotoP, wx.NewId())
            menuAdd(self, viewmenu, "Jump forward", "Advance the cursor to the next quote/bracket", self.redirect.OnJumpF, wx.NewId())
            menuAdd(self, viewmenu, "Jump backward", "Advance the cursor to the previous quote/bracket", self.redirect.OnJumpB, wx.NewId())
            viewmenu.AppendSeparator()
            menuAdd(self, viewmenu, "Toggle Bookmark\tCtrl+M", "Create/remove bookmark for this line", self.OnToggleBookmark, pypeID_TOGGLE_BOOKMARK)
            menuAdd(self, viewmenu, "Next Bookmark\tF2", "Hop to the next bookmark in this file", self.OnNextBookmark, pypeID_NEXT_BOOKMARK)
            menuAdd(self, viewmenu, "Previous Bookmark\tShift+F2", "Hop to the previous bookmark in this file", self.OnPreviousBookmark, pypeID_PRIOR_BOOKMARK)
            viewmenu.AppendSeparator()
            menuAdd(self, viewmenu, "Find Definition", "Shows the filter tool and tries to find the current word in the definitions", self.OnFindDefn, wx.NewId())
            viewmenu.AppendSeparator()
            menuAdd(self, viewmenu, "Split Wide", "Shows an alternate view of the current document in the wide tools", self.OnSplitW, wx.NewId())
            menuAdd(self, viewmenu, "Split Tall", "Shows an alternate view of the current document in the tall tools", self.OnSplitT, wx.NewId())
            menuAdd(self, viewmenu, "Unsplit", "Removes all document views", self.OnUnsplit, wx.NewId())


#------------------------------- Document menu -------------------------------
        if 1:

            setmenu= wx.Menu()
            menuAddM(menuBar, setmenu, "&Document")
            ## menuAdd(self, setmenu, "Use Snippets (req restart)", "Enable or disable the use of snippets, requires restart for change to take effect", self.OnSnipToggle, SNIPT, wx.ITEM_CHECK)
            ## setmenu.AppendSeparator()

            #------------------------------ Style subenu ---------------------
            stylemenu= wx.Menu()
            menuAddM(setmenu, stylemenu, "Syntax Highlighting", "Change the syntax highlighting for the currently open document")
            for i in ASSOC:
                name, mid = i[6], i[0]
                st = "Highlight for %s syntax"%name
                if name == 'Text':
                    st = "No Syntax Highlighting"

                menuAdd(self, stylemenu, name, st, self.OnStyleChange, mid, typ)

            #---------------------------- Encodings submenu ------------------
            if UNICODE:
                encmenu= wx.Menu()
                menuAddM(setmenu, encmenu, "Encodings", "Change text encoding")
                menuAdd(self, encmenu, 'ascii', "Change encoding for the current file to ascii (will use utf-8 if unicode characters found)", self.OnEncChange, ENCODINGS['ascii'], typ)
                menuAdd(self, encmenu, 'other', "Will use the encoding specified in your encoding declaration, reverting to ascii if not found, and utf-8 as necessary", self.OnEncChange, ENCODINGS['other'], typ)
                for bom, enc in BOM[:-2]:
                    menuAdd(self, encmenu, enc, "Change encoding for the current file to %s"%enc, self.OnEncChange, ENCODINGS[enc], typ)

            #--------------------------- Line ending menu --------------------
            endingmenu = wx.Menu()
            menuAddM(setmenu, endingmenu, "Line Ending", "Change the line endings on the current document")

            x = LE_RMAPPING.values()
            x.sort()
            for _, idn, name, helpt in x:
                menuAdd(self, endingmenu, name, helpt, self.OnLineEndChange, idn, typ)
            #
            setmenu.AppendSeparator()
            menuAdd(self, setmenu, "Show Autocomplete", "Show the autocomplete dropdown while typing", self.OnAutoCompleteToggle, AUTO, wx.ITEM_CHECK)
            menuAdd(self, setmenu, "Use Methods", "Try to only display methods of classes during autocomplete", self.OnUseMethodsToggle, FETCH_M, wx.ITEM_CHECK)
            menuAdd(self, setmenu, "Show line numbers", "Show or hide the line numbers on the current document", self.OnNumberToggle, NUM, wx.ITEM_CHECK)
            menuAdd(self, setmenu, "Show margin", "Show or hide the bookmark signifier margin on the current document", self.OnMarginToggle, MARGIN, wx.ITEM_CHECK)
            menuAdd(self, setmenu, "Show Indentation Guide", "Show or hide gray indentation guides in indentation", self.OnIndentGuideToggle, INDENTGUIDE, wx.ITEM_CHECK)
            menuAdd(self, setmenu, "Show Whitespace", "Show or hide 'whitespace' characters", self.OnWhitespaceToggle, S_WHITE, wx.ITEM_CHECK)
            menuAdd(self, setmenu, "Show Line Endings", "Show or hide line ending characters", self.OnLineEndingToggle, S_LEND, wx.ITEM_CHECK)
            menuAdd(self, setmenu, "Save Position", "Remember or forget the last position of the cursor when the current document is closed", self.OnSavePositionToggle, SAVE_CURSOR, wx.ITEM_CHECK)
            menuAdd(self, setmenu, "Highlight Current line", "When checked, will change the background color of the current line", self.HightlightLineToggle, HIGHLIGHT_LINE, wx.ITEM_CHECK)
            setmenu.AppendSeparator()
            menuAdd(self, setmenu, "Refresh\tF5", "Refresh the browsable source tree, autocomplete listing, and the tooltips (always accurate, but sometimes slow)", self.OnRefresh, wx.NewId())
            menuAdd(self, setmenu, "Run Macro", "Run the currently selected macro on the current document", self.macropage.OnPlay, wx.NewId())
            setmenu.AppendSeparator()
            menuAdd(self, setmenu, "Expand all", "Expand all folded code through the entire document", self.OnExpandAll, wx.NewId())
            menuAdd(self, setmenu, "Fold all", "Fold all expanded code through the entire document", self.OnFoldAll, wx.NewId())
            menuAdd(self, setmenu, "Use Tabs", "New indentation will include tabs", self.OnSetTabToggle, USETABS, wx.ITEM_CHECK)
            menuAdd(self, setmenu, "Wrap Long Lines", "Visually continue long lines to the next line", self.OnWrapL, WRAPL, wx.ITEM_CHECK)
            menuAdd(self, setmenu, "Sloppy Cut/Copy", "Will select all partially selected lines during cut/copy.", self.OnSloppy, SLOPPY, wx.ITEM_CHECK)
            menuAdd(self, setmenu, "Smart Paste", "Will auto-indent pastes that are multi-line", self.OnSmartPaste, SMARTPASTE, wx.ITEM_CHECK)
            setmenu.AppendSeparator()
            menuAdd(self, setmenu, "Set Triggers", "Sets trigger expansions for the current document", self.OnSetTriggers, wx.NewId())
            menuAdd(self, setmenu, "Set Indent Width", "Set the number of spaces per indentation level", self.OnSetIndent, wx.NewId())
            menuAdd(self, setmenu, "Set Tab Width", "Set the visual width of tabs in the current open document", self.OnSetTabWidth, wx.NewId())
            menuAdd(self, setmenu, "Set Long Line Column", "Set the column number for the long line indicator", self.OnSetLongLinePosition, wx.NewId())

            #---------------------------- Long line submenu ------------------
            longlinemenu = wx.Menu()
            menuAddM(setmenu, longlinemenu, "Set Long Line Indicator", "Change the mode that signifies long lines")

            x = LL_RMAPPING.values()
            x.sort()
            for _, idn, name, helpt in x:
                menuAdd(self, longlinemenu, name, helpt, self.OnSetLongLineMode, idn, typ)

#------------------------------- Options Menu --------------------------------
        if 1:
            optionsmenu= wx.Menu()
            menuAddM(menuBar, optionsmenu, "&Options")
            settingsmenu = wx.Menu()
            menuAddM(optionsmenu, settingsmenu, "Save Settings", "Set the default behavior of documents opened of a given type")
            for mid in SITO:
                lang, desc = SOURCE_ID_TO_OPTIONS[mid]
                menuAdd(self, settingsmenu, desc, "Save the settings for the current document as the default for %s documents"%desc, self.OnSaveLang, mid)
            #menuAdd(self, settingsmenu, "", ", self.OnSaveSettings, wx.NewId())
            loadsettingsmenu = wx.Menu()
            menuAddM(optionsmenu, loadsettingsmenu, "Load Settings", "Set the current document behavior to that of the default for documents of a given type")
            for mid in SITO2:
                lang, desc = SOURCE_ID_TO_OPTIONS2[mid]
                menuAdd(self, loadsettingsmenu, desc, "Set the current document behavior to that of the default for %s"%desc, self.OnLoadSavedLang, mid)

            optionsmenu.AppendSeparator()
            #-------------------------- Default Style submenu ----------------
            stylemenu2 = wx.Menu()
            menuAddM(optionsmenu, stylemenu2, "Default Highlighting", "Set the default syntax highlighting for new or unknown documents")
            for i in ASSOC:
                name, mid = i[6], i[1]
                st = "All new or unknown documents will be highlighted as %s"%name
                menuAdd(self, stylemenu2, name, st, self.OnDefaultStyleChange, mid, typ)

            ## optionsmenu.AppendSeparator()
            ## menuAdd(self, optionsmenu, "Enable File Drops", "Enable drag and drop file support onto the text portion of the editor", self.OnDNDToggle, DND_ID, wx.ITEM_CHECK)
            optionsmenu.AppendSeparator()

            menuAdd(self, optionsmenu, "One PyPE", "When checked, will listen on port 9999 for filenames to open", self.OnSingleToggle, SINGLE_ID, wx.ITEM_CHECK)
            menuAdd(self, optionsmenu, "Use Icons", "When checked, the editor uses filetype-specific icons next to file names", self.OnIconToggle, IT_ID, wx.ITEM_CHECK)
            menuAdd(self, optionsmenu, "Method Colors", "When checked, the editor will use colored icons next to functions and methods based on how 'public' a method is (requires refresh)", self.OnMethodColorToggle, METH_C_ID, wx.ITEM_CHECK)
            if UNICODE:
                menuAdd(self, optionsmenu, "Always Write BOM", "If checked, will write BOM when coding: directive is found, otherwise not", self.OnBOMToggle, USEBOM_ID, wx.ITEM_CHECK)
            menuAdd(self, optionsmenu, "Strict Todo", "When checked, todos must also begin with > character (except xml/html)", self.OnStrictTodoToggle, STRICT_TODO_ID, wx.ITEM_CHECK)
            menuAdd(self, optionsmenu, "Set Line Color", "The color of the current line when 'Highlight Current Line' is enabled", self.OnLineColor, wx.NewId())

            _om = wx.Menu()
            menuAddM(optionsmenu, _om, "Layout Options", "Options regarding the PyPE window layout")

            menuAdd(self, _om, "Editor on top", "When checked, the editor is above the Todos, Log, etc., otherwise it is below", self.OnLogBarToggle, LB_ID, wx.ITEM_CHECK)
            menuAdd(self, _om, "Editor on left", "When checked, the editor is left of the source trees, document list, etc., otherwise it is to the right", self.OnDocBarToggle, DB_ID, wx.ITEM_CHECK)
            menuAdd(self, _om, "Show Wide Tools", "Shows or hides the tabbed tools that are above or below the editor", self.OnShowWideToggle, WIDE_ID, wx.ITEM_CHECK)
            menuAdd(self, _om, "Show Tall Tools", "Shows or hides the tabbed tools that are right or left of the editor", self.OnShowTallToggle, TALL_ID, wx.ITEM_CHECK)
            menuAdd(self, _om, "One Tab", "When checked, the name, line, filter, and todo lists all share a tab (requires restart)", self.OnOneTabToggle, ONE_TAB, wx.ITEM_CHECK)
            menuAdd(self, _om, "Wide Todo", "When checked, the todo list will be near the Log tab, when unchecked, will be near the Documenst tab (requires restart)", self.OnTodoToggle, TD_ID, wx.ITEM_CHECK)

            _om.AppendSeparator()

            x = TB_RMAPPING.values()
            x.sort()
            for _, idn, name, helpt in x:
                menuAdd(self, _om, "(toolbar)" + name, helpt, self.OnToolBar, idn, typ)

            doptmenu = wx.Menu()
            menuAddM(optionsmenu, doptmenu, "Documents Tab", "Change behavior of the Documents tab")
            for value in (1,3,2,0):
                iid = DOCUMENT_LIST_OPTION_TO_ID[value]
                desc = DOCUMENT_LIST_OPTIONS[iid][1]
                menuAdd(self, doptmenu, "(documents) " +desc, "Make the Documents list look like: %s"%desc, self.OnChangeDocumentsOptions, iid, typ)

            doptmenu.AppendSeparator()
            menuAdd(self, doptmenu, "Show Recent", "When checked, will provide a list of recently open documents in the Documents tab (requires restart)", self.OnShowRecentDocs, SHOW_RECENT, wx.ITEM_CHECK)

            ## if show_recent:
            doptmenu.AppendSeparator()
            for value in (1,3,2,0):
                iid = DOCUMENT_LIST_OPTION_TO_ID2[value]
                desc = DOCUMENT_LIST_OPTIONS2[iid][1]
                menuAdd(self, doptmenu, "(recent) " + desc, "Make the Recent Documents list look like: %s"%desc, self.OnChangeDocumentsOptions2, iid, typ)

            doptmenu.AppendSeparator()
            menuAdd(self, doptmenu, "Show Quick Browse", "Show a searchable listing of recently open documents and watched paths", self.OnShowQuickbrowse, SHOW_SEARCH, typ)


            moptmenu = wx.Menu()
            menuAddM(optionsmenu, moptmenu, "Macro Options", "Change the behavior of macros during double-click")
            menuAdd(self, moptmenu, "Use images for macro buttons", "When checked, the macro buttons will have images (requires restart)", self.OnMacroButtonImage, IMAGE_BUTTONS, typ)
            moptmenu.AppendSeparator()

            for value in xrange(3):
                iid = MACRO_CLICK_TO_ID[value]
                desc = MACRO_CLICK_OPTIONS[iid][1]
                menuAdd(self, moptmenu, "(double click) " + desc, "When double clicking on a macro: %s"%desc, self.OnChangeMacroOptions, iid, typ)

            #
            #ability to enable/disable a tool
            toolsmenu = wx.Menu()
            menuAddM(optionsmenu, toolsmenu, "Tool Options", "Enable or disable a particular tool")
            for i in TOOLS_ENABLE_L:
                menuAdd(self, toolsmenu, i[1], "Enable "+i[2], self.OnToolToggle, i[0], wx.ITEM_CHECK)

            optionsmenu.AppendSeparator()

            caretmenu = wx.Menu()
            menuAddM(optionsmenu, caretmenu, "Caret Options", "Set options relating to your blinking cursor")

            x = [(j[2], i, j[3], j[4]) for i,j in CARET_ID_TO_OPTIONS.iteritems()]
            x.sort()
            for _, idn, name, helpt in x:
                menuAdd(self, caretmenu, "(caret behavior) " + name, helpt, self.OnCaret, idn, typ)

            caretmenu.AppendSeparator()

            menuAdd(self, caretmenu, "Set Caret M value", "Set the number of lines of unapproachable margin, the M value referenced in Caret Options", self.OnCaretM, wx.NewId())
            menuAdd(self, caretmenu,  "Set Caret N value", "Set the multiplier, the N value referenced in Caret Options", self.OnCaretN, wx.NewId())
            caretmenu.AppendSeparator()

            for i in (1,2,3):
                menuAdd(self, caretmenu, "caret is %i pixels wide"%i, "Set your caret to be %i pixels wide."%i, self.OnCaretWidth, CARET_W_WIDTH_TO_O[i], typ)

#---------------- Python interpreter choice for Python Shell -----------------

            shellmenu = wx.Menu()
            menuAddM(optionsmenu, shellmenu, "Shell Options", "Set various shell options")

            for i in xrange(len(SHELL_OUTPUT_OPTIONS)):
                idn = SHELL_NUM_TO_ID[i]
                desc = SHELL_OUTPUT_OPTIONS[idn][1]
                menuAdd(self, shellmenu, "(shell output) "+desc, "Any output recieved from shells will be indicated by: %s"%desc, self.OnShellStyle, idn, typ)

            shellmenu.AppendSeparator()
            menuAdd(self, shellmenu, "Set Shell Output Color", "The color of the output indicator chosen above", self.OnShellColor, wx.NewId())

            self.python_choices = choices = shellmenu
            menuAdd(self, choices, "Browse for Python shells...", "Choose some Python interpreter not listed", self.OnBrowseInterpreter, wx.NewId())
            choices.AppendSeparator()

            interpreter.check_paths(python_choices, which_python)

            for i in interpreter.python_choices:
                self.AddPythonOption(i, i==interpreter.which_python)


            #--------------- end Python interpreter choice for Python Shell --

            _realtime = wx.Menu()
            menuAddM(optionsmenu, _realtime, "Realtime Options", "Adjust the behavior of the realtime syntax checker and tool refresh")
            for i, n, d in SYNTAX_CHECK_DELAY_L:
                menuAdd(self, _realtime, "(check syntax) " + d, "Check the syntax of Python documents at most every: %s"%d, self.OnSyntaxChange, i, wx.ITEM_CHECK)

            _realtime.AppendSeparator()

            for i, n, d in REFRESH_DELAY_L:
                menuAdd(self, _realtime, "(update tools) " + d, "Refresh at most every: %s"%d, self.OnRefreshChange, i, wx.ITEM_CHECK)

            findbar = wx.Menu()
            menuAddM(optionsmenu, findbar, "Findbar Options", "Set findbar preferences")

            menuAdd(self, findbar, "Findbar below editor", "When checked, any new find/replace bars will be below the editor, otherwise above (bars will need to be reopened)", self.OnFindbarToggle, FINDBAR_BELOW_EDITOR, wx.ITEM_CHECK)
            menuAdd(self, findbar, "Use Findbar history", "When checked, allows for the find and replace bars to keep history of searches (bars will need to be reopened)", self.OnFindbarHistory, NO_FINDBAR_HISTORY, wx.ITEM_CHECK)
            menuAdd(self, findbar, "Clear Find Bar history", "Clears the find/replace history on the current document", self.OnFindbarClear, CLEAR_FINDBAR_HISTORY)

            optionsmenu.AppendSeparator()

            menuAdd(self, optionsmenu, "Change Menus and Hotkeys", "Change the name of menu items and their hotkeys, any changes will require a restart to take effect", self.OnChangeMenu, wx.NewId())
            titlemenu = wx.Menu()
            menuAddM(optionsmenu, titlemenu, "Title Options", "Set what information you would like PyPE to display in the title bar")
            fn = "pype.py"
            long = "C:\\PyPE\\pype.py"
            pype = "PyPE %s"%VERSION
            for i in xrange(5):
                title_id, proto, desc = TITLE_OPTION_TO_ID[i]
                menuAdd(self, titlemenu, desc, "Set the title like: "+proto%locals(), self.OnChangeTitle, title_id, typ)

            menuAdd(self, optionsmenu, "Save preferences", "Saves all of your current preferences now", self.OnSavePreferences, wx.NewId())


#--------------------------------- Help Menu ---------------------------------

        if 1:
            helpmenu= wx.Menu()
            menuAddM(menuBar, helpmenu, "&Help")
            menuAdd(self, helpmenu, "About...", "About this piece of software", self.OnAbout, wx.ID_ABOUT)
            helpmenu.AppendSeparator()
            menuAdd(self, helpmenu, "PyPE Help\tF1", "View the help", self.OnHelp, wx.ID_HELP)

#------------------------ A ...few... state variables ------------------------
        if 1:
            self.Show(True)
            self.dirname = '.'
            self.closing = 0
            self.openfiles = {}
            self.realfn = {}
            self.dpm = 0
            self.menubar.Check(AUTO, showautocomp)
            self.menubar.Check(WRAPL, wrapmode != wxstc.STC_WRAP_NONE)
            ## self.menubar.Check(DND_ID, dnd_file)
            self.menubar.Check(IT_ID, USE_DOC_ICONS)
            codetree.colored_icons = colored_icons
            self.menubar.Check(METH_C_ID, codetree.colored_icons)
            self.menubar.Check(LB_ID, logbarlocn)
            self.menubar.Check(DB_ID, docbarlocn)
            self.menubar.Check(WIDE_ID, SHOWWIDE)
            self.menubar.Check(TALL_ID, SHOWTALL)
            self.menubar.Check(ONE_TAB, ONE_TAB_)
            self.menubar.Check(SINGLE_ID, single_pype_instance)
            if UNICODE:
                self.menubar.Check(USEBOM_ID, always_write_bom)
            self.menubar.Check(SHELL_NUM_TO_ID[SHELL_OUTPUT], 1)
            self.menubar.Check(IMAGE_BUTTONS, macro_images)
            self.menubar.Check(TD_ID, TODOBOTTOM)
            self.menubar.Check(STRICT_TODO_ID, STRICT_TODO)
            self.menubar.Check(USETABS, use_tabs)
            self.menubar.Check(INDENTGUIDE, indent_guide)
            self.menubar.Check(lexers3[DEFAULTLEXER], 1)
            self.menubar.Check(SAVE_CURSOR, save_cursor)

            self.menubar.Check(SYNTAX_CHECK_DELAY_NUM_TO_ID[HOW_OFTEN1], 1)
            self.menubar.Check(REFRESH_DELAY_NUM_TO_ID[HOW_OFTEN2], 1)

            self.menubar.Check(FINDBAR_BELOW_EDITOR, findbar_location)
            self.menubar.Check(NO_FINDBAR_HISTORY, not no_findbar_history)
            self.menubar.Check(CARET_W_WIDTH_TO_O[CARET_WIDTH], 1)
            self.menubar.FindItemById(CLEAR_FINDBAR_HISTORY).Enable(not no_findbar_history)
            self.menubar.Check(DOCUMENT_LIST_OPTION_TO_ID[document_options], 1)
            if hasattr(self.docpanel, 'recentlyclosed'):
                self.menubar.Check(DOCUMENT_LIST_OPTION_TO_ID2[document_options2], 1)
            self.menubar.Check(SHOW_RECENT, show_recent)
            self.menubar.Check(SHOW_SEARCH, show_search)

            for i in TOOLS_ENABLE_L:
                if i[4] in window_management.enabled:
                    self.menubar.Check(i[0], 1)
                elif i[1] == 'Global Filter' and global_filter_table:
                    self.menubar.Check(i[0], 1)

#------------------------ Drag and drop file support -------------------------
        self.SetDropTarget(FileDropTarget(self))

        #set up some events
        if 1:
            wx.EVT_CLOSE(self, self.OnExit)
            wx.EVT_END_SESSION(self, self.OnExit)
            wx.EVT_QUERY_END_SESSION(self, self.OnExit)
            wx.EVT_SIZE(self, self.OnSize)
            wx.EVT_ACTIVATE(self, self.OnActivation)
            wx.EVT_KEY_DOWN(self, self.OnKeyPressed)
            self.starting = 0
            if self.control.GetPageCount() > 0:
                stc = self.getNumWin()[1]
                self.OnDocumentChange(stc)

        #set up some timers
        if 1:
            self.timer = Timer(self.ex_size, None)

            self.timer2 = Timer(self.single_instance_poller)
            self.timer2.Start(100, oneShot=False)

            self.timer3 = Timer(self._no_activity, None)

            # pushed to mainwindow from PythonSTC
            #syntax checking
            self.t = Timer(self.redirect._gotcharacter, None)
            #live tree/tool update
            self.t2 = Timer(self.redirect._gotcharacter2, None)

            #interpreter polling
            ## self.global_poller = wx.Timer(self, wx.NewId())
            ## self.Bind(wx.EVT_TIMER, self.RunEvents, self.global_poller)
            ## self.global_poller.Start(500, oneShot=False)
            wx.CallAfter(scheduler._schedulethread)


#------------------ Open files passed as arguments to PyPE -------------------

        self.client.Unsplit(startup=1)
        self.client2.Unsplit(startup=1)
        if SHOWTALL:
            wx.CallAfter(self.client.Split)
        if SHOWWIDE:
            wx.CallAfter(self.client2.Split)

        if (not SHOWWIDE) or (not SHOWTALL):
            self.OnSize(None)

        wx.CallAfter(self.OnDrop, fnames, 0)
        if single_pype_instance:
            single_instance.startup()
        if USE_THREAD:
            self.Bind(EVT_DONE_PARSING, self.doneParsing)
            wx.CallAfter(parse_thread, self)
            wx.CallAfter(check_files, self)

    ## def RunEvents(self, evt):
        ## scheduler.GlobalSchedule.run(time.time())

    #...
    def _activity(self, py=None, stc=None):
        global start_use, end_use
        if start_use == None:
            start_use = time.time()

        end_use = time.time()
        self.timer3.Start(5000, oneShot=True)

        if stc:
            if HOW_OFTEN2 != -1:
                self.t2.Start(stc.lastparse2, oneShot=True)

            #we always want to check syntax in the shell
            if HOW_OFTEN1 != -1 or not isinstance(stc, PythonSTC):
                self.t.Start(stc.lastparse, oneShot=True)

    def _no_activity(self, e):
        global USED_TIME, start_use
        if start_use:
            USED_TIME += long(max(end_use-start_use, 5))
            start_use = None

    def _updateChecks(self):
        win = None
        try:
            num, win = self.getNumWin()
        except cancelled:
            ## print "no window!"
            pass

        self.control.updateChecks(win)

    def getglobal(self, nam):
        return globals()[nam]

    def getInt(self, title, text, default):
        dlg = wx.TextEntryDialog(self, text, title, str(default))
        resp = dlg.ShowModal()
        valu = dlg.GetValue()
        dlg.Destroy()
        if resp != wx.ID_OK:
            raise cancelled
        return validate(valu, default)

    def _setupToolBar(self):
        size = (16,16)
        def getBmp(artId, client):
            bmp = wx.ArtProvider_GetBitmap(artId, client, size)
            if not bmp.Ok():
                bmp = EmptyBitmap(*size)
            return bmp

        if TOOLBAR == 1:
            orient = wx.TB_HORIZONTAL
        else:
            orient = wx.TB_VERTICAL
        tb = self.CreateToolBar(
            orient|wx.NO_BORDER|wx.TB_FLAT|wx.TB_TEXT)

        tb.SetToolBitmapSize(size)

        icon = getBmp(wx.ART_NORMAL_FILE, wx.ART_TOOLBAR)
        tb.AddSimpleTool(wx.ID_NEW, icon, "New Document",
            "Create a new empty document")
        icon = getBmp(wx.ART_FILE_OPEN, wx.ART_TOOLBAR)
        tb.AddSimpleTool(wx.ID_OPEN, icon, "Open",
            "Open an existing document")

        icon = getBmp(wx.ART_FILE_SAVE, wx.ART_TOOLBAR)
        tb.AddSimpleTool(wx.ID_SAVE, icon, "Save", "Save current document")

        icon = getBmp(wx.ART_FILE_SAVE_AS, wx.ART_TOOLBAR)
        tb.AddSimpleTool(wx.ID_SAVEAS, icon, "Save as...", "Save current document as...")

        tb.AddSeparator()

        icon = getBmp(wx.ART_FOLDER, wx.ART_TOOLBAR)
        tb.AddSimpleTool(wx.ID_CLOSE, icon, "Close", "Close the current document")

        tb.AddSeparator()

        icon = getBmp(wx.ART_CUT, wx.ART_TOOLBAR)
        tb.AddSimpleTool(wx.ID_CUT, icon, "Cut",
            "Cut selection to the clibboard")
        icon = getBmp(wx.ART_COPY, wx.ART_TOOLBAR)
        tb.AddSimpleTool(wx.ID_COPY, icon, "Copy",
            "Copy selection to the clibboard")
        icon = getBmp(wx.ART_PASTE, wx.ART_TOOLBAR)
        tb.AddSimpleTool(wx.ID_PASTE, icon, "Paste",
            "Paste current clibboard contents")
        icon = getBmp(wx.ART_DELETE, wx.ART_TOOLBAR)
        tb.AddSimpleTool(pypeID_DELETE, icon, "Delete",
            "Delete selection")

        tb.AddSeparator()

        icon = getBmp(wx.ART_UNDO, wx.ART_TOOLBAR)
        tb.AddSimpleTool(wx.ID_UNDO, icon, "Undo",
            "Undo edit")
        icon = getBmp(wx.ART_REDO, wx.ART_TOOLBAR)
        tb.AddSimpleTool(wx.ID_REDO, icon, "Redo",
            "Redo edit (i.e. undo undo edit)")

        tb.AddSeparator()

        icon = getBmp(wx.ART_FIND, wx.ART_TOOLBAR)
        tb.AddSimpleTool(pypeID_FINDBAR, icon, "Find",
            "Find")
        icon = getBmp(wx.ART_FIND_AND_REPLACE, wx.ART_TOOLBAR)
        tb.AddSimpleTool(pypeID_REPLACEBAR, icon, "Replace",
            "Find and replace")

        tb.AddSeparator()

        icon = getBmp(wx.ART_ADD_BOOKMARK, wx.ART_TOOLBAR)
        tb.AddSimpleTool(pypeID_TOGGLE_BOOKMARK, icon, "Toggle Bookmark",
            "Create or Remove a bookmark at the current line")

        icon = getBmp(wx.ART_GO_DOWN, wx.ART_TOOLBAR)
        tb.AddSimpleTool(pypeID_NEXT_BOOKMARK, icon, "Next Bookmark",
            "Go to the next bookmark in this file")

        icon = getBmp(wx.ART_GO_UP, wx.ART_TOOLBAR)
        tb.AddSimpleTool(pypeID_PRIOR_BOOKMARK, icon, "Previous Bookmark",
            "Go to the previous bookmark in this file")

        tb.AddSeparator()
        tb.AddSeparator()

        icon = getBmp(wx.ART_HELP, wx.ART_TOOLBAR)
        tb.AddSimpleTool(wx.ID_HELP, icon, "Help!",
            "Opens up the help for PyPE")

        tb.Realize()

    def OnDocumentChange(self, stc, forced=False):
        if not forced and not self.starting:
            self.t.Stop()
            self.t2.Stop()

        if not self.starting:
            start = time.time()

            if stc.cached is None or forced:
                if stc.refresh:
                    return
                stc.ConvertEOLs(fmt_mode[stc.format])
                out = wxstc.StyledTextCtrl.GetText(stc)
                m2 = md5.new(_to_str(out)).digest()
                if m2 == stc.m2:
                    return
                stc.m2 = m2
                out = out.replace('\t', stc.GetTabWidth()*' ')
                lang = lexer2lang.get(stc.GetLexer(), 'text')
                if out and USE_THREAD:
                    stc.refresh = 1
                    parse_queue.put((out, stc, lang))
                    return

                tpl = parse(lang, out, stc.format, 3, lambda:None)
                self._doneParsing(stc, tpl, time.time()-start)

            self.updateWindowTitle()

    def doneParsing(self, evt):
        stc = evt.stc
        if not stc:
            return

        self._doneParsing(stc, evt.tpl, evt.delta)

    def _doneParsing(self, stc, tpl, delta):

        if isinstance(stc, PythonSTC):
            fcn = lambda dt: int(max(dt, 1)*_MULT[HOW_OFTEN2]*1000)
        else:
            fcn = lambda dt: int(max(dt, .02)*5*1000)

        t = time.time()

        stc.refresh = 0
        stc.cached = tpl
        h1, _, stc.tooltips, todo, tags = tpl
        stc.hierarchy = h1
        ## stc.kw.sort()
        ## stc.kw = ' '.join(stc.kw)
        stc.docstate.Update(h1, todo, tags)
        if self.gf:
            self.gf.new_hierarchy(stc, h1)

        delta += time.time()-t
        stc.lastparse2 = int(max((5,20,120)[HOW_OFTEN2]*delta, (5,20,120)[HOW_OFTEN2])*1000)
        if not stc.automatic:
            self.SetStatusText(("Browsable source tree, autocomplete, tooltips and todo"
                                " updated for %s in %.1f seconds.")%(stc.filename, delta))
        stc.automatic = 0

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
                w2 = win.parent.GetWindow2()
                try:
                    size = (w2.GetEffectiveMinSize())[1]+5
                except:
                    size = (w2.GetAdjustedBestSize())[1]+5
                win.parent.SetSashPosition(-size)
        except cancelled:
            pass
        # Save window size before it is maximized
        if not self.IsMaximized():
            global LASTSIZE, LASTPOSITION
            LASTSIZE = self.GetSizeTuple()
            LASTPOSITION = self.GetPositionTuple()

    def single_instance_poller(self, evt=None):
        if single_pype_instance:
            single_instance.poll()

        wins = [self.altview, self.altview2]
        try:
            wins.append(self.getNumWin()[1])
        except cancelled:
            pass

        for win in wins:
            x = win.GetMarginWidth(0)
            if x:
                #we are supposed to have a margin...
                y = len(str(win.GetLineCount()))
                z = int(.9*StyleSetter.fs*max(4, y+1))
                if x != z:
                    win.SetMarginWidth(0, z)

    def OnSize(self, event):
        self.ex_size()
        if event:
            event.Skip()

    def dialog(self, message, title, styl=wx.OK):
        d= wx.MessageDialog(self,message,title,styl)
        retr = d.ShowModal()
        d.Destroy()
        return retr

    def exceptDialog(self, title="Error"):
        k = cStringIO.StringIO()
        traceback.print_exc(file=k)
        k = k.getvalue()
        print k
        dlg = ScrolledMessageDialog(self, k, title)
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
            try:
                wx.SafeYield()
            except:
                pass

        self.redrawvisible()

    def SetStatusText(self, text, number=0, log=1):
        if (number == 0) and text:
            if log:
                print text
                text = "[%s] %s"%(time.asctime(), text)
        wx.CallAfter(self.sb.SetStatusText, text, number)

    def OnActivation(self, e):
        try:
            self.control.__iter__
        except wx.PyDeadObjectError:
            e.Skip()
            return
        self.OnCheckMods(force=False)
        self.redrawvisible()
        self.SendSizeEvent()

    def OnCheckMods(self, evt=None, force=True):
        try:
            self.control.__iter__
        except wx.PyDeadObjectError:
            e.Skip()
            return
        docs_and_flags = []
        for document in self.control:
            fn = self.getAlmostAbsolute(document.filename, document.dirname)
            docs_and_flags.append([fn, (document.filename, document.dirname), document.mod])
        if docs_and_flags:
            t = (not force) and time.time() or 0
            file_mods_to_check.put((time.time(), docs_and_flags))
        CheckMacros()

    def CheckedDocMods(self, mods):
        dirty = []
        deleted = []
        for fn, pair, omod, cmod, digest in mods:
            if not self.isOpen(*pair):
                continue
            document = self.control.GetPage(self.getPositionAbsolute(self.getAbsolute(*pair))).GetWindow1()
            if omod and not cmod:
                ## self.selectAbsolute(self.getAbsolute(*pair))
                document.MakeDirty(None)
                deleted.append(self.getAbsolute(*pair))
                document.mod = None
            elif omod != cmod:
                if md5.new(document.GetText(error=0)).digest() == digest:
                    #Fixes a problem with PyPE being open during daylight
                    #savings time changes.
                    #Also fixes an issue when an identical file is saved
                    #over a currently-being-edited file.
                    document.mod = cmod
                    document.MakeClean(None)
                    continue
                else:
                    dirty.append(self.getAbsolute(*pair))
                    ## self.selectAbsolute(self.getAbsolute(*pair))
                    document.MakeDirty(None)
        if deleted:
            dlg = wx.MessageDialog(self,
                "Some files seem to have been deleted by an external program.\n"
                "Unless the files are saved, data loss may occur.\n" + '\n'.join(deleted),
                "WARNING")
            dlg.Destroy()
        if dirty:
            dlg = wx.MultiChoiceDialog(self, 
               "The following files have been modified on disk since you\n"
               "last saved, and have been marked as 'dirty'.\n"
               "You can reload the files individually via File -> Reload,\n"
               "you can force a re-check of the files via\n"
               "File -> Check Mods, or by selecting the documents below\n"
               "you can force a reload now.", "Some documents have changed", dirty)
            if dlg.ShowModal() == wx.ID_OK:
                for name in (dirty[i] for i in dlg.GetSelections()):
                    dirname, filename = os.path.split(name)
                    self._reload_file(filename, dirname)
            dlg.Destroy()

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
        try:
            self.config = unrepr(open(path, 'r').read())
        except:
            traceback.print_exc()
            self.config = {}
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
                   'col_mode':stc.STC_EDGE_LINE,
               'indent_guide':0,
               'showautocomp':0,
              'fetch_methods':1,
                   'wrapmode':stc.STC_WRAP_NONE,
                   'sortmode':1,
                'save_cursor':0,
                'cursor_posn':0,
                 'whitespace':0,
             'show_line_ends':0,
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
                            ('match_flags', wx.FR_DOWN),
                            ('pathmarksn', []),
                            ('workspaces', {}),
                            ('workspace_order', []),
                            ('SASH1', 80),
                            ('SASH2', 300),
                            ('LASTSIZE', (750,550)),
                            ('LASTPOSITION', self.GetPositionTuple()),
                            ('LASTWINDOWSTATE', 0),
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
                            ('document_options2', 1),
                            ('macro_doubleclick', 0),
                            ('COLOUR', '#d0d0d0'),
                            ('SHELL_OUTPUT', 0),
                            ('SHELL_COLOR', '#d0d0d0'),
                            ('macro_images', 1),
                            ('show_recent', 1),
                            ('STRICT_TODO', 0),
                            ('python_choices', []),
                            ('which_python', ''),
                            ('colored_icons', 1),
                            ('SEARCH_SASH_POSITION', 0),
                            ('USED_TIME', 0L),
                            ('HOW_OFTEN1', -1),
                            ('HOW_OFTEN2', -1),
                            ('disabled_tools', []),
                            ('paths_to_watch', []),
                            ('extensions_to_watch', list(set(extns))),
                            ('show_search', 1),
                            ('global_filter_table', 0),
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
        self.config['LASTSIZE'] = LASTSIZE
        self.config['LASTPOSITION'] = LASTPOSITION
        self.config['LASTWINDOWSTATE'] = self.IsMaximized()
        self.config['SASH1'] = self.client2.getSize()#BOTTOM.GetSize()[1]-self.control.GetSize()[1]
        self.config['SASH2'] = self.client.getSize()#self.GetSize()[0]-self.control.GetSize()[0]
        ## print 'savehistory sash sizes', self.config['SASH2'], self.config['SASH1']

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
        self.config['document_options2'] = document_options2
        self.config['macro_doubleclick'] = macro_doubleclick
        self.config['COLOUR'] = COLOUR
        self.config['SHELL_OUTPUT'] = SHELL_OUTPUT
        self.config['SHELL_COLOR'] = SHELL_COLOR
        self.config['macro_images'] = macro_images
        self.config['show_recent'] = show_recent
        self.config['STRICT_TODO'] = STRICT_TODO
        self.config['python_choices'] = interpreter.python_choices
        self.config['which_python'] = interpreter.which_python
        self.config['colored_icons'] = codetree.colored_icons
        self.config['SEARCH_SASH_POSITION'] = self.findinfiles.controlsWindow.GetSashPosition()
        self.config['USED_TIME'] = USED_TIME
        self.config['HOW_OFTEN1'] = HOW_OFTEN1
        self.config['HOW_OFTEN2'] = HOW_OFTEN2
        self.config['disabled_tools'] = [i for i in window_management.possible if i not in window_management.enabled]
        self.config['paths_to_watch'] = paths_to_watch
        self.config['extensions_to_watch'] = extensions_to_watch
        self.config['show_search'] = show_search
        self.config['global_filter_table'] = global_filter_table
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

    def OnSave(self,e,upd=1):
        wnum, win = self.getNumWin(e)
        if win.dirname:
            # todo: we really should check the state of the file on-disk
            # in order to verify that we had the proper modification time
            # earlier...
            try:
                txt = win.GetText()
                ofn = os.path.join(win.dirname, win.filename)
                fil = open(ofn, 'wb')
                fil.write(txt)
                fil.close()
                if UNICODE: a = "%s as %s"%(ofn, win.enc)
                else:       a = ofn
                if upd:
                    win.mod = os.stat(ofn)[8]
                self.SetStatusText("Correctly saved %s"%a)
                self.curdocstates[ofn] = win.GetSaveState()
                if upd:
                    win.MakeClean()
            except cancelled:
                raise
            except:
                self.exceptDialog("Save Failed")
                raise cancelled
        else:
            self.OnSaveAs(e)

    def OnSaveAs(self,e,upd=1):
        wnum, win = self.getNumWin(e)

        dlg = wx.FileDialog(self, "Save file as...", current_path, "", "All files (*.*)|*.*", wx.SAVE|wx.OVERWRITE_PROMPT)
        rslt = dlg.ShowModal()
        if rslt == wx.ID_OK:
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

            if not upd:
                x,y = win.filename, win.dirname

            win.filename = fn
            win.dirname = dn

            if upd:
                self.makeOpen(fn, dn)
            self.fileHistory.AddFileToHistory(pth)

            try:
                self.OnSave(e,upd)
            finally:
                if not upd:
                    win.filename, win.dirname = x,y

            if upd:
                #fix the icons and names.
                self.dragger._RemoveItem(wnum)
                self.dragger._InsertItem(wnum, fn)

                win.MakeDirty()
                win.MakeClean()

            if upd:
                if USE_DOC_ICONS:
                    self.control.SetPageImage(wnum, GDI(fn))
                self.control.SetSelection(wnum)
        else:
            raise cancelled

    def OnSaveCopyAs(self, evt):
        self.OnSaveAs(evt, 0)

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
        dlg = wx.FileDialog(self, "Choose a/some file(s)...", wd, "", wildcard, wx.OPEN|wx.MULTIPLE|wx.HIDE_READONLY)
        if dlg.ShowModal() == wx.ID_OK:
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
        dlg = wx.TextEntryDialog(self, 'Enter the module name you would like to open', 'Open module...')
        if dlg.ShowModal() == wx.ID_OK:
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
        dlg = wx.DirDialog(self, "Choose a path", "", style=wx.DD_DEFAULT_STYLE|wx.DD_NEW_DIR_BUTTON)
        if dlg.ShowModal() == wx.ID_OK:
            path = os.path.normcase(os.path.normpath(dlg.GetPath()))
            if not (path in self.config['modulepaths']) and not (path in sys.path):
                self.config['modulepaths'].append(path)
    def OnNewPythonShell(self, e):
        self.newTab("", " ", 1, 1)
    def OnNewCommandShell(self, e):
        self.newTab("", " ", 1, 2)

    def OnRunCurrentFile(self, e, interact=0):
        win = self.getNumWin(e)[1]
        if not win.dirname:
            self.SetStatusText("Error: can't start unnamed file")
            return

        extn = win.filename.split('.')[-1]
        fn = win.filename
        if ' ' in fn:
            fn = '"%s"'%fn
        dir = win.dirname
        if extn in ('py', 'pyw'):
            #if we don't run via a command shell, then either sometimes we
            #don't get wx GUIs, or sometimes we can't kill the subprocesses
            inte = ('', '-i')[bool(interact)]
            if sys.platform == 'win32':
                cmd = 'cmd /c '
            else:
                cmd = ''
                ## cmd = 'sh --noediting -c '
            cmd += 'python -u %s %s'%(inte, fn.replace('"', '\\"'))
        elif extn in ('tex',):
            cmd = 'pdflatex %s'%fn
        elif extn in ('htm', 'html', 'shtm', 'shtml'):
            return webbrowser.open(os.path.join(dir, fn))
        else:
            self.SetStatusText("Error: I don't know how to run file type: %r"%extn)
            return
        data = (dir, cmd)

        i = -1
        for i,j in enumerate(self.control):
            if not isinstance(j, PythonSTC) and not j.filter and not j.restartable and j.restart:
                #we found a re-usable command console
                self.control.SetSelection(i)
                break
        else:
            #we need to create a new command console
            i += 1
            j = None
            self.newTab('', ' ', 1, 3)

        k = [j]

        def run_shell():
            j = k[0]
            if j is None:
                j = self.control.GetPage(i).GetWindow1()

            j._Restart(data)

        interpreter.FutureCall(25, run_shell)

    def OnRunCurrentFileI(self, e):
        return self.OnRunCurrentFile(e, 1)

    def OnRunSelected(self, e):
        win = self.getNumWin(e)[1]

        win.lines.selectedlinesi = win.lines.selectedlinesi

        #get the lines if we don't already have some
        data = ''.join(win.lines.selectedlines)
        data = win._StripPrefix(data, 0, 1)
        if not data.strip():
            print "no data!"
            return
        #copy the text to the clipboard
        if not SetClipboardText(data):
            print "no clipboard!"
            return

        #find some Python shell
        i = -1
        for i,j in enumerate(self.control):
            if not isinstance(j, PythonSTC) and j.filter == 1:
                #we found a usable Python shell
                self.control.SetSelection(i)
                break
        else:
            #we need to create a new Python shell
            i += 1
            j = None
            self.newTab('', ' ', 1, 1)

        k = [j]

        def run_copied():
            j = k[0]
            if j is None:
                j = self.control.GetPage(i).GetWindow1()

            j.SetSelection(j.promptPosEnd, j.GetTextLength())
            j.ReplaceSelection('')
            j.Paste()

        interpreter.FutureCall(25, run_copied)

    @auto_thaw
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
            fn = ' '
            FN = ''
            txt = ''

        split = SplitterWindow(self.control, wx.NewId(), style=wx.SP_NOBORDER)
        split.SetMinimumPaneSize(0)
        wx.EVT_SPLITTER_SASH_POS_CHANGING(self, split.GetId(), veto)

        ftype = extns.get(fn.split('.')[-1].lower(), 'python')
        ## if ftype in document_defaults:
            ## print "found filetype-specific defaults", ftype
        ## else:
            ## print "could not find", ftype
        state = dict(document_defaults.get(ftype, DOCUMENT_DEFAULTS))

        if not shell:
            nwin = PythonSTC(self.control, wx.NewId(), split)
        else:
            state = dict(state)
            state['wrapmode'] = 1
            state['whitespace'] = 0
            nwin = interpreter.MyShell(split, wx.NewId(), self, None, shell)

        nwin.filename = fn
        nwin.dirname = d
        if shell < 2:
            nwin.changeStyle(stylefile, self.style(fn))
        else:
            #we don't want to syntax highlight by default for non-python shells.
            nwin.changeStyle(stylefile, self.style('a.txt'))

        try:
            if d:
                nwin.mod = os.stat(FN)[8]
                if len(txt) == 0:
                    nwin.format = eol
                    nwin.SetText('')
                else:
                    nwin.format = parsers.detectLineEndings(txt)
                    nwin.SetText(txt)

                #if FN in self.config['LASTOPEN']:
                #    state = self.config['LASTOPEN'][FN]
                if FN in self.lastused:
                    _ = self.lastused[FN]
                    __ = _.pop('triggers', None)
                    state.update(_)
                    del _, __, self.lastused[FN]
                else:
                    state['CHECK_VIM'] = None
            else:
                nwin.mod = None
                nwin.format = eol
                nwin.SetText(txt)
        except UnicodeDecodeError:
            nwin.Destroy()
            split.Destroy()
            self.exceptDialog()
            return

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

        if state == document_defaults.get(ftype, DOCUMENT_DEFAULTS) and nwin.GetTextLength() < 200000:
            # try to detect the "true" defaults
            state['use_tabs'], state['spaces_per_tab'], state['indent'] = \
                parsers.detectLineIndent(nwin.lines, state['use_tabs'], state['spaces_per_tab'], state['indent'])
            print "detected", state['use_tabs'], state['spaces_per_tab'], state['indent']

        nwin.SetSaveState(state)

        ## print 3
        if fn == ' ':
            ## print 3.5
            globals()['NEWDOCUMENT'] += 1
            nwin.NEWDOCUMENT = NEWDOCUMENT
        nwin.docstate = docstate(self, nwin)
        ## print 4
        split.Initialize(nwin)
        ## print 5
        shortname = nwin.getshort()
        ## print 'Adding page with name:', shortname
        self.control.AddPage(split, shortname, switch)
        if switch:
            wx.CallAfter(self.control.SetSelection, self.control.GetPageCount()-1)
        nwin.MakeClean()
        ## self.OnRefresh(None, nwin)
        self.updateWindowTitle()
        if switch:
            nwin.SetFocus()
        ## self.OnDocumentChange(nwin)
        self.docpanel._refresh()
        wx.CallAfter(self._updateChecks)
        return nwin.enc

    def OnReload(self, e, win=None):
        if win == None:
            num, win = self.getNumWin(e)
        if not e is None:
            dlg = wx.MessageDialog(self, "%s was modified after last save.\nReloading from disk will destroy all changes.\n\nContinue anyway?"%win.filename, 'File was modified, data loss may occur!', wx.YES_NO|wx.CANCEL)
            a = dlg.ShowModal()
            if a == wx.ID_CANCEL:
                raise cancelled
            elif a == wx.ID_NO:
                return
        self._reload_file(win.filename, win.dirname)

    def _reload_file(self, filename, dirname):
        try:
            FN = self.getAlmostAbsolute(filename, dirname)
            posn = self.getPositionAbsolute(self.getAbsolute(filename, dirname))
            win = self.control.GetPage(posn).GetWindow1()
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
            ## self.OnRefresh(None, win)
        except:
            self.exceptDialog("Reload failed")
            ## self.dialog("Error encountered while trying to reload from disk.", "Reload failed")

    def sharedsave(self, win, force=0):
        nam = win.filename
        ex = wx.CANCEL*bool(not force)
        if not win.dirname.strip():
            nam = "<untitled %i>"%win.NEWDOCUMENT
        a = self.dialog("%s was modified after last save.\nSave changes before closing?"%nam,\
                        "Save changes?", wx.YES_NO|ex)
        if a == wx.ID_CANCEL:
            raise cancelled
        elif a == wx.ID_NO:
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
            #only save difference between the document state and the default
            #state for this document...
            ftype = extns.get(win.filename.split('.')[-1].lower(), 'python')
            dflt = document_defaults.get(ftype, DOCUMENT_DEFAULTS)

            x = win.GetSaveState()
            for i in x.keys():
                if i in dflt and x[i] == dflt[i]:
                    del x[i]
                    if DEBUG: print "shared default", i

            self.curdocstates[fn] = x

        if self.isOpen(win.filename, win.dirname):
            self.lastused[fn] = self.curdocstates.pop(fn, {})
            self.closeOpen(win.filename, win.dirname)
            self.SetStatusText("Closed %s"%self.getAlmostAbsolute(win.filename, win.dirname))
        else:
            self.SetStatusText("Closed unnamed file without saving")
        if self.gf:
            self.gf.close_hierarchy(win)
        if hasattr(win, "kill"):
            win.kill()
        if hasattr(win, 't'):
            win.t.Stop()
            win.t2.Stop()
        self.control.DeletePage(wnum)
        self.updateWindowTitle()
        self.docpanel._refresh()
        wx.CallAfter(self._updateChecks)

    def OnRestart(self, e):
        self.OnExit(e)
        _restart()

    def OnExit(self,e):
        try: e.SetCanVeto(1) #try make this vetoable
        except: pass
        force_user = not getattr(e, 'CanVeto', lambda:1)()
        if self.closing:
            return e.Skip()
        self.closing = 1
        cnt = self.control.GetPageCount()
        sel = self.control.GetSelection()
        try:
            for i in xrange(cnt):
                win = self.control.GetPage(i).GetWindow1()

                if isdirty(win):
                    self.control.SetSelection(i)
                    self.sharedsave(win, force_user)
                else:
                    self.curdocstates[self.getAlmostAbsolute(win.filename, win.dirname)] = win.GetSaveState()
        except cancelled:
            self.closing = 0
            if sel > -1:
                self.control.SetSelection(sel)
            try: return e.Veto()
            except: return

        self.saveHistory()
        parse_queue.put(None)
        file_mods_to_check.put((None, None))
        ShutdownScheduler()
        documents.die = None
        if sel > -1:
            self.control.SetSelection(sel)
        return self.Close(True)

#--------------------------- cmt-001 - 08/06/2003 ----------------------------
#------------- Open the file selected from the file history menu -------------
    def OnFileHistory(self, e):
        fileNum = e.GetId() - wx.ID_FILE1
        path = self.fileHistory.GetHistoryFile(fileNum)
        self.OnDrop([path])
#------------------------- end cmt-001 - 08/06/2003 --------------------------

#----------------------------- Edit Menu Methods -----------------------------
    def OneCmd(self, funct_name, evt):
        wnum, win = self.getNumWin(evt)
        ff = self.FindFocus()
        if ff != win:
            if isinstance(ff, (wx.ComboBox, wx.TextCtrl)):
                if isinstance(ff, wx.ComboBox):
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
    def OnPasteAndDown(self, e):
        self.OneCmd('PasteAndDown',e)
    def OnPasteRectangular(self, e):
        self.OneCmd('PasteRectangular',e)
    def OnDeleteRight(self, e):
        self.OneCmd('DeleteRight',e)
    def OnDeleteLine(self, e):
        self.OneCmd('DeleteLine',e)

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
        if isinstance(box, wx.TextCtrl):
            box.SetSelection(0, box.GetLastPosition())
        else:
            box.SetMark(0, box.GetLastPosition())

    def OnFindAgain(self, evt):
        num, win = self.getNumWin(evt)
        if win.parent.IsSplit():
            win.parent.GetWindow2().OnFindN(evt)
        win.SetFocus()

#----------------------------- View Menu Methods -----------------------------
    def OnZoom(self, e):
        wnum, win = self.getNumWin(e)
        if e.GetId() == ZI:incr = 1
        else:              incr = -1
        win.SetZoom(win.GetZoom()+incr)

    def OnGoto(self, e):

        wnum, win = self.getNumWin(e)
        valu = self.getInt('Which line would you like to advance to?', '', win.LineFromPosition(win.GetSelection()[0])+1)
        win.GotoLineS(valu)

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
        if 'filter' not in window_management.enabled:
            self.SetStatusText("Error: you must enable the filter in 'Options -> Tool Options' to use this feature")
            return

        num, win = self.getNumWin(e)

        if hasattr(self, 'single_ctrl'):
            x = self.single_ctrl
        else:
            x = self.RIGHTNB

        for i in xrange(x.GetPageCount()):
            if x.GetPage(i) == self.filterl:
                x.SetSelection(i)
                break

        gcp = win.GetCurrentPos()
        st = win.WordStartPosition(gcp, 1)
        end = win.WordEndPosition(gcp, 1)

        f = win.docstate.filter
        f.cs.SetValue(1)
        f.filter.SetValue(win.GetTextRange(st, end))
        f.how.SetValue('exact')
        f.update()
        f.filter.SetFocus()

    def OnSplitW(self, e):
        self._OnSplit(self.altview)
    def OnSplitT(self, e):
        self._OnSplit(self.altview2)
    def _OnSplit(self, alt):
        num, win = self.getNumWin()
        alt.SetDocPointer(NULLDOC) #reset the pointer first
        alt.SetDocPointer(win.GetDocPointer())
        x = win.GetSaveState(1)
        del x['FOLD']
        alt.SetSaveState(x)
        alt.SetLexer(win.GetLexer())
        alt.changeStyle(stylefile, self.style(win.filename))

        for i in xrange(alt.parent.GetPageCount()):
            if alt.parent.GetPage(i) is alt:
                alt.parent.SetSelection(i)
                break

        if not alt.parent.GetParent().IsSplit():
            alt.parent.GetParent().Split()

    def OnUnsplit(self, e):
        self.altview.SetDocPointer(NULLDOC)
        self.altview2.SetDocPointer(NULLDOC)

#--------------------------- Document Menu Methods ---------------------------

    def OnStyleChange(self,e):
        wnum, win = self.getNumWin(e)
        lang = lexers[e.GetId()]
        win.changeStyle(stylefile, lang)
        win.triggers = document_defaults[lang]['triggers']
        wx.CallAfter(self.control.updateChecks, win)

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
        wx.CallAfter(self.control.updateChecks, win)

    def OnLineEndChange(self, e):
        n, win = self.getNumWin(e)
        endid = e.GetId()
        newend = LE_MAPPING[endid][0]
        oldend = win.GetEOLMode()
        if oldend != newend:
            win.format = fmt_Rmode[newend]
            win.ConvertEOLs(newend)
            win.SetEOLMode(newend)
        wx.CallAfter(self.control.updateChecks, win)

    def OnAutoCompleteToggle(self, event):
        # Images are specified with an appended "?type"
        #for i in range(len(kw)):
        #    if kw[i] in keyword.kwlist:
        #        kw[i] = kw[i]# + "?1"
        n, win = self.getNumWin(event)
        win.showautocomp = not win.showautocomp
        self.control.updateChecks(win)

    def OnUseMethodsToggle(self, e):
        n, win = self.getNumWin(e)
        win.fetch_methods = not win.fetch_methods

    def OnNumberToggle(self, e):
        n, win = self.getNumWin(e)
        win.SetMarginWidth(0, not win.GetMarginWidth(0))

    def OnMarginToggle(self, e):
        n, win = self.getNumWin(e)
        win.SetMarginWidth(1, (win.GetMarginWidth(1)+16)%32)

    def OnIndentGuideToggle(self, e):
        n, win = self.getNumWin(e)
        win.SetIndentationGuides(not win.GetIndentationGuides())

    def OnWhitespaceToggle(self, e):
        n, win = self.getNumWin(e)
        win.SetViewWhiteSpace(not win.GetViewWhiteSpace())

    def OnLineEndingToggle(self, e):
        n, win = self.getNumWin(e)
        win.SetViewEOL(not win.GetViewEOL())

    def OnSavePositionToggle(self, e):
        n, win = self.getNumWin(e)
        win.save_cursor = not win.save_cursor

    def HightlightLineToggle(self, e):
        n, win = self.getNumWin(e)
        win.SetCaretLineVisible(not win.GetCaretLineVisible())

    def OnExpandAll(self, e):
        n, win = self.getNumWin(e)
        lc = win.GetLineCount()
        win.ShowLines(0, lc-1)
        for line in xrange(lc):
            if win.GetFoldLevel(line) & stc.STC_FOLDLEVELHEADERFLAG:
                win.SetFoldExpanded(line, 1)

    def OnFoldAll(self, e):
        n, win = self.getNumWin(e)
        #these next two lines are to allow
        #win.GetFoldLevel() to be accurate
        win.HideLines(0, win.GetLineCount()-1)
        try: wx.Yield()
        except: pass

        #toss all the old folds
        self.OnExpandAll(e)

        lc = win.GetLineCount()
        lines = []
        for line in xrange(lc):
            if win.GetFoldLevel(line) & stc.STC_FOLDLEVELHEADERFLAG:
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
        win.sloppy = not win.sloppy

    def OnSmartPaste(self, e):
        wnum, win = self.getNumWin(e)
        win.smartpaste = not win.smartpaste

    def WrapToggle(self, win):
        #tossing the current home/end key configuration, as it will change
        win.CmdKeyClear(stc.STC_KEY_HOME,0)
        win.CmdKeyClear(stc.STC_KEY_HOME,stc.STC_SCMOD_SHIFT)
        win.CmdKeyClear(stc.STC_KEY_HOME,stc.STC_SCMOD_ALT)
        win.CmdKeyClear(stc.STC_KEY_HOME,stc.STC_SCMOD_ALT|stc.STC_SCMOD_SHIFT)
        win.CmdKeyClear(stc.STC_KEY_END,0)
        win.CmdKeyClear(stc.STC_KEY_END,stc.STC_SCMOD_SHIFT)
        win.CmdKeyClear(stc.STC_KEY_END,stc.STC_SCMOD_ALT)
        win.CmdKeyClear(stc.STC_KEY_END,stc.STC_SCMOD_ALT|stc.STC_SCMOD_SHIFT)

        if win.GetWrapMode() == stc.STC_WRAP_NONE:
            win.SetWrapMode(stc.STC_WRAP_WORD)

            #making home and end work like we expect them to when lines are wrapped
            win.CmdKeyAssign(stc.STC_KEY_HOME, 0, stc.STC_CMD_HOMEDISPLAY)
            win.CmdKeyAssign(stc.STC_KEY_HOME, stc.STC_SCMOD_SHIFT, stc.STC_CMD_HOMEDISPLAYEXTEND)
            win.CmdKeyAssign(stc.STC_KEY_HOME, stc.STC_SCMOD_ALT, stc.STC_CMD_VCHOME)
            win.CmdKeyAssign(stc.STC_KEY_HOME, stc.STC_SCMOD_ALT|stc.STC_SCMOD_SHIFT, stc.STC_CMD_VCHOMEEXTEND)
            win.CmdKeyAssign(stc.STC_KEY_END, 0, stc.STC_CMD_LINEENDDISPLAY)
            win.CmdKeyAssign(stc.STC_KEY_END, stc.STC_SCMOD_SHIFT, stc.STC_CMD_LINEENDDISPLAYEXTEND)
            win.CmdKeyAssign(stc.STC_KEY_END, stc.STC_SCMOD_ALT, stc.STC_CMD_LINEEND)
            win.CmdKeyAssign(stc.STC_KEY_END, stc.STC_SCMOD_ALT|stc.STC_SCMOD_SHIFT, stc.STC_CMD_LINEENDEXTEND)
        else:
            win.SetWrapMode(stc.STC_WRAP_NONE)

            #making home and end work like we expect them to when lines are not wrapped
            win.CmdKeyAssign(stc.STC_KEY_HOME, 0, stc.STC_CMD_VCHOME)
            win.CmdKeyAssign(stc.STC_KEY_HOME, stc.STC_SCMOD_SHIFT, stc.STC_CMD_VCHOMEEXTEND)
            win.CmdKeyAssign(stc.STC_KEY_HOME, stc.STC_SCMOD_ALT, stc.STC_CMD_HOMEDISPLAY)
            win.CmdKeyAssign(stc.STC_KEY_HOME, stc.STC_SCMOD_ALT|stc.STC_SCMOD_SHIFT, stc.STC_CMD_HOMEDISPLAYEXTEND)
            win.CmdKeyAssign(stc.STC_KEY_END, 0, stc.STC_CMD_LINEEND)
            win.CmdKeyAssign(stc.STC_KEY_END, stc.STC_SCMOD_SHIFT, stc.STC_CMD_LINEENDEXTEND)
            win.CmdKeyAssign(stc.STC_KEY_END, stc.STC_SCMOD_ALT, stc.STC_CMD_LINEENDDISPLAY)
            win.CmdKeyAssign(stc.STC_KEY_END, stc.STC_SCMOD_ALT|stc.STC_SCMOD_SHIFT, stc.STC_CMD_LINEENDDISPLAYEXTEND)

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
        wx.CallAfter(self.control.updateChecks, win)
#--------------------------- Options Menu Methods ----------------------------

    def OnSaveLang(self, e):
        mid = e.GetId()
        lang, desc = SOURCE_ID_TO_OPTIONS.get(mid, ('python', ''))
        n, win = self.getNumWin()
        dct = win.GetSaveState()
        dct.pop('BM', None)
        dct.pop('FOLD', None)
        dct.pop('checksum', None)
        dct.pop('cursor_posn', None)
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
        wx.CallAfter(self.control.updateChecks, None)

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

    def OnMethodColorToggle(self, e):
        codetree.colored_icons = not codetree.colored_icons
        self.OnRefresh(None)

    def OnLogBarToggle(self, e):
        global logbarlocn
        logbarlocn = not logbarlocn
        if self.BOTTOM.IsSplit():
            self.BOTTOM.swapit()

    def OnDocBarToggle(self, e):
        global docbarlocn
        docbarlocn = not docbarlocn
        if self.RIGHT.IsSplit():
            self.RIGHT.swapit()

    def OnShowWideToggle(self, e):
        global SHOWWIDE
        SHOWWIDE = not SHOWWIDE
        if SHOWWIDE:
            self.client2.Split()
            ## self.BOTTOM.Show()
        else:
            self.client2.Unsplit()
            ## self.BOTTOM.Hide()
        self.OnSize(None)
        self.menubar.Check(WIDE_ID, SHOWWIDE)

    def OnShowTallToggle(self, e):
        global SHOWTALL
        SHOWTALL = not SHOWTALL
        if SHOWTALL:
            self.client.Split()
            ## self.RIGHT.Show()
        else:
            self.client.Unsplit()
            ## self.RIGHT.Hide()
        self.OnSize(None)
        self.menubar.Check(TALL_ID, SHOWTALL)

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
    def OnTodoToggle(self, e):
        global TODOBOTTOM
        TODOBOTTOM = not TODOBOTTOM

    def OnStrictTodoToggle(self, e):
        global STRICT_TODO
        STRICT_TODO = not STRICT_TODO

    def OnBOMToggle(self, e):
        global always_write_bom
        always_write_bom = not always_write_bom

    def OnToolBar(self, e):
        global TOOLBAR
        TOOLBAR = TB_MAPPING[e.GetId()][0]
        self.SetStatusText("To apply your changed toolbar settings, restart PyPE.")
        wx.CallAfter(self.control.updateChecks, None)

    def OnCaret(self, e):
        global caret_option
        i = e.GetId()
        caret_option, flags = CARET_ID_TO_OPTIONS[i][:2]
        wx.CallAfter(self.control.updateChecks, None)
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

    def OnBrowseInterpreter(self, e):
        wd = os.getcwd()
        dlg = wx.FileDialog(
            self, message="Choose a Python Interpreter", defaultDir=wd,
            defaultFile="", wildcard="All files (*.*)|*.*",
            style=wx.OPEN|wx.HIDE_READONLY|wx.FILE_MUST_EXIST
            )

        x = interpreter.python_choices[:]
        if dlg.ShowModal() == wx.ID_OK:
            interpreter.check_paths(dlg.GetPaths())

        dlg.Destroy()

        for i in interpreter.python_choices:
            if i not in x:
                self.AddPythonOption(i, i==interpreter.which_python)

    def AddPythonOption(self, name, select=0):
        if select:
            for i in PYTHON_INTERPRETER_CHOICES:
                self.menubar.Check(i, 0)

        nid = wx.NewId()
        PYTHON_INTERPRETER_CHOICES.append(nid)

        menuAdd(self, self.python_choices, name, "Will use %s as the interpreter for the 'Python Shell' when checked"%name, self.OnChoosePython, nid, wx.ITEM_CHECK)
        self.menubar.Check(nid, select)

    def OnChoosePython(self, e):
        for i in PYTHON_INTERPRETER_CHOICES:
            self.menubar.Check(i, 0)

        self.menubar.Check(e.GetId(), 1)
        interpreter.which_python = self.menubar.GetLabel(e.GetId()).strip()

    def OnShellStyle(self, e):
        global SHELL_OUTPUT
        for i in SHELL_OUTPUT_OPTIONS:
            self.menubar.Check(i, 0)
        self.menubar.Check(e.GetId(), 1)

        SHELL_OUTPUT = SHELL_OUTPUT_OPTIONS[e.GetId()][0]

    def OnShellColor(self, e):
        global SHELL_COLOR
        data = wx.ColourData()
        data.SetChooseFull(True)
        data.SetColour(SHELL_COLOR)
        dlg = wx.ColourDialog(self, data)
        changed = dlg.ShowModal() == wx.ID_OK

        if changed:
            c = dlg.GetColourData().GetColour()
            SHELL_COLOR = '#%02x%02x%02x'%(c.Red(), c.Green(), c.Blue())
        dlg.Destroy()

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

    def OnSyntaxChange(self, e):
        for i in SYNTAX_CHECK_DELAY_ID_TO_NUM:
            self.menubar.Check(i, 0)
        self.menubar.Check(e.GetId(), 1)
        global HOW_OFTEN1
        HOW_OFTEN1 = SYNTAX_CHECK_DELAY_ID_TO_NUM[e.GetId()]


    def OnRefreshChange(self, e):
        for i in REFRESH_DELAY_ID_TO_NUM:
            self.menubar.Check(i, 0)
        self.menubar.Check(e.GetId(), 1)
        global HOW_OFTEN2
        HOW_OFTEN2 = REFRESH_DELAY_ID_TO_NUM[e.GetId()]

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
        findbar_location = not findbar_location

    def OnFindbarHistory(self, e):
        global no_findbar_history
        no_findbar_history = not no_findbar_history
        self.menubar.FindItemById(CLEAR_FINDBAR_HISTORY).Enable(not no_findbar_history)

    def OnChangeMenu(self, e):
        keydialog.MenuItemDialog(self, self).ShowModal()

    def OnChangeTitle(self, e):
        global title_option
        i = e.GetId()
        title_option, _, _ = TITLE_ID_TO_OPTIONS[i]
        self.updateWindowTitle()
        wx.CallAfter(self.control.updateChecks, None)

    def OnChangeDocumentsOptions(self, e):
        global document_options
        i = e.GetId()
        document_options = DOCUMENT_LIST_OPTIONS[i][0]
        self.docpanel._setcolumn()
        self.docpanel._refresh()
        wx.CallAfter(self.control.updateChecks, None)

    def OnChangeDocumentsOptions2(self, e):
        global document_options2
        i = e.GetId()
        document_options2 = DOCUMENT_LIST_OPTIONS2[i][0]
        self.docpanel._setcolumn()
        self.docpanel._refresh()
        wx.CallAfter(self.control.updateChecks, None)

    def OnShowRecentDocs(self, e):
        global show_recent
        show_recent = not show_recent

    def OnShowQuickbrowse(self, e):
        global show_search
        show_search = not show_search

    def OnChangeMacroOptions(self, e):
        global macro_doubleclick
        i = e.GetId()
        macro_doubleclick = MACRO_CLICK_OPTIONS[i][0]
        wx.CallAfter(self.control.updateChecks, None)

    def OnToolToggle(self, e):
        tool = e.GetId()
        info = TOOLS_ENABLE_L[TOOLS_ENABLE[tool]]
        if info[1] == 'Global Filter':
            global global_filter_table
            global_filter_table = not global_filter_table
            if global_filter_table:
                self.RIGHTNB.InsertPage(self.gfp, self.gf, "GlobalF")
                wx.CallAfter(self.gf.OnText, None)
            else:
                self.RIGHTNB.RemovePage(self.gfp)
                self.gf.Hide()
        elif info[4] in window_management.enabled:
            window_management.enabled.pop(info[4])
            t = getattr(self, info[3])
            t.Hide()
            for i in xrange(t.parent.GetPageCount()):
                if t.parent.GetPage(i) == t:
                    t.parent.RemovePage(i)
                    break
        else:
            window_management.enabled[info[4]] = None
            t = getattr(self, info[3])
            t.parent.AddPage(t, info[1])
            for i in self.control:
                if hasattr(i, '_invalidate_cache'):
                    i._invalidate_cache()
            win = self.getNumWin()[1]
            win.docstate.Show()

    def OnMacroButtonImage(self, e):
        global macro_images
        macro_images = not macro_images

    def OnSavePreferences(self, e):
        self.saveHistory()

#----------------------------- Help Menu Methods -----------------------------
    def OnAbout(self, e):

        t = []
        used = USED_TIME
        for i,j in ((60, 'seconds'), (60, 'minutes'), (24, 'hours')):
            if not used:
                break
            k = used%i
            if k:
                t.insert(0, "%s %s"%(k, j))
            used = (used-k)/i
        if used:
            t.insert(0, "%s %s"%(used, "days"))

        t = ', '.join(t)

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
        of this document.

        You have used PyPE for: %s"""%(VERSION, t)
        self.dialog(txt.replace('        ', ''), "About...")

    def OnHelp(self, e):
        if not SHOWWIDE:
            self.OnShowWideToggle(None)
        for i in xrange(self.BOTTOMNB.GetPageCount()):
            if isinstance(self.BOTTOMNB.GetPage(i), help.MyHtmlWindow):
                self.BOTTOMNB.SetSelection(i)
                break

        def fixsize():
            h = self.BOTTOM.GetSize()[1]//2
            self.BOTTOM.SetSashPosition(h)

        wx.CallAfter(fixsize)

#-------------------------- Hot Key support madness --------------------------
    def keyboardShortcut(self, keypressed, evt=None):
        menuid = HOTKEY_TO_ID[keypressed]
        wx.PostEvent(self, wx.MenuEvent(wx.wxEVT_COMMAND_MENU_SELECTED, menuid))

    def OnKeyPressed(self, event):
        showpress=0
        self._activity()
        keypressed = GetKeyPress(event)

        #fix for funky bug on OS X
        if not self.menubar.IsEnabled(wx.ID_UNDO):
            for menuid in (wx.ID_UNDO, wx.ID_REDO, wx.ID_CUT, wx.ID_COPY):
                self.menubar.Enable(menuid, 1)

        if showpress: print "keypressed", keypressed

        if keypressed in HOTKEY_TO_ID:
            return self.keyboardShortcut(keypressed, event)
        if self.macropage.RunMacro(keypressed):
            return

        key = GetKeyCode(event)
        wnum = self.control.GetSelection()
        pagecount = self.control.GetPageCount()
        if wnum > -1:
            win = self.control.GetPage(wnum).GetWindow1()

        if pagecount:
            if (key==13):
                if type(self.FindFocus()) not in (PythonSTC, interpreter.MyShell):
                    return event.Skip()
                #when 'enter' is pressed, indentation needs to happen.
                if win.AutoCompActive():
                    return win.AutoCompComplete()
                if win.CallTipActive():
                    win.CallTipCancel()
                win._autoindent()
            elif key == wx.WXK_ESCAPE:
                if win.AutoCompActive():
                    win.AutoCompCancel()
                if win.CallTipActive():
                    win.CallTipCancel()
            else:
                event.Skip()
                if not (win.GetStyleAt(win.GetCurrentPos())):
                    #3, 13, 6, 7
                    if win.CallTipActive():
                        good = STRINGPRINTABLE
                        if (key in good) or (key in (wx.WXK_SHIFT, wx.WXK_CONTROL, wx.WXK_ALT)):
                            pass
                            #if key in (48, 57) and event.ShiftDown():
                            #    win.CallTipCancel()
                            #else it is something in the arguments that is OK.
                        else:
                            ## print "calltipcancel"
                            win.CallTipCancel()
                    if (not win.CallTipActive()) and event.ShiftDown() and (key == ord('9')):
                        ## self._ct(win, 1)
                        wx.CallAfter(self._ct, win, 1)
                    elif win.showautocomp and bool(win.kw or win.hierarchy):
                        if keypressed.split('+')[-1] in _keys:
                            return
                        if keypressed.endswith('+') and not keypressed.endswith('++'):
                            return
                        wx.CallAfter(self._ac, win)

        else:
            return event.Skip()

    def getLeftFunct(self, win, skip=0):
        bad = dict.fromkeys('\t .,;:([)]}\'"\\<>%^&+-=*/|`\r\n')
        line = win.lines.curline.rstrip('\r\n')
        #can't use self.lines.curlinep because it uses utf-aligned positions
        #on get, but it uses actual columns on set
        colpos = win.GetColumn(win.GetCurrentPos())-skip
        cur = colpos-1
        ## print line[cur:cur+1]
        while (cur >= 0) and line[cur:cur+1] not in bad:
            cur -= 1
            ## print line[cur:cur+1]
        cur += 1
        return cur, colpos, line[cur:colpos], win._is_method(win.lines.curlinei, line, cur)

    def _ct(self, win, skip):
        ## print "calltipshow"
        win.CallTipSetBackground(wx.Colour(255, 255, 232))
        cur, colpos, word, _ = self.getLeftFunct(win, skip)
        tip = '\n'.join(win.tooltips.get(word, []))
        if tip:
            win.CallTipShow(win.GetCurrentPos(),tip)
        ## else:
            ## print "no tip", repr(word)

    def _ac(self, win):
        cur, colpos, word, method = self.getLeftFunct(win)
        if not word:
            return win.AutoCompCancel()

        ## print "got word:", word

        words = None
        if method and win.fetch_methods:
            ## print "found method!"
            words = win._method_listing(win.lines.curlinei, cur, word) or []
        if not words:
            words = sorted([i for i in win.kw.split() if i.startswith(word)] + win._name_listing(win.lines.curlinei, cur, word))

        if len(words) == 0:
            ## print 'no words!'
            return win.AutoCompCancel()
        if len(words) == 1 and words[-1] == word:
            ## print "exact words"
            return win.AutoCompCancel()

        words = ' '.join(words)
        ## print "got words:", repr(words)
        win.AutoCompSetIgnoreCase(False)
        win.AutoCompShow(len(word), words)


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
encoding_template = '''\
        Based on BOM detection, coding declarations,
        and defined defaults for the file type you are
        opening, PyPE determined that your file was
        likely encoded as %r, but its attempt to decode
        your document failed due to:
        %s
        It will now try to decode your document as %r,
        and depending on the content of your file, may
        result in data corruption if this decision was
        not correct and you attempt to save your file.

        If you believe PyPE to be in error, do not save
        your file, and contact PyPE's author.'''.replace(8*' ', '')
#

def chain(*args):
    for i in args:
        for j in i:
            yield j

class PythonSTC(stc.StyledTextCtrl):
    def __init__(self, notebook, ID, parent):
        stc.StyledTextCtrl.__init__(self, parent, ID)#, style = wx.NO_FULL_REPAINT_ON_RESIZE)
        self.SetWordChars('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
        self.SetEndAtLastLine(False)
        self.paste_rectangle = None
        self.cached = None
        self.MarkerDefine(BOOKMARKNUMBER, BOOKMARKSYMBOL, 'blue', 'blue')

        _, flags = CARET_OPTION_TO_ID[caret_option]
        self.SetXCaretPolicy(flags, caret_slop*caret_multiplier)
        self.SetYCaretPolicy(flags, caret_slop)

        self.hierarchy = []
        self.kw = ''
        self.tooltips = {}
        self.ignore = {}
        self.lines = lineabstraction.LineAbstraction(self)

        self.parent = parent
        self.notebook = notebook #should also be equal to self.parent.parent
        try:
            self.root = self.notebook.root
        except:
            self.root = root
        self.sloppy = 0
        self.smartpaste = 0
        self.dirty = 0
        self.refresh = 0
        self.lexer = 'text'
        self.selep = None
        self.recording = 0
        self.macro = []
        self.fetch_methods = 0
        self.fetch_methods_cache = [-1, 0, '', []]

        #drop file and text support
        self.SetDropTarget(FileDropTarget(self.root))

        #for command comlpetion
        self.SetKeyWords(0, " ".join(keyword.kwlist))

        self.SetMargins(0,0)
        self.SetViewWhiteSpace(False)
        self.SetBackSpaceUnIndents(1)
        #self.SetBufferedDraw(False)
        #self.SetViewEOL(True)

        self.SetMarginType(0, stc.STC_MARGIN_NUMBER)
        #self.StyleSetSpec(stc.STC_STYLE_LINENUMBER, "size:%(size)d,face:%(mono)s" % faces)

        # Setup a margin to hold fold markers
        #I agree, what is this value?
        #self.SetFoldFlags(16)  ###  WHAT IS THIS VALUE?  WHAT ARE THE OTHER FLAGS?  DOES IT MATTER?

        self.SetProperty("fold", "1")
        self.SetMarginType(2, stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(2, stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(2, True)
        self.SetMarginWidth(2, 12)
        if hasattr(self, 'SetPasteConvertEndings'):
            self.SetPasteConvertEndings(1)

        if collapse_style: # simple folder marks, like the old version
            self.MarkerDefine(stc.STC_MARKNUM_FOLDER, stc.STC_MARK_BOXPLUS, "navy", "white")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN, stc.STC_MARK_BOXMINUS, "navy", "white")
            # Set these to an invisible mark
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_BACKGROUND, "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_BACKGROUND, "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB, stc.STC_MARK_BACKGROUND, "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL, stc.STC_MARK_BACKGROUND, "white", "black")

        else: # more involved "outlining" folder marks
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_BOXPLUSCONNECTED,  "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_BOXMINUSCONNECTED, "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNER,  "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_LCORNER,  "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_VLINE,    "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_BOXPLUS,  "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_BOXMINUS, "white", "black")


        # Make some styles,  The lexer defines what each style is used for, we
        # just have to define what each style looks like.  This set is adapted from
        # Scintilla sample property files.

        #And good wxPython users who have seen some demos know the above was copied
        #and pasted, along with a lot of sample code, right out of the demo.  The
        #demo r0XX0rs.

        # Global default styles for all languages
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "fore:#000000,face:%(mono)s,back:#FFFFFF,size:%(size)d" % faces)
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  "back:#C0C0C0,face:%(mono)s,size:%(size2)d" % faces)
        self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, "face:%(other)s" % faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,  "fore:#003000,face:%(mono)s,back:#80E0E0"% faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,    "fore:#E0FFE0,face:%(mono)s,back:#FF0000"% faces)

        #various settings
        self.SetSelBackground(1, '#B0B0FF')

        #again, some state variables
        self.filename = ''
        self.dirname = ''
        self.opened = 0
        self.AutoCompStops(' .,;:()[]{}\'"\\<>%^&+-=*/|`')

        stc.EVT_STC_UPDATEUI(self,    ID, self.OnUpdateUI)
        stc.EVT_STC_MARGINCLICK(self, ID, self.OnMarginClick)
        wx.EVT_KEY_DOWN(self, self.root.OnKeyPressed)
        #wx.EVT_CHAR(self, self.root.OnKeyPressed)
        wx.EVT_KEY_UP(self, self.key_up)

        stc.EVT_STC_CHARADDED(self, ID, self.added)
        stc.EVT_STC_CHANGE(self, ID, self.key_up)
        #unavailable in 2.5.1.2, didn't work in previous versions of wxPython
        # stc.EVT_STC_POSCHANGED(self, ID, self.pos)
        stc.EVT_STC_SAVEPOINTREACHED(self, ID, self.MakeClean)
        stc.EVT_STC_SAVEPOINTLEFT(self, ID, self.MakeDirty)
        stc.EVT_STC_NEEDSHOWN(self, ID, self.OnNeedShown)
        self.Bind(stc.EVT_STC_MACRORECORD, self.GotEvent)
        self.SetModEventMask(stc.STC_MOD_INSERTTEXT|stc.STC_MOD_DELETETEXT|stc.STC_PERFORMED_USER|stc.STC_PERFORMED_UNDO|stc.STC_PERFORMED_REDO)

        if REM_SWAP:
            self.CmdKeyClear(ord('T'), stc.STC_SCMOD_CTRL)

        self.CmdKeyClear(ord('Z'), stc.STC_SCMOD_CTRL)
        self.CmdKeyClear(ord('Y'), stc.STC_SCMOD_CTRL)
        self.CmdKeyClear(ord('X'), stc.STC_SCMOD_CTRL)
        self.CmdKeyClear(ord('C'), stc.STC_SCMOD_CTRL)
        self.CmdKeyClear(ord('V'), stc.STC_SCMOD_CTRL)
        self.CmdKeyClear(ord('A'), stc.STC_SCMOD_CTRL)

        ## self.dragstartok = 0
        ## self.dragging = 0
        ## sekf.have_selection = 0

        ## self.Bind(wx.EVT_MOTION, self._checkmouse)
        ## self.Bind(wx.EVT_LEFT_DOWN, self._checkmouse2)
        ## self.Bind(wx.EVT_LEFT_UP, self._checkmouse3)
        self.has_bad = 0
        self.lastparse = _MULT[HOW_OFTEN1]*1000
        self.lastparse2 = _MULT[HOW_OFTEN2]*1000
        self.m1 = None
        self.m2 = None
        self.automatic = 0
        try:
            self.SetTwoPhaseDraw(1)
        except:
            pass

        try:
            self.IndicatorSetUnder(1)
        except:
            pass

    def gotcharacter(self):
        ## self._gotcharacter()
        self.root._activity(self.lexer == 'python', self)

    def _checkmouse(self, evt):
        if self.dragging or not self.dragstartok or not evt.Dragging():
            return
        self._startdrag(evt)

    def _checkmouse2(self, evt):
        self.dragstartok = 1
        evt.Skip()

    def _checkmouse3(self, evt):
        self.dragstartok = 0
        evt.Skip()

    def _startdrag(self, evt):
        if self.SelectionIsRectangle():
            return evt.Skip()

        #Need to differentiate between discovering the initial selection
        #and dragging that selection.  Still working on making it reliable.

    def _filetype(self):
        if '.' not in self.filename:
            return lexer2lang.get(self.GetLexer(), 'python')
        return get_filetype(self.filename)

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
        stc.StyledTextCtrl.StopRecord(self)
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
                for i in re.split('(%L)', todo): # '(%-?L)'
                    if i == '%L':
                        self._autoindent()
                    ## elif i == '%-L':
                        ## self._autoindent()
                        ## l = max(self.GetSelection())
                        ## self.SetSelection(l,l)
                        ## self.Dent(None, -1)
                    else:
                        self.ReplaceSelection(i)
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
            wx.Yield()
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

        self.gotcharacter()

    def pos_ch(self, e):
        if self.root.control.GetCurrentPage() == self.GetParent():
            if not hasattr(self, 'lines'):
                return
            l = self.lines
            self.root.SetStatusText("L%i C%i"%(l.curlinei+1, l.curlinep), 1)
        if e:
            e.Skip()

        self.gotcharacter()

    def added(self, e):
        if self.recording:
            if e:
                self.macro.append((2170, 0, _decode_key(e.GetKey())))
            ## print "got key", repr(self.macro[-1][-1]), e.GetKey()

        expanded = 0
        try:
            full = e is None
            tr = self.triggers
            fcn = self.PositionBefore
            pp = gcp = self.GetCurrentPos()
            p = fcn(gcp)
            c = 1
            while pp != p:
                if not full and c > 1:
                    break
                ## print repr(tr)
                ch = self.GetTextRange(p,pp)
                c += 1
                ## print repr(ch), tr.keys()
                tr = tr.get(ch, None)
                if tr is None:
                    ## print "ran off of triggers!", repr(ch), p, gcp
                    break
                elif isinstance(tr, (str, unicode)):
                    if e:
                        self.macro.append((None, 1, 'added'))

                    self.SetSelection(p, gcp)
                    self.ReplaceSelection('')
                    self.InterpretTrigger(tr)

                    expanded = 1
                    break
                pp, p = p, fcn(p)
                ## print p, pp
            else:
                pass
                ## print "not found", p, gcp
        finally:
            self.key_up(e)

    def jump(self, direction):
        #1 forward, -1 backward
        if direction not in (1,-1):
            return

        #set up characters
        chars2, chars3 = '({[:,\'"', ')}]\'"'
        if self.GetLexer() in (stc.STC_LEX_HTML, stc.STC_LEX_XML):
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
    def GetSaveState(self, scp=0):
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
                'show_line_ends':self.GetViewEOL(),
                'sloppy':self.sloppy,
                'smartpaste':self.smartpaste,
                'showline':self.GetCaretLineVisible(),
                'fetch_methods':self.fetch_methods,
               }
        if not self.save_cursor and not scp:
            del ret['cursor_posn']
        if self.GetTextLength() < MAX_SAVE_STATE_DOC_SIZE:
            ret['checksum'] = md5.new(self.GetText(0)).hexdigest()

        if (self.GetLineCount() < MAX_SAVE_STATE_LINE_COUNT and
            self.GetTextLength() < MAX_SAVE_STATE_DOC_SIZE):
            for line in xrange(self.GetLineCount()):
                if self.MarkerGet(line) & BOOKMARKMASK:
                    BM.append(line)

                if (self.GetFoldLevel(line) & stc.STC_FOLDLEVELHEADERFLAG) and\
                (not self.GetFoldExpanded(line)):
                    FOLD.append(line)
            FOLD.reverse()

        return ret

    def SetSaveState(self, saved):
        self.SetUseTabs(saved['use_tabs'])
        self.SetProperty("tab.timmy.whinge.level", "10"[bool(saved['use_tabs'])])
        self.SetTabWidth(saved['spaces_per_tab'])
        self.SetIndent(saved['indent'])
        self.SetMarginWidth(0, saved['line_margin'])
        self.SetMarginWidth(1, 16*saved['marker_margin'])
        self.SetEdgeColumn(saved['col_line'])
        self.SetEdgeMode(saved['col_mode'])
        self.SetIndentationGuides(saved['indent_guide'])
        self.showautocomp = saved['showautocomp']
        self.fetch_methods = saved['fetch_methods']
        self.findbarprefs = dict(saved.get('findbarprefs', {}))
        self.triggers = saved.get('triggers', {})
        self.sloppy = saved['sloppy']
        self.smartpaste = saved['smartpaste']
        self.SetCaretLineVisible(saved['showline'])
        self.SetViewWhiteSpace(saved['whitespace'])
        self.SetViewEOL(saved['show_line_ends'])
        if self.GetWrapMode() != saved['wrapmode']:
            self.root.WrapToggle(self)
        ## self.tree.tree.SORTTREE = saved.get('sortmode', sortmode)
        self.save_cursor = saved['save_cursor']
        for bml in saved.get('BM', []):
            self.MarkerAdd(bml, BOOKMARKNUMBER)

        try: wx.Yield()
        except: pass

        def posn(self, a):
            self.SetSelection(a,a)
            self.EnsureCaretVisible()
            self.ScrollToColumn(0)

        if 'CHECK_VIM' in saved:
            self._check_vim()

        wx.CallAfter(self._update_fold, saved.get('FOLD', []))
        wx.CallAfter(posn, self, saved.get('cursor_posn', 0))

    def _update_fold(self, fold):
        for exl in fold:
            a = self.GetLastChild(exl, -1)
            self.HideLines(exl+1,a)
            self.SetFoldExpanded(exl, 0)

    def _check_vim(self):
        DBG = 0

        if DBG: print "checking vim!"
        sre = re.compile('\s*:set?\s+(.+)')

        #hcl ->  Highlight Current Line
        #ut -> Use Tabs
        #siw -> Set Indent Width
        #stw -> Set Tab Width
        ## #mc -> Match Case

        options = {
            'cursorline':'hcl',
            'cul':'hcl',
            'nocursorline':'!hcl',
            'nocul':'!hcl',
            'expandtab':'!ut',
            'et':'!ut',
            'noexpandtab':'ut',
            'noet':'ut',
            'shiftwidth':'siw',
            'sw':'siw',
            'softtabstop':'siw',
            'sts':'siw', #(shiftwidth preferred)
            'tabstop':'stw',
            'ts':'stw',
            ## 'ignorecase':'mc',
            ## 'ic':'mc',
            ## 'noignorecase':'mc',
            ## 'noic':'mc',
        }

        toggle = ('ut', 'hcl')

        values = {}
        saw_sw = 0

        lines = self.lines
        rex = findinfiles.commentedPatterns[self._filetype()]

        for i in chain(xrange(min(20, len(lines))), xrange(max(20, len(lines)-20), len(lines))):
            comment = rex.search(lines[i])
            if not comment:
                continue
            if DBG: print "comment:", comment.group(1).rstrip()

            set_command = sre.search(comment.group(1).rstrip())
            if not set_command:
                continue

            if DBG: print "set command:", set_command.group(1)

            for o in set_command.group(1).lower().split():
                o = o.replace(':', '=')
                if DBG: print "option:", o,
                inv = 0
                value = None
                if o.startswith('inv'):
                    o = o[3:]
                    inv = 1
                if '!' in o:
                    inv = not inv
                    option = o.replace('!', '')
                elif '=' in o:
                    option, value = o.split('=', 1)
                else:
                    option = o
                if option not in options:
                    if DBG: print "bad option", option
                    continue
                key = options[option]
                ks = key.strip('!')
                if DBG: print "maps to:", ks

                if ks in toggle and value is None:
                    key = '!'*inv + key
                    if key[:2] == '!!':
                        towrite = towrite[2:]
                    if DBG: print "updating toggle", key
                    values[ks] = '!' not in key
                elif ks not in toggle and value:
                    try:
                        value = max(int(value), 1)
                    except ValueError:
                        print "huh:", value
                        continue
                    if key == 'siw' and option in ('shiftwidth','sw'):
                        saw_sw = 1
                    elif saw_sw and key == 'siw':
                        continue
                    if DBG: print "setting", ks, '<-', value
                    values[ks] = value
                else:
                    if DBG: print "insane value!", ks, value
                    continue
        if DBG: print values.items()
        if 'hcl' in values:
            self.SetCaretLineVisible(values['hcl'])
        if 'ut' in values:
            self.SetUseTabs(values['ut'])
            self.SetProperty("tab.timmy.whinge.level", "10"[bool(values['ut'])])
        if 'siw' in values:
            self.SetIndent(values['siw'])
        if 'stw' in values:
            self.SetTabWidth(values['stw'])

#-------------------- fix for SetText for the 'dirty bit' --------------------
    def SetText(self, txt, emptyundo=1):
        tryencodings = ['ascii']
        foundbom = 0
        if UNICODE:
            ## if get_filetype(self.filename) in ('xml', 'html'):
                ## #default XML and HTML encodings are utf-8 by spec:
                ## #http://www.w3.org/TR/2000/REC-xml-20001006#NT-EncodingDecl
                ## tryencodings.append('utf-8')
            for bom, enc in BOM:
                if bom and txt[:len(bom)] == bom:
                    tryencodings.append(enc)
                    txt = txt[len(bom):]
                    foundbom += 1
            twolines = txt.lstrip().split(self.format, 2)[:2]
            foundcoding = 0
            for line in twolines:
                x = re.search('''[cC][oO][dD][iI][nN][gG][=:](?:["'\s]*)([-\w.]+)''', line)
                if not x:
                    continue
                x = x.group(1).lower()
                ## print "ENCODING:", x
                #always try to decode with the BOM first
                tryencodings.insert(len(tryencodings)-foundbom, x)
                foundcoding += 1
                break

            te = []
            while tryencodings:
                i = tryencodings.pop()
                if i not in te:
                    te.append(i)

            te.reverse()

            while len(te) > 1:
                prev = te[-1]
                if te[-1] == 'ascii':
                    te[-1] = 'latin-1'
                try:
                    txt = txt.decode(te[-1])
                except Exception, why:
                    te[-1] = prev
                    self.root.dialog(encoding_template%(te[-1], why, te[-2]),
                                     "%r decoding error"%(te[-1],))
                    _ = te.pop()
                    continue
                else:
                    te[-1] = prev
                    break

            self.enc = te[-1]

            if self.enc not in ADDBOM:
                self.enc = 'other'
        else:
            self.enc = tryencodings[-1]

        self.SetEOLMode(fmt_mode[self.format])
        stc.StyledTextCtrl.SetText(self, txt)
        self.ConvertEOLs(fmt_mode[self.format])
        self.opened = 1
        if emptyundo:
            self.EmptyUndoBuffer()
            self.SetSavePoint()

    def GetText(self, error=1):
        self.ConvertEOLs(fmt_mode[self.format])
        if UNICODE:
            tryencodings = ['utf-8', 'ascii']
            ## if get_filetype(self.filename) in ('xml', 'html'):
                ## #default XML and HTML encodings are utf-8 by spec:
                ## #http://www.w3.org/TR/2000/REC-xml-20001006#NT-EncodingDecl
                ## tryencodings.append('utf-8')

            txt = otxt = stc.StyledTextCtrl.GetText(self)
            twolines = txt.lstrip().split(self.format, 2)[:2]
            #pull the encoding
            for line in twolines:
                x = re.search('''[cC][oO][dD][iI][nN][gG][=:](?:["'\s]*)([-\w.]+)''', line)
                if not x:
                    continue
                tryencodings.append(str(x.group(1).lower()))
                break

            if self.enc != 'other':
                tryencodings.append(self.enc)

            te = []
            while tryencodings:
                i = tryencodings.pop()
                if i not in te:
                    te.append(i)

            why = None
            for i in te:
                prev = i
                if i == 'ascii':
                    i = 'latin-1'
                try:
                    txt = otxt.encode(i)
                except UnicodeEncodeError, wh:
                    i = prev
                    if why is None:
                        why = wh
                else:
                    i = prev
                    if error and ((self.enc != 'other' and self.enc != i) or \
                                  (self.enc == 'other' and i != te[0])):
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
                                '''%(y, te[0], why, i)).replace(32*' ', ''),
                                "Continue with alternate encoding?", wx.YES_NO) != wx.ID_YES:
                            raise cancelled
                        self.root.SetStatusText("Using %r encoding for %s"%(i, y))

                    ## print 'SAVED ENCODING:', i
                    if (always_write_bom and i == te[0]) or (i != te[0]):
                        ## print "added BOM for", i
                        txt = ADDBOM.get(i, '') + txt
                    return txt
            #this exception should never be raised
            raise Exception, "You should contact the author of this software."
        return stc.StyledTextCtrl.GetText(self)

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
        interpreter.FutureCall(1, self.do, stc.StyledTextCtrl.Cut)
    def Copy(self):
        if self.sloppy and not self.SelectionIsRectangle():
            self.SelectLines()
        interpreter.FutureCall(1, self.do, stc.StyledTextCtrl.Copy, 0)

    def _StripPrefix(self, d, newindent=0, dofirst=1):
        if d is None:
            return ''

        #sanitize the information
        lines = d.replace('\r\n', '\n').replace('\r', '\n').split('\n')

        #find the leading indentation for the text
        tabwidth = self.GetTabWidth()
        repl = tabwidth*' '
        x = []
        z = len(d)
        for line in lines:
            leading_whitespace = line[:len(line)-len(line.lstrip())]
            rest = line[len(leading_whitespace):]
            leading_whitespace = leading_whitespace.replace('\t', repl)
            llw = len(leading_whitespace)
            if not rest:
                llw = z
            x.append((llw, leading_whitespace, rest))

        #reindent
        base = newindent*' '
        min_i = min(x)[0]
        usetabs = self.GetUseTabs()
        out = []
        for y, (li, lw, lr) in enumerate(x):
            lw = lw[min_i:]
            if dofirst or y:
                lw = base + lw
            if usetabs:
                lw = lw.replace(repl, '\t')
            out.append(lw+lr)

        return self.format.join(out)

    def Paste(self):
        while self.smartpaste:
            if self.recording:
                self.macro.append((2179, 0, 0))

            x,y = self.GetSelection()
            dofirst = x != y
            d = GetClipboardText()
            if d is None or '\n' not in d:
                if self.recording:
                    _ = self.macro.pop()
                break

            self.BeginUndoAction()
            #create a new line using the auto-indent stuff
            try:
                curline = self.LineFromPosition(x)
                x = self.GetLineEndPosition(curline)
                if not dofirst:
                    self.SetSelection(x,x)
                if not dofirst:
                    cl = self.lines.curline
                    if cl[:self.lines.curlinep].lstrip():
                        self._tdisable(self._autoindent, self)
                    else:
                        self.lines.curlinep = len(cl)-len(cl.lstrip(' \t'))

                newindent = self.GetLineIndentation(self.LineFromPosition(self.GetSelection()[0]))
                x = self._StripPrefix(d, newindent, dofirst)

                #insert the text
                if dofirst:
                    self.lines.selectedlines = []
                self.ReplaceSelection(x)
            finally:
                self.EndUndoAction()
            return

        self.do(stc.StyledTextCtrl.Paste)

    def PasteRectangular(self):
        if self.recording:
            self.macro.append((None, '', 'PasteRectangular'))
        _, self.recording = self.recording, 0
        try:
            sel = GetClipboardText()
            currentPos = self.GetCurrentPos()
            xInsert = self.GetColumn(currentPos)
            line = self.GetCurrentLine()
            prevCr = 0
            self.BeginUndoAction()
            try:
                for i, c in enumerate(sel):
                    if c == '\r' or c == '\n':
                        if c == '\r' or not prevCr:
                            line += 1
                        if line >= self.GetLineCount():
                            if self.GetEOLMode() != wx.SC_EOL_LF:
                                self.InsertText(self.GetLength(), "\r")
                            if self.GetEOLMode() != wx.SC_EOL_CR:
                                self.InsertText(self.GetLength(), "\n")
                        # Pad the end of lines with spaces if required
                        currentPos = self.FindColumn(line, xInsert)
                        if self.GetColumn(currentPos) < xInsert and i + 1 < len(sel):
                            k = max(xInsert - self.GetColumn(currentPos), 0)
                            if k:
                                self.InsertText(currentPos, k*' ')
                                currentPos += k
                        prevCr = c == '\r'
                    else:
                        self.InsertText(currentPos, c);
                        currentPos += 1
                        prevCr = 0
            finally:
                self.EndUndoAction()
        finally:
            self.recording = _
        self.SetSelection(currentPos, currentPos)

    def PasteAndDown(self):
        if self.recording:
            self.macro.append((None, '', 'PasteAndDown'))
        pos = self.GetCurrentPos()
        npr = 1
        if self.paste_rectangle:
            if md5.new(GetClipboardText()).digest() == self.paste_rectangle:
                npr = 0
        _, self.recording = self.recording, 0
        try:
            self.Paste()
            self.SetCurrentPos(pos)
            self.CharLeft()
            if npr:
                self.LineDown()
        finally:
            self.recording = _

    def DeleteSelection(self):  self.do(stc.StyledTextCtrl.DeleteBack)
    def DeleteRight(self):      self.do(stc.StyledTextCtrl.DelLineRight)
    def DeleteLine(self):       self.do(stc.StyledTextCtrl.LineDelete)
    def Undo(self):     self.do(stc.StyledTextCtrl.Undo)
    def Redo(self):     self.do(stc.StyledTextCtrl.Redo)
    def CanEdit(self):
        return 1
#--------- Ahh, the style change code...isn't it great?  Not really. ---------
    def changeStyle(self, stylefile, language):
        try:
            StyleSetter.initSTC(self, stylefile, language)
            self.lexer = language
        except:

            self.root.SetStatusText("Style Change failed for %s, assuming plain text"%language)
            self.root.exceptDialog()
            # we'll go plain text for now
            self.SetLexer(stc.STC_LEX_NULL)
            self.lexer = 'text'
            self.kw = ''
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
        if charBefore and chr(charBefore) in "[]{}()" and styleBefore == stc.STC_P_OPERATOR:
            braceAtCaret = caretPos - 1

        # check after
        if braceAtCaret < 0:
            charAfter = self.GetCharAt(caretPos)
            styleAfter = self.GetStyleAt(caretPos)
            if charAfter and chr(charAfter) in "[]{}()" and styleAfter == stc.STC_P_OPERATOR:
                braceAtCaret = caretPos

        if braceAtCaret >= 0:
            braceOpposite = self.BraceMatch(braceAtCaret)

        if braceAtCaret != -1  and braceOpposite == -1:
            self.BraceBadLight(braceAtCaret)
        else:
            self.BraceHighlight(braceAtCaret, braceOpposite)
            #pt = self.PointFromPosition(braceOpposite)
            #self.Refresh(True, wx.Rect(pt.x, pt.y, 5,5))
            #print pt
            #self.Refresh(False)
        self.pos_ch(None)

    def OnMarginClick(self, evt):
        # fold and unfold as needed
        if evt.GetMargin() == 2:
            lineClicked = self.LineFromPosition(evt.GetPosition())
            if self.GetFoldLevel(lineClicked) & stc.STC_FOLDLEVELHEADERFLAG:
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
            if self.GetFoldLevel(lineNum) & stc.STC_FOLDLEVELHEADERFLAG:
                expanding = not self.GetFoldExpanded(lineNum)
                break;

        lineNum = 0
        while lineNum < lineCount:
            level = self.GetFoldLevel(lineNum)
            if level & stc.STC_FOLDLEVELHEADERFLAG and \
               (level & stc.STC_FOLDLEVELNUMBERMASK) == stc.STC_FOLDLEVELBASE:

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

            if level & stc.STC_FOLDLEVELHEADERFLAG:
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
        ## print repr(self.GetSelectedText())
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
        inde = incr*self.GetIndent()
        tabw = self.GetTabWidth()
        absi = abs(inde)
        utab = self.GetUseTabs()

        col = self.GetColumn(self.GetCurrentPos())
        lines = self.lines

        newlines = []
        for line in lines.selectedlines:
            right = line.lstrip()
            chari = len(line)-len(right)
            curi = line.count('\t', 0, chari)
            curi = max((curi*tabw + chari-curi) + inde, 0)
            curi -= incr*((absi+incr*(curi%absi))%absi)
            if utab:
                newlines.append((curi//tabw)*'\t' + (curi%tabw)*' ' + right)
            else:
                newlines.append(curi*' ' + right)


        sl, el = lines.selectedlinesi

        if el-1 > sl:
            lines.selectedlines = newlines
            lines.selectedlinesi = sl,el
        else:
            curp = lines.curlinep
            lines.targetlinesi = lines.selectedlinesi
            lines.targetlines = newlines
            if curp <= chari:
                #handles case where cursor was in the indent
                lines.curlinep = curi
            else:
                lines.curlinep = curp + curi - chari

    def OnIndent(self, e):
        self.Dent(e, 1)
    def OnDedent(self, e):
        self.Dent(e, -1)
    def OnInsertComment(self, e):
        dlg = wx.TextEntryDialog(self, '', 'Enter a comment.', '')
        resp = dlg.ShowModal()
        valu = dlg.GetValue()
        dlg.Destroy()
        if resp != wx.ID_OK:
            raise cancelled

        _lexer = self.GetLexer()
        k = len(valu)
        d = ''
        if _lexer == stc.STC_LEX_CPP:
            c = '/*'
            d = '*/'
        elif _lexer in (stc.STC_LEX_HTML, stc.STC_LEX_XML):
            c = '<!-- '
            d = ' -->'
        elif _lexer == stc.STC_LEX_LATEX:
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
                    if _lexer == stc.STC_LEX_CPP:
                        self.InsertText(firstChar, '// ')
                    elif self.GetLexer() in (stc.STC_LEX_HTML, stc.STC_LEX_XML):
                        self.InsertText(lastChar, ' -->')
                        self.InsertText(firstChar, '<!-- ')
                    elif _lexer == stc.STC_LEX_LATEX:
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
                    if _lexer == stc.STC_LEX_CPP:
                        if texta.startswith('// '):
                            lengtha = 3
                        elif texta.startswith('//'):
                            lengtha = 2
                    elif self.GetLexer() in (stc.STC_LEX_HTML, stc.STC_LEX_XML):
                        if texta.startswith('<!-- '):
                            lengtha = 5
                        elif texta.startswith('<!--'):
                            lengtha = 4

                        if lengtha:
                            if texta.endswith(' -->'):
                                rangeb = (lastChar-4, lastChar)
                            elif texta.endswith('-->'):
                                rangeb = (lastChar-3, lastChar)
                    elif _lexer == stc.STC_LEX_LATEX:
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

    def WrapFE(self, tail):
        lines = self.lines
        self.BeginUndoAction()
        try:
            lines.selectedlinesi = lines.selectedlinesi
            oldlines = ''.join(lines.selectedlines)
            min_indent = self._get_min_indent(oldlines)
            iw = self.GetIndent()
            newlines = self._StripPrefix(oldlines[:-1], min_indent+iw)
            prefix = self._StripPrefix('try:', min_indent)
            suffix = self._StripPrefix('%s:\n%s'%(tail, iw*' '), min_indent)
            lines.selectedlines = ['\n'.join([prefix, newlines, suffix, ''])]

            sp = self.PositionBefore(self.GetSelection()[1])
            self.SetSelection(sp,sp)
        finally:
            self.EndUndoAction()

    def WrapFinally(self, e):
        self.WrapFE('finally')

    def WrapExcept(self, e):
        self.WrapFE('except')

    def WrapExceptFinally(self, e):
        lines = self.lines
        startline = lines.selectedlinesi[0]
        self.BeginUndoAction()
        try:
            self.WrapFE('except')
            endline = lines.selectedlinesi[1]
            lines.selectedlinesi = startline, endline
            self.WrapFE('finally')
        finally:
            self.EndUndoAction()

    def convertLeadingTabsToSpaces(self, e):
        lines = self.lines
        a,b = self.GetSelection()
        z = x,y = map(self.LineFromPosition, (a,b))
        sl = lines.selectedlinesi

        if a==b:
            x = 0
            y = len(lines)

        msg = ('''\
        Each leading tab in line(s) %i-%i should
        be replaced by how many spaces?'''%(x+1, y+(x==y))).replace('        ', '')

        count = self.root.getInt("How many spaces per tab?",
                                 msg, self.GetTabWidth())

        repl = count*' '
        self.BeginUndoAction()
        try:
            for l in xrange(x,y+(x==y)):
                line = lines[l]
                sline = line.lstrip('\t')
                if line != sline:
                    lines[l] = (len(line)-len(sline))*repl + sline
        finally:
            self.EndUndoAction()

        if a!=b:
            lines.selectedlinesi = z

    def convertLeadingSpacesToTabs(self, e):
        lines = self.lines
        a,b = self.GetSelection()
        z = x,y = map(self.LineFromPosition, (a,b))
        sl = lines.selectedlinesi

        if x == y:
            x = 0
            y = len(lines)

        msg = ('''\
        How many leading spaces per tab in line(s) %i-%i?'''%(x+1, y)).replace('        ', '')
        default = str()

        count = self.root.getInt("How many spaces per tab?",
                                 msg, self.GetIndent())

        self.BeginUndoAction()
        try:
            for l in xrange(x,y+(x==y)):
                line = lines[l]
                sline = line.lstrip(' ')
                if line != sline:
                    lead = len(line)-len(sline)
                    lead //= count
                    if lead:
                        lines[l] = lead*'\t' + line[lead*count:]
        finally:
            self.EndUndoAction()

        if a!=b:
            lines.selectedlinesi = z


    def _get_min_indent(self, text, ignoreempty=0):
        lines = []
        for line in text.split('\n'):
            if ignoreempty and line.strip('\t\r '):
                lines.append(line.rstrip('\r'))
            elif not ignoreempty:
                lines.append(line.rstrip('\r'))

        lineind = []
        tw = self.GetTabWidth()-1
        for i in lines:
            leading = len(i) - len(i.lstrip())
            leading += i.count('\t', 0, leading)*tw
            lineind.append(leading)

        return lineind and min(lineind) or 0

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
                for i in parsers.no_ends:
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
            candidates = set(['return', 'pass', 'break', 'continue'])
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
                ls = line.split()
                ls[0:1] = ls[0].split('#')
                ls[0:1] = ls[0].split(';')
                if ls[0] in candidates:
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
        self.StartStyling(start, stc.STC_INDIC2_MASK)
        self.SetStyling(len(text), stc.STC_INDIC2_MASK)
        self.IndicatorSetStyle(stc.STC_INDIC2_MASK, stc.STC_INDIC_BOX)
        self.IndicatorSetForeground(stc.STC_INDIC2_MASK, wx.RED)

    def _is_method(self, lineno, line, col):
        if col < 1 or line[col-1] != '.':
            return False
        
        ftype = self._filetype()

        if USE_NEW and ftype == 'python':
            cur_scope = self.get_scope(lineno, col)
            # I don't like this, but we've already got a pretty solid scope,
            # so we'll just see if there's a self/class argument to validate
            # our pulling of the functions/methods.
            return bool(re.search('\W(self|klass|cls|class_|_class)\W', cur_scope.defn))
        
        if ftype == 'cpp':
            #really could be ANYTHING. or ANYTHING->
            #but not ANYTHING.ANYTHING(.|->) or ANYTHING->ANYTHING(.|->)
            if line[col-1:col] == '.' or line[col-2:col] == '->':
                col -= 1+line[col-1] == '>'
                x = get_last_word(line[:col])
                if x and line[col-len(x)-1:col-len(x)] not in ('.', '>'):
                    return True

        return False

    def get_scope(self, curline, curcol):
        sh = self.hierarchy
        cf = bisect.bisect_right(sh, parsers.line_info(curline))
        cf = max(min(cf, len(sh))-1, 0)
        try:
            cur_scope = sh[cf]
        except:
            print cf, len(sh)
            raise
        
        line = self.lines[curline]
        ci = min(len(line) - len(line.lstrip()), curcol)
        indent = len(line[:ci].replace('\t', '        '))

        while 1:
            if cur_scope.short.startswith('--') and cur_scope.short.endswith('--'):
                cf = sh.index(cur_scope) - 1
                cur_scope = sh[cf]
            elif cur_scope.lex_parent and (indent <= cur_scope.indent or curline >= (cur_scope.lineno + cur_scope.olines)):
                cur_scope = cur_scope.lex_parent
            else:
                ## print "name is ok", cur_scope.short
                ## print "has parent", bool(cur_scope.lex_parent)
                ## print "indent", indent, cur_scope.indent
                ## print "curline", curline, cur_scope.lineno + cur_scope.olines
                break
        return cur_scope

    def _name_listing(self, curline, curcol, prefix=''):
        cur_scope = self.get_scope(curline, curcol)
        available = set()
        while cur_scope:
            ## print "using scope for the name listing", cur_scope.long, cur_scope.locals
            available.update(name for name in cur_scope.locals if isinstance(name, basestring) and name.startswith(prefix))
            cur_scope = cur_scope.search_list
        return sorted(available)

    def _method_listing(self, curline, curcol, prefix=''):
        lines = self.lines
        ftype = self._filetype()
        _curline = curline
        
        if USE_NEW:
            # I <3 the new parser framework.
            # We already know that this is a method call, so we just chase up
            # the lexical parents until we find a class :)
            orig_scope = cur_scope = self.get_scope(curline, curcol)
            while cur_scope and not cur_scope.defn.startswith('class '):
                cur_scope = cur_scope.lex_parent
            if not cur_scope:
                # We checked all of the lexical parents and didn't find
                # anything.  Screw it, we'll stick with the original scope.
                cur_scope = orig_scope
            ## print "using scope for the method listing", cur_scope.long
            return sorted((name for name in cur_scope.locals if isinstance(name, basestring) and name.startswith(prefix)))
        
        #I seriously need a static lexer for Python, Pyrex, C, C++, etc.
        #It would make discovering the type of an object much easier, and we
        #wouldn't need to do the inaccurate 'pseudo-parsing' we are doing now.

        if ftype == 'python':
            #find a line starting with def, then with class
            info = self.fetch_methods_cache
            if curline == info[0]:
                if time.time()-info[1] < 60:
                    mll = min(curcol-1, len(info[2]))
                    if lines[curline][:mll] == info[2][:mll]:
                        info[1] = time.time()
                        return info[3]
                self.fetch_methods_cache = [-1, 0, '', []]

            indent = self.GetLineIndentation(curline)
            for tofind in ('def', 'class'):
                for i in xrange(curline-1, -1, -1):
                    l = lines[i]
                    if (l.split() or ('',))[0] == tofind:
                        ind = self.GetLineIndentation(i)
                        if ind < indent:
                            ## print "found", tofind
                            curline = i
                            indent = ind
                            break
                else:
                    ## print "didn't find", tofind
                    return

            #get the class name...
            cn = l.lstrip()[6:].lstrip()
            cn = cn.split('(')[0].split(':')[0]
            ## print "class name is:", cn

        elif ftype == 'cpp':
            return
            #not done yet, if it will ever be

            line = lines[curline]
            object_name = get_last_word(line[:curcol-1-(line[curcol-1]=='>')])
            if object_name == 'this':
                #implicit argument, check the class of this method, and/or
                #check for "type name" pairs farther up
                pass

            #we scan up to determine what type it is
            for i in xrange(curline-1, -1, -1):
                l = lines[i].split()
                if len(l) == 2 and l[1].rstrip(';') == object_name:
                    cn = l[1]
                    break
            else:
                return

            #now that we know the type, we get the methods...

        else:
            return

        l = self._subnode_listing(cn)
        self.fetch_methods_cache = [_curline, time.time(), lines[_curline], l]

        if prefix:
            return [i for i in l if i.startswith(prefix)]
        return l

    def _subnode_listing(self, cn):
        names = []
        for name, h in parsers.preorder(self.hierarchy):
            ## print 'name:', name
            if name == cn:
                for i in h[3]:
                    ## print i[1][2]
                    names.append(i[1][2])

        ## print "valid names: %r"%cn, names
        names.sort()
        return names

    def _find_locals(self, lineno):
        lines = self.lineabstraction
        s = set()
        for l in xrange(lineno-1, -1, -1):
            line = lines[l].lstrip()
            if lls.startswith('def '):
                # we can pull the argument names from the signature!
                break
            elif lls.startswith('class '):
                break
            
            # assignments...
            # ... = ...
            # for ... in ...
            # with ... as ...
            
            stuff = ''
            if lls.startswith('for '):
                end = ((lls.find(' in ') + 1) or (len(lls)+1)) - 1
                stuff = lls[4:end]
            elif lls.startswith('with '):
                if ' as ' not in lls:
                    continue
                stuff = lls[lls.find(' as '):]
            elif '=' in lls:
                # Look for regular assignments, we won't try too hard here.
                pass
                
            if stuff:
                s.update(stuff.replace(',', ' ').replace('(', ' ').replace(')', ' ').split())

    def indicate_text(self, start, len, ind):
        if not ind:
            #unstyle!
            style = self.GetEndStyled()
            self.StartStyling(start, stc.STC_INDIC2_MASK)
            self.SetStyling(len, 0)
            self.StartStyling(style, stc.STC_INDIC2_MASK^0xff)

        else:
            indic = SHELL_NUM_TO_INDIC[SHELL_OUTPUT]
            if indic != None:
                style = self.GetEndStyled()

                self.StartStyling(start, stc.STC_INDIC2_MASK)
                self.SetStyling(len, stc.STC_INDIC2_MASK)
                self.IndicatorSetStyle(2, indic)
                self.IndicatorSetForeground(2, SHELL_COLOR)

                self.StartStyling(style, stc.STC_INDIC2_MASK^0xff)

    def _gotcharacter(self, e=None):
        if HOW_OFTEN1 == -1:
            return

        if self.lexer in ('text', 'tex') and isinstance(self, PythonSTC) and self.GetTextLength() < 200000:
            ## print "spellchecking", self.lexer
            self._spellcheck()
            return

        if self.lexer != 'python' or self.filename.split('.')[-1] in ('spt', 'tmpl'):
            # don't check syntax for non-python files
            return

        #check syntax if we are visible
        content = self.getcmd(0).rstrip().replace('\r\n', '\n').replace('\r', '\n') + '\n'
        if not content and not self.has_bad:
            return

        m1 = md5.new(_to_str(content)).digest()
        if m1 == self.m1:
            return
        self.m1 = m1

        if isinstance(self, PythonSTC):
            fcn = lambda dt: int(max(dt, 1)*_MULT[HOW_OFTEN1]*1000)
        else:
            fcn = lambda dt: int(max(dt, .02)*5*1000)

        try:
            t = time.time()
            ## print "checking syntax!"
            parsers.parser.suite(content)
        except SyntaxError, e:
            ## print "found error!", vars(e)
            #highlight the error
            line = e.lineno - 1
            if not isinstance(self, PythonSTC):
                if self.has_bad:
                    #we have an interpreter, need to un-highlight extra stuff.
                    self.indicate_text(self.promptPosEnd, self.GetTextLength()-self.promptPosEnd, 0)

                #handle highlighting the proper line
                line += self.LineFromPosition(self.promptPosEnd)
            elif self.has_bad:
                self.indicate_text(0, self.GetTextLength(), 0)

            ls = self.PositionFromLine(line)
            skip = 0
            if not isinstance(self, PythonSTC):
                skip = 4
                ls += skip

            length = self.LineLength(line)-skip
            self.indicate_text(ls, max(length,0), 1)
            self.has_bad = 1
        else:
            ## print "no error found!"
            if self.has_bad:
                #clear indicators
                if isinstance(self, PythonSTC):
                    startpos = 0
                else:
                    startpos = self.promptPosEnd
                endpos = self.GetTextLength()
                self.indicate_text(startpos, endpos-startpos, 0)
                self.has_bad = 0
        self.lastparse = fcn(time.time()-t)

    def _spellcheck(self):
        spellcheck.SCI.load_d(1)
        if not spellcheck.dictionary:
            ## print "delaying spellcheck"
            self.root.t.Start(500, oneShot=True)
            return

        if isinstance(self, PythonSTC):
            fcn = lambda dt: int(max(dt, 1)*_MULT[HOW_OFTEN1]*1000)
        else:
            fcn = lambda dt: int(max(dt, .02)*5*1000)

        t = time.time()
        m1 = md5.new(_to_str(self.GetText())).digest()
        if m1 == self.m1:
            return
        self.m1 = m1
        ## print "actually spellchecking", self.lexer
        dcts = {}
        d = self.root.config["DICTIONARIES"]
        for i in xrange(spellcheck.SCI.dictionaries.GetCount()):
            if spellcheck.SCI.dictionaries.IsChecked(i):
                _ = d[spellcheck.SCI.dictionaries.GetString(i)]
                dcts.update(_)
                ## print "dictionary", _.keys()

        ## _dcts = {}
        ## for i in dcts:
            ## if type(i) is str:
                ## i = i.decode('latin-1')
            ## _dcts[i] = None

        ## dcts = _dcts.keys()
        ## dcts.sort()
        ## print 80*'*'
        ## print '\n'.join(dcts)
        ## print 80*'*'

        errors = spellcheck.SCI.find_errors(self, (spellcheck.dictionary, dcts))
        self.indicate_text(0, self.GetTextLength(), 0)
        for start, end in errors:
            self.indicate_text(start, end-start, 1)
        self.lastparse = fcn(time.time()-t)

    def _gotcharacter2(self, e=None):
        if HOW_OFTEN2 == -1:
            return

        self.automatic = 1
        #start a "refresh" if we are visible
        self.root.OnDocumentChange(self, 1)

    def getcmd(self, ue=1):
        if self.GetTextLength() < 200000:
            return self.GetText(ue)
        return ''

    def GotoLineS(self, line):
        line -= 1
        if line < self.GetLineCount():
            linepos = self.GetLineEndPosition(line)
            self.EnsureVisible(line)
            self.SetSelection(linepos-len(self.GetLine(line))+len(self.format), linepos)
            self.ScrollToColumn(0)

    def _invalidate_cache(self):
        self.cache = None
        self.m2 = None
        self.gotcharacter()

class View(PythonSTC):
    def __init__(self, *args):
        PythonSTC.__init__(self, *args)
        ## self.CmdKeyClearAll()

        # Clear keys that could modify the document.
        # This is a hack to get around the fact that
        # .SetReadOnly() works on a per-document basis,
        # not per-view as we need.
        self.CmdKeyClear(ord('T'), stc.STC_SCMOD_CTRL)
        self.CmdKeyClear(ord('T'), stc.STC_SCMOD_CTRL|stc.STC_SCMOD_SHIFT)
        self.CmdKeyClear(ord('L'), stc.STC_SCMOD_CTRL)
        self.CmdKeyClear(ord('L'), stc.STC_SCMOD_CTRL|stc.STC_SCMOD_SHIFT)
        self.CmdKeyClear(ord('D'), stc.STC_SCMOD_CTRL)
        self.CmdKeyClear(ord('U'), stc.STC_SCMOD_CTRL)
        self.CmdKeyClear(ord('U'), stc.STC_SCMOD_CTRL|stc.STC_SCMOD_SHIFT)
        self.CmdKeyClear(wx.WXK_TAB, stc.STC_SCMOD_SHIFT)
        self.CmdKeyClear(wx.WXK_TAB, 0)
        self.CmdKeyClear(wx.WXK_RETURN, stc.STC_SCMOD_SHIFT)
        self.CmdKeyClear(wx.WXK_RETURN, 0)
        self.CmdKeyClear(wx.WXK_DELETE, 0)
        self.CmdKeyClear(wx.WXK_DELETE, stc.STC_SCMOD_SHIFT)
        self.CmdKeyClear(wx.WXK_DELETE, stc.STC_SCMOD_CTRL)
        self.CmdKeyClear(wx.WXK_DELETE, stc.STC_SCMOD_CTRL|stc.STC_SCMOD_SHIFT)
        self.CmdKeyClear(wx.WXK_INSERT, 0)
        self.CmdKeyClear(wx.WXK_INSERT, stc.STC_SCMOD_SHIFT)
        self.CmdKeyClear(wx.WXK_BACK, 0)
        self.CmdKeyClear(wx.WXK_BACK, stc.STC_SCMOD_SHIFT)
        self.CmdKeyClear(wx.WXK_BACK, stc.STC_SCMOD_CTRL)
        self.CmdKeyClear(wx.WXK_BACK, stc.STC_SCMOD_ALT)
        self.CmdKeyClear(wx.WXK_BACK, stc.STC_SCMOD_CTRL|stc.STC_SCMOD_SHIFT)

        #add copying!
        self.CmdKeyAssign(ord('C'), stc.STC_SCMOD_CTRL, stc.STC_CMD_COPY)

        #remove the popup menu
        self.UsePopUp(0)

        self.Bind(wx.EVT_CHAR, self.OnChar)
    def OnChar(self, evt):
        #should prevent non-hotkey modification
        return

class FileDropTarget(wx.FileDropTarget):
    def __init__(self, root):
        wx.FileDropTarget.__init__(self)
        self.root = root
    def OnDropFiles(self, x, y, filenames):
        self.root.OnDrop(filenames)

class TextDropTarget(wx.TextDropTarget):
    def __init__(self, parent):
        wx.TextDropTarget.__init__(self)
        self.parent = parent

    def OnDropText(self, x, y, text):
        self.parent.OnDropText(text)
        #This is so that you can keep your document unchanged while adding
        #code snippets.
        return False

#DropTargetFT basis thanks to Anthony Wiese
class DropTargetFT(wx.PyDropTarget):
    def __init__(self, window):
        wx.PyDropTarget.__init__(self)
        self.window = window
        self.initObjects()

    def initObjects(self):
        self.data = wx.DataObjectComposite()
        self.textDataObject = wx.TextDataObject()
        self.fileDataObject = wx.FileDataObject()
        self.data.Add(self.textDataObject, True)
        self.data.Add(self.fileDataObject, False)
        self.SetDataObject(self.data)

    def OnEnter(self, x, y, dragResult):
        return dragResult

    def OnDrop(self, x, y):
        return True

    def OnDragOver(self, x, y, dragResult):
        return dragResult

    def OnData(self, x, y, dragResult):
        if self.GetData():
            files = self.fileDataObject.GetFilenames()
            text = self.textDataObject.GetText()

            if len(files) > 0:
                self.window.OnDrop(files)
            elif(len(text) > 0):
                if SetClipboardText(text):
                    try:
                        win = self.window.getNumWin()[1]
                    except cancelled:
                        self.window.newTab('', '', 1)
                        wx.CallAfter(self.window.OnPaste, None)
                    else:
                        p = win.PositionFromPointClose(x,y)
                        win.SetSelection(p,p)
                        win.Paste()
            else:
                self.window.SetStatusText("can't read this dropped data")
        self.initObjects()

class SplitterWindow(wx.SplitterWindow):
    if 1:
        swap = 0
        which = None, None, None, None, None
        posn = None

    def __init__(self, *args, **kwargs):
        wx.SplitterWindow.__init__(self, *args, **kwargs)
        self.SetMinimumPaneSize(5)

    def SplitVertically(self, win1, win2, sashPosition=0, swap=0):
        self.swap = swap
        self.which = self.SplitVertically, win1, win2, sashPosition, swap
        if swap:
            win1, win2, sashPosition = win2, win1, -sashPosition
        wx.SplitterWindow.SplitVertically(self, win1, win2, sashPosition)
        self.SetSashGravity(1.0 - bool(swap))

    def SplitHorizontally(self, win1, win2, sashPosition=0, swap=0):
        self.swap = swap
        self.which = self.SplitHorizontally, win1, win2, sashPosition, swap
        if swap:
            win1, win2, sashPosition = win2, win1, -sashPosition
        wx.SplitterWindow.SplitHorizontally(self, win1, win2, sashPosition)
        self.SetSashGravity(1.0 - bool(swap))

    def swapit(self):
        self.Unsplit()
        f,w1,w2,sp,sw = self.which
        f(w1, w2, -self.posn, not sw)

    def getSize(self):
        #size of the second window
        if self.IsSplit():
            x = self.GetSashPosition()
            if not self.swap:
                x = self.GetSize()[self.which[0] == self.SplitHorizontally] - x
            return x
        else:
            return self.posn

    def Unsplit(self, which=None, startup=0):
        if which is None:
            which = self.GetWindow2()
        if not startup:
            self.posn = self.getSize()
        else:
            self.posn = abs(self.which[-2])
        ## self.posn += self.GetSize()[self.which[0] == self.SplitHorizontally]
        wx.SplitterWindow.Unsplit(self, which)

    def Split(self):
        if self.which:
            f,w1,w2,sp,sw = self.which
            f(w1, w2, -self.posn, sw)

    def GetWindow1(self):
        if self.IsSplit() and self.swap:
            x = wx.SplitterWindow.GetWindow2(self)
        else:
            x = wx.SplitterWindow.GetWindow1(self)
        return x
    def GetWindow2(self):
        if self.IsSplit() and self.swap:
            x = wx.SplitterWindow.GetWindow1(self)
        else:
            x = wx.SplitterWindow.GetWindow2(self)
        return x
    def SetSashPosition(self, position, redraw = 1):
        if self.swap:
            position = -position
        return wx.SplitterWindow.SetSashPosition(self, position, redraw)

VS = wx.VERSION_STRING

def main():
    docs = [os.path.abspath(os.path.join(current_path, i))
            for i in sys.argv[1:]]
    if single_instance.send_documents(docs):
        return

    global IMGLIST1, IMGLIST2, IMGLIST3, root, app
    app = wx.App(0)
    IMGLIST1 = wx.ImageList(16, 16)
    IMGLIST2 = wx.ImageList(16, 16)
    IMGLIST3 = []
    for il in (IMGLIST1, IMGLIST2):
        for icf in ('icons/blank.ico', 'icons/py.ico'):
            icf = os.path.join(runpath, icf)
            img = wx.ImageFromBitmap(wx.Bitmap(icf))
            img.Rescale(16,16)
            bmp = wx.BitmapFromImage(img)
            IMGLIST3.append(bmp)
            il.AddIcon(wx.IconFromBitmap(bmp))
    IMGLIST3.pop()

    opn=0
    if len(sys.argv)>1 and ('--last' in sys.argv):
        opn=1
    filehistory.root = root = app.frame = MainWindow(None, -1, "PyPE", docs)
    root.updateWindowTitle()
    app.SetTopWindow(app.frame)
    app.frame.Show()
    app.frame.Hide() #to fix not showing problem on Windows
    app.frame.Show() #
    if opn:
        app.frame.OnOpenPrevDocs(None)
    app.frame.SendSizeEvent()
    app.MainLoop()

if __name__ == '__main__':
    main()
