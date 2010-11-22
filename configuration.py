#----------------------------- configuration.py ------------------------------
#----------------------- Settings for configuring PyPE -----------------------

collapse_style = 0

#if the following is set to 1, then drag and drop TEXT support will not work
#in the editor control, but will enable drag and drop FILE support in the
#editor control.  Enabled by default.  Why?  Because I drag files, I cut and
#paste text.
dnd_file = 1

#CTRL-T swaps two lines.  Setting the below to 1 disables this hotkey.
REM_SWAP = 1

import os
import sys
#from wxPython.wx import *
from wxPython.stc import wxSTC_EOL_CRLF, wxSTC_EOL_LF, wxSTC_EOL_CR
from parsers import *

fmt_mode = {"\r\n":wxSTC_EOL_CRLF,
              "\n":wxSTC_EOL_LF,
              "\r":wxSTC_EOL_CR}
fmt_Rmode = {}
for i,j in fmt_mode.items():
    fmt_Rmode[j] = i

eol = os.linesep
eolmode = fmt_mode[eol]

runpath = os.path.dirname(os.path.normpath(os.path.abspath(__file__)))

def fp(path):
    if sys.platform=='win32':
        if ' ' in path:
            return '"%s"'%path
        return path
    return path.replace(' ', '\\ ')

def fixpath(path):
    return os.path.normpath(fp(path))

se = fixpath(sys.executable)
spawnargs = [se]

if sys.executable[-8:].lower() == 'pype.exe':
    runme = se
else:
    b = fixpath(os.path.join(runpath, sys.argv[0]))
    runme = "%s %s"%(se,b)
    spawnargs.append(b)

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

a = os.listdir(homedir)
rem = []
for fil in a:
    index = fil.find('.tmp.')
    if index>=0:
        try: os.remove(os.path.join(homedir, fil))
        except: pass

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

def validate(dlg, orig):
    try:
        a = int(dlg.GetValue())
    except:
        a = 0
    if a < 1:
        return orig
    return a
