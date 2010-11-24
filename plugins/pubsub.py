
'''
This software is licensed under the GPL (GNU General Public License) version 2
as it appears here: http://www.gnu.org/copyleft/gpl.html
It is also included with this archive as `gpl.txt <gpl.txt>`_.
'''

'''
This module implements the minimal API necessary to support publish/subscribe.
Why reinvent the wheel?  Because wx.lib.pubsub has gotten too heavy.
'''

from collections import defaultdict
import re
import traceback
import wx

class AttrDict(dict):
    def __getattr__(self, attr):
        return self[attr]
    def __setattr__(self, attr, value):
        self[attr] = value
    def __delattr__(self, attr):
        del self[attr]

_topics = defaultdict(list)

class Abort(Exception):
    '''raise me to abort the processing of a message'''

def _fix_topic(function):
    def fixed(topic, *args, **kwargs):
        topic = re.sub("\.+", '.', topic).strip('.')
        return function(topic, *args, **kwargs)
    return fixed

@_fix_topic
def subscribe(topic, function):
    '''
    Subscribe the function to the given topic.
    '''
    _topics[topic].append(function)

@_fix_topic
def unsubscribe(topic, function):
    '''
    Unsubscribe the function from the given topic.
    '''
    fcns = _topics.get(topic, [])
    try:
        indx = fcns.index(function)
    except IndexError:
        return
    del fcns[indx]

@_fix_topic
def publish_now(topic, kwargs):
    '''
    Deliver the message *right now* to all subscribers of the topic and
    ancestor topics.
    '''
    kwargs = AttrDict(kwargs)
    kwargs._topic = topic
    ct = ''
    delivered = 0
    try:
        for sub_topic in topic.split('.'):
            ct += ('.' if ct else '') + sub_topic
            kwargs._topic_delivered = ct
            calls = _topics.get(ct, ())
            ## print "trying to send to", ct, len(calls)
            for call in calls:
                delivered += 1
                # Everyone gets the same dictionary, figure that if they
                # mangle the data, it is expected.
                call(kwargs)
    except Abort:
        pass
    except:
        traceback.print_exc()
    return delivered

def publish(topic, **kwargs):
    '''
    Deliver the message in the next invocation of the event loop.
    '''
    wx.CallAfter(publish_now, topic, kwargs)
