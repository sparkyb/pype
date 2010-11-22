
'''
This software is licensed under the GPL (GNU General Public License) version 2
as it appears here: http://www.gnu.org/copyleft/gpl.html
It is also included with this archive as `gpl.txt <gpl.txt>`_.
'''

# setup.py
# to make a binary for windows from source...
# 1. download and install the py2exe utility from:
#      http://starship.python.net/crew/theller/py2exe/
# 2. run the following command:
#      python setup.py py2exe

# to make a source tarball or zip from source, compress it by hand

# The build process for bdist_wininst produces an improper installer.
# It seems possible, if not likely, that bdist_rpm suffers the same problems.
# I have explicitly removed support for them unless someone sends in a fix
# for making them work.

"""\
A Python-oriented editor with support for multiple platforms

PyPE (Python Programmers Editor) was written in order to offer a lightweight
but powerful editor for those of you who think emacs is too much and Idle is
too little. Syntax highlighting is included out of the box, as is multiple
open documents via tabs.

See http://pype.sf.net/features.html for an almost complete listing of PyPE's
available features.
"""

import sys

badcommands = 'wininst rpm dist install'.split()

if [i for j in badcommands for i in sys.argv if j in i]:
    print '''
You seem to be attempting some sort of non-py2exe distribution creation or
install attempt, according to the argument(s): %r

Unzip the version of PyPE you are currently using into some path that you
would like to run PyPE from, then run it from there.
'''%([i for j in badcommands for i in sys.argv if j in i],)
    sys.exit(1)

import __version__
if 'py2exe' in sys.argv:
    import pype
    try:
        import py2exe
    except:
        raise SystemExit("py2exe needs to be installed to create Windows binaries")
from distutils.core import setup
import glob
import os
import time

nam = "PyPE"
if sys.platform == 'win32' and 'py2exe' in sys.argv:
    nam += "-win32"
    if pype.VS[-1] == 'u':
        nam += '-unicode'

def glob_(path, extns):
    x = []
    for i in extns:
        x.extend(glob.glob(os.path.join(path, i)))
    return x
    
samples = os.path.join('macros', 'samples')

classifiers = '''
Development Status :: 5 - Production/Stable
Environment :: Other Environment
Intended Audience :: Developers
Intended Audience :: End Users/Desktop
License :: OSI Approved :: GNU General Public License (GPL)
Natural Language :: English
Operating System :: OS Independent
Programming Language :: Python
Topic :: Software Development
Topic :: Text Editors
'''

doclines = [i.strip() for i in __doc__.split("\n")]

# The manifest will be inserted as a resource into the executable.  This
# gives the controls the Windows XP appearance if run on XP.
manifest_template = '''
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
<assemblyIdentity
    version="5.0.0.0"
    processorArchitecture="x86"
    name="%(name)s"
    type="win32"
/>
<description>%(name)s, %(description)s</description>
<dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.Windows.Common-Controls"
            version="6.0.0.0"
            processorArchitecture="X86"
            publicKeyToken="6595b64144ccf1df"
            language="*"
        />
    </dependentAssembly>
</dependency>
</assembly>
'''
info = dict(
    name=nam,
    version=__version__.VERSION_,
    author="Josiah Carlson",
    author_email="jcarlson@uci.edu",
    copyright="\xa9 2003-%i Josiah Carlson"%(time.gmtime()[0]),
    url="http://pype.sf.net/",
    license="GNU GPL v. 2",
    description=doclines[0],
    long_description='\n'.join(doclines[2:]),
    platforms=["any"],
    classifiers=[i.strip() for i in classifiers.split('\n') if i.strip()],

)

class Target:
    def __init__(self, **kw):
        self.__dict__.update(info)
        self.__dict__.update(kw)

PyPE = Target(
    # icon for executable:
    icon_resources = [(1, os.path.join("icons", "pype.ico"))],
    other_resources = [(24, 1, manifest_template%info)],   
    #script to build:
    script = "pype.py",
)

data_files=[('', glob.glob('*.txt')+\
            ['stc-styles.rc.cfg', 'readme.html', 'PKG-INFO', 'MANIFEST.in']),
            ('icons', glob.glob(os.path.join('icons', '*.*'))),
            #('macros', glob.glob(os.path.join('macros', '*.py'))),
            (samples, glob_(samples, ('*.txt', '*.py')))]

import wx
if wx.VERSION >= (2, 7):
    data_files[0][1].append('gdiplus.dll')

setup(
    windows=[PyPE],
    data_files=data_files,
    options={"py2exe": {"packages": ["encodings"],
                        "compressed": 1}},
    **info
)
