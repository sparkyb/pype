
import sched
import time
import traceback
import Queue
import sys
import os

USE_WX_TIMER = 1

class sobject(object):
    __slots__ = 'sched', 'function', 'args', 'kwargs', 'delay', 'priority', 'runcount', 'item'
    # an object-oriented version of the scheduler interface, with auto multi-run
    def __init__(self, sched, runcount, delay, priority, function, *args, **kwargs):
        ## print "scheduling item with delay", delay, function
        self.sched = sched
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.runcount = runcount
        self.delay = delay
        self.priority = priority
        self.item = None
        if runcount is None or runcount > 0:
            self._sched(delay, priority, self.run)
                
    def _sched(self, delay, priority, run):
        self.item = GlobalSchedule.enter(delay, priority, run, ())
        gsq = GlobalSchedule._queue[:1]
        if USE_WX_TIMER and gsq and gsq[0] is self.item:
            dt = max(int((gsq[0].time - time.time())*1000), 10)
            TIMER_INSTANCE.Stop()
            TIMER_INSTANCE.Start(milliseconds=dt, oneShot=True)
            ## print "starting timer!"

    def cancel(self):
        if self.runcount is None or self.runcount > 0:
            if self.item:
                self.sched.cancel(self.item)
            self.runcount = 0

    def run(self):
        if self.runcount is None or self.runcount > 0:
            try:
                return self.function(*self.args, **self.kwargs)
            finally:
                if self.runcount is not None:
                    self.runcount -= 1
                if self.runcount is None or self.runcount > 0:
                    self._sched(self.delay, self.priority, self.run)

    def reenter(self, delay, priority, runcount=1):
        self.cancel()
        self.runcount = runcount
        self.item = self.sched.enter(delay, self.priority, self.run, ())

    #the wx-like interface
    def Start(self, msdelay=-1, oneShot=False):
        if msdelay == -1:
            msdelay = 1000*self.delay
        if not oneShot:
            count = None
        else:
            count = 1
        ## print ''.join(traceback.format_stack()[-4:]).rstrip()
        ## print "starting", msdelay/1000.0, self.function
        self.reenter(msdelay/1000.0, 0, count)

    Stop = cancel

    def IsRunning(self):
        return self.runcount is None or self.runcount > 0

GlobalSchedule = sched.scheduler(time.time, (lambda arg:None), True)
GlobalQ = Queue.Queue()
CyclesPerSecond = 40
QUIT = 0

def PFutureCall(msdelay, priority, function, *args, **kwargs):
    return sobject(GlobalSchedule, 1, msdelay/1000.0, priority, function, *args, **kwargs)

def FutureCall(msdelay, function, *args, **kwargs):
    return PFutureCall(msdelay, 0, function, *args, **kwargs)

def ShutdownScheduler():
    global QUIT
    QUIT = 1
    def runme(*args, **kwargs):
        os._exit(0)
    PFutureCall(-1000000, -1000000, runme)

def Timer(function, *args, **kwargs):
    # We'll "schedule" it to run zero times after 1 second
    return sobject(GlobalSchedule, 0, 1, 0, function, *args, **kwargs)

def actually_run():
    global cancelled
    try:
        cancelled
    except NameError:
        cancelled = sys.modules['__main__'].cancelled
    for i in GlobalQ.get():
        if QUIT:
            break
        _1, _2, fcn, arg = i
        try:
            ## print "running function...", fcn
            fcn(*arg)
        except cancelled:
            pass
        except (SystemExit, AssertionError, KeyboardInterrupt):
            break
        except:
            import traceback
            traceback.print_exc()

def RunScheduledEvents():
    x = GlobalSchedule.getqueue(time.time(), copy=0)
    if QUIT:
        return 1
    import wx
    GlobalQ.put(x)
    if QUIT:
        return 1
    try:
        wx.CallAfter(actually_run)
    except AssertionError:
        return 1
    return 0

def _schedulethread(ok=0):
    while ok and not QUIT:
        time.sleep(1.0/max(CyclesPerSecond, 1))
        if QUIT:
            return
        if RunScheduledEvents():
            return
    if QUIT:
        return
    import threading
    x = threading.Thread(target=_schedulethread, args=(1,))
    x.setDaemon(1)
    x.start()

import sys
sys.modules['__builtin__'].FutureCall = FutureCall
sys.modules['__builtin__'].PFutureCall = FutureCall
sys.modules['__builtin__'].Timer = Timer
sys.modules['__builtin__'].ShutdownScheduler = ShutdownScheduler

if USE_WX_TIMER:
    def OnTimerDone(evt=None):
        ## print "going to run scheduled events..."
        TIMER_INSTANCE.Stop()
        if RunScheduledEvents():
            ## print "need to kill the scheduler..."
            return
        gsq = GlobalSchedule._queue[:1]
        dt = 1000
        if gsq:
            ## print "event:", gsq[0]
            dt = min(max(int((gsq[0].time - time.time())*1000), 10), 1000)
        TIMER_INSTANCE.Start(milliseconds=dt, oneShot=True)
        ## print "starting timer!"

    def _schedulethread(ok=0):
        global wx, WXAPP, TIMER_INSTANCE
        import wx
        WXAPP = wx.GetApp()
        TIMER_INSTANCE = wx.Timer(WXAPP, wx.NewId())
        WXAPP.Bind(wx.EVT_TIMER, OnTimerDone, TIMER_INSTANCE)
        TIMER_INSTANCE.Start(1, oneShot=True)
        ## print "starting timer!"
