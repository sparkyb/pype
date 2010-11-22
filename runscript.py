#!/usr/bin/python

#I didn't want to write a command line parser...so I didn't.

if __name__ == '__main__':
    import sys, os

    #Because the windows version of Python doesn't include a path-searching
    #spawnv, they don't get one.  This is irksome, but hey, you can't have
    #everything on every patform.
    #It also probably doesn't exist on pre OSX macs, but I can't be sure.

    if sys.argv[1] != '*':
        os.chdir(sys.argv[1])
    if sys.platform=='win32':
        os.system("start %s"%' '.join(sys.argv[2:]))
    else:
        os.spawnvp(os.P_NOWAIT, sys.argv[2], sys.argv[2:])

