#----------------------------- configuration.py ------------------------------
#----------------------- Settings for configuring PPE ------------------------
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

runpath = os.path.split(os.path.normcase(os.path.normpath(sys.argv[0])))[0]

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
paths = {}
display2code={}
displayorder=[]
shellcommands = []
try:
    from pathmarks import *
except:
    pass

