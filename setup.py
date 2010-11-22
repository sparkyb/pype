# setup.py
# to make a binary for windows from source...
# 1. download and install the py2exe utility from:
#      http://starship.python.net/crew/theller/py2exe/
# 2. run the following command:
#      python setup.py py2exe

# to make a source tarball or zip (depending on your platform) from source:
#   python setup.py sdist

# The build process for bdist_wininst produces an improper installer.
# It seems possible, if not likely, that bdist_rpm suffers the same problems.
# I have explicitly removed support for them unless someone sends in a fix
# for making them work.

"""A Python-oriented editor with support for multiple platforms

PyPE (Python Programmers Editor) was written in order to offer a lightweight
but powerful editor for those of you who think emacs is too much and Idle is
too little. Syntax highlighting is included out of the box, as is multiple
open documents via tabs.

See http://pype.sf.net/features.html for an almost complete listing of PyPE's
available features.
"""

import sys

if [i for i in sys.argv if 'wininst' in i or 'rpm' in i]:
    print '''
You seem to be attempting a bdist_wininst or bdist_rpm distribution creation.
According to my experience, running the results of PyPE + bdist_wininst will
muck up your Python installation (destroying readme.txt, etc.).  It seems
possible, if not likely, that the bdist_rpm variant suffers from the same kind
of problems.  You are likely better off using the 'python setup.py sdist'
version, and packaging it up with some platform-specific tool.
'''
    sys.exit(1)

from distutils.core import setup
import __version__

if 'py2exe' in sys.argv:
    import pype
    try:
        import py2exe
    except:
        raise SystemExit("py2exe needs to be installed to create Windows binaries")
import glob
import os

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

setup(
    name=nam,
    version=__version__.VERSION_,
    author="Josiah Carlson",
    author_email="jcarlson@uci.edu",
    url="http://pype.sf.net/",
    license="GNU GPL v. 2",
    description=doclines[0],
    long_description='\n'.join(doclines[2:]),
    platforms=["any"],
    classifiers=[i.strip() for i in classifiers.split('\n') if i.strip()],
    
    windows=[{"script": "pype.py",
              "icon_resources": [(1, os.path.join("icons", "pype.ico"))]}],
    data_files=[('', glob.glob('*.txt')+\
                ['stc-styles.rc.cfg', 'readme.html', 'PKG-INFO', 'MANIFEST.in']),
                ('icons', glob.glob(os.path.join('icons', '*.*'))),
                #('macros', glob.glob(os.path.join('macros', '*.py'))),
                (samples, glob_(samples, ('*.txt', '*.py')))],
    options = {"py2exe": {"packages": ["encodings"],
                          "compressed": 1}},
)
