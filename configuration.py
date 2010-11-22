#----------------------------- configuration.py ------------------------------
#----------------------- Settings for configuring PyPE -----------------------
import os
import sys
#from wxPython.wx import *
from wxPython.stc import wxSTC_EOL_CRLF, wxSTC_EOL_LF, wxSTC_EOL_CR
from parsers import *

#--------- If I'm wrong on any of the line endings, please tell me. ----------
crlf = ["nt", "dos", "ce", "os2"]
lf = ["posix", "riscos", "java"]
cr = ["mac"]
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

del a;del b;del se

stylefile = os.path.join(runpath, 'stc-styles.rc.cfg')

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

#if the following is set to 1, then drag and drop TEXT support will not work
#in the editor control, but will enable drag and drop FILE support in the
#editor control.  Enabled by default.  Why?  Because I drag files, I cut and
#paste text.
dnd_file = 1

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
    if not os.path.exists(homedir):
        os.mkdir(homedir)
except:
    print "unable to create config directory", homedir
# End cmt-001 08/06/2003
