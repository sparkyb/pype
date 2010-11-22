
import socket
import asyncore
import traceback
import sys

configuration = _pype

callback = None

port = 9999

def partition(string, sep):
    offset = string.find(sep)
    if offset == -1:
        return string, '', ''
    return string[:offset], sep, string[offset+len(sep):]

class PathReader(asyncore.dispatcher):
    def __init__(self, conn):
        asyncore.dispatcher.__init__(self, conn)
        self.incoming = ''
        ## self.handle_error = self.handle_close
    
    ## def handle_close(self):
        ## self.close()
    
    def handle_read(self):
        data = self.recv(4096)
        if not data:
            self.handle_close()
            return
        self.incoming += data
        
        fnames = []
        fname, sep, self.incoming = partition(self.incoming, '\n')
        while sep:
            if fname:
                fnames.append(fname)
            fname, sep, self.incoming = partition(self.incoming, '\n')
        self.incoming = fname
        if fnames:
            callback(fnames)

class Listener(asyncore.dispatcher):
    def __init__(self):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(('127.0.0.1', port))
        self.listen(5)

    def handle_accept(self):
        try:
            conn, addr = self.accept()
        except socket.error:
            return
        except TypeError:
            return
        PathReader(conn)

def send_documents(docs):
    if configuration.nosocket:
        return 0
    try:
        startup(0)
    except socket.error, why:
        if why[0] != 10048:
            traceback.print_exc()
            return 0
    else:
        shutdown(0)
        return 0
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', port))
        docs.append('')
        s.sendall('\n'.join(docs))
        s.close()
    except socket.error:
        return 0
    else:
        print "sent documents to already running PyPE at port %i"%(port,)
        return 1

def poll():
    asyncore.poll()

def startup(p=1):
    if p:
        print "Starting up document listener!"
    Listener()

def shutdown(p=1):
    if p:
        print "Shutting down document listener!"
    for i in asyncore.socket_map.values():
        i.close()
