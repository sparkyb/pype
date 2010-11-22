
import sys
import imp

if __name__ == '__main__':
    sys.modules['notmain'] = sys.modules['__main__']
    sys.modules['__main__'] = imp.load_source('__main__', 'pype.py', open('pype.py')) 
