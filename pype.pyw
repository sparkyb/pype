
'''
This software is licensed under the GPL (GNU General Public License) version 2
as it appears here: http://www.gnu.org/copyleft/gpl.html
It is also included with this archive as `gpl.txt <gpl.txt>`_.
'''


import sys
import imp

if __name__ == '__main__':
    sys.modules['notmain'] = sys.modules['__main__']
    sys.modules['__main__'] = imp.load_source('__main__', 'pype.py', open('pype.py')) 
