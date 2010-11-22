#----------------------------- configuration.py ------------------------------
#----------------------- Settings for configuring PyPE -----------------------
import os
import sys
#from wxPython.wx import *
from wxPython.stc import wxSTC_EOL_CRLF, wxSTC_EOL_LF, wxSTC_EOL_CR
from parsers import *

fmt_mode = {"\r\n":wxSTC_EOL_CRLF,
              "\n":wxSTC_EOL_LF,
              "\r":wxSTC_EOL_CR}
eol = os.linesep
eolmode = fmt_mode[eol]

runpath = os.path.dirname(os.path.normpath(os.path.abspath(__file__)))

se = sys.executable
a = se
b = sys.argv[0]
if ' ' in a:
    a = '"%s"'%a
if ' ' in b:
    b = '"%s"'%b
runme = "%s %s"%(a,b)

if se[-8:] == 'pype.exe':
    runme = a

spawnargs = [sys.executable]
if sys.executable[-8:] != 'pype.exe':
    spawnargs.append(sys.argv[0])

stylefile = os.path.join(runpath, 'stc-styles.rc.cfg')

def command_parser(command):
    args = []
    beg = 0
    cur = 0
    while cur < len(command):
        if command[cur:cur+2] == '\\ ':
            cur = cur + 2
        elif command[cur] == ' ':
            args.append(command[beg:cur])
            cur += 1
            beg = cur
        else:
            cur += 1
    if beg != cur:
        args.append(command[beg:cur])
    return args


#light vert line just before this column number
#that is after this many characters
col_line = 78

#width of the left margin in pixels (I like mine big)
margin_width = 40

#for those collapseable source blocks (they rock)
collapse = 1
collapse_style = 0

#most python users use this...Stay away from tabs, they reduce file size,
#but are a bitch when it comes to formatting.
indent = 4
use_tabs = 0
#if use_tabs enabled, the number of spaces per tab
spaces_per_tab = 8

#if the following is set to 1, then drag and drop TEXT support will not work
#in the editor control, but will enable drag and drop FILE support in the
#editor control.  Enabled by default.  Why?  Because I drag files, I cut and
#paste text.
dnd_file = 1

#CTRL-T swaps two lines.  Setting the below to 1 disables this hotkey.
REM_SWAP = 1

#the default STC behavior resulted in hitting 'home' would send you to the
#beginning of the entire line, rather than the displayed line
#setting the below to 0 will give the default STC behavior (like emacs).
#setting the below to 1 will give the behavior that most people are used to.
SWAP_HE_BEHAVIOR = 1

#for open/save dialogs
wildcard = "All python files (*.py *.pyw)|*.py;*.pyw;*.PY;*.PYW|"\
           "C/C++ files (*.c* *.h)|*.c*;*.h;*.C*;*.H|"\
           "HTML/XML files (*.htm* *.shtm* *.xml)|*.htm*;*.shtm*;*.xml;*.HTM*;*.SHTM*;*.XML|"\
           "All files (*.*)|*.*"

#for style mappings from extensions
extns = {'py' : 'python',
        'pyw' : 'python',
          'c' : 'cpp',
         'cc' : 'cpp',
        'cpp' : 'cpp',
        'c++' : 'cpp',
          'h' : 'cpp',
        'htm' : 'html',
       'html' : 'html',
       'shtm' : 'html',
      'shtml' : 'html',
        'xml' : 'xml',
        'txt' : 'text'}

#--------------- load pathmarks, snippets, and shell commands ----------------
#paths = {}
#display2code={}
#displayorder=[]
#shellcommands = []

# cmt-001 08/06/2003 - Create a pype configuration directory to store info
default_homedir = os.path.dirname(os.path.abspath(__file__))

try:
    #all user-based OSes
    thd = os.path.expanduser("~")
    if thd == "~": raise
    homedir = os.path.join(thd, ".pype")
except:
    try:
        #*nix fallback
        homedir = os.path.join(os.environ['HOME'], ".pype")
    except:
        try:
            #windows NT,2k,XP,etc. fallback
            homedir = os.path.join(os.environ['USERPROFILE'], ".pype")
        except:
            #What os are people using?
            homedir = os.path.join(default_homedir, ".pype")
try:
    # create the config directory if it
    # doesn't already exist
    def expandfull(var, rem=3):
        if not rem:
            return os.path.expandvars(var)
        a = os.path.expandvars(var)
        b = []
        d = [b.extend(i.split('\\')) for i in a.split('/')]
        c = []
        for i in b:
            if '%' in i:
                c.append(expandfull(i, rem-1))
            else:
                c.append(i)
        return '\\'.join(c)
    if eol == "\r\n" and '%' in homedir:
        homedir = expandfull(homedir)
    if not os.path.exists(homedir):
        os.mkdir(homedir)
except:
    #print "unable to create config directory", homedir
    homedir = default_homedir
# End cmt-001 08/06/2003

def get_paragraphs(text, l_sep):
    in_lines = text.split(l_sep)
    lines = []
    cur = []
    for line in in_lines:
        cur.append(line)
        if line:
            if line[-1] != ' ':
                cur.append(' ')
        else:
            if cur:
                lines.append(cur)
                cur = []
            lines.append([])
    if cur:
        lines.append(cur)
    return [''.join(i) for i in lines]

def wrap_paragraph(text, width):
    words = text.split(' ')
    lines = []
    cur = []
    l = 0
    for word in words:
        lw = len(word)
        if not lw:
            cur.append(word)
        elif (l + len(cur) + len(word)) <= width:
            cur.append(word)
            l += lw
        else:
            if cur[-1]:
                cur.append('')
            lines.append(cur)
            cur = [word]
            l = lw
    if cur:
        lines.append(cur)
    return '\n'.join([' '.join(i) for i in lines])

def wrap_lines(text, width, lend):
    paragraphs = get_paragraphs(text, lend)
    retr = lend.join([wrap_paragraph(i, width) for i in paragraphs])
    return retr
