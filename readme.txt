=================================================
Readme/Help for PyPE (Python Programmer's Editor)
=================================================

.. contents:: Table of Contents

-------------------------------
License and Contact information
-------------------------------
http://pype.sourceforge.net
http://come.to/josiah

PyPE is copyright 2003-2006 Josiah Carlson.
Contributions are copyright their respective authors.

This software is licensed under the GPL (GNU General Public License) as it
appears here: http://www.gnu.org/copyleft/gpl.html
It is also included with this archive as `gpl.txt <gpl.txt>`_.

The included STCStyleEditor.py, which is used to support styles, was released
under the wxWindows license and is copyright (c) 2001 - 2002 Riaan Booysen.
The copy included was also distributed with the wxPython Demos and Docs for
wxPython version 2.6 for Python 2.3, and may or may not have been modified by
the time you read this.  The wxWindows license and the LGPL license it
references are included with this software as `wxwindows.txt <wxwindows.txt>`_
and `lgpl.txt <lgpl.txt>`_.

The included stc-styles.rc.cfg was modified from the original version in order
to not cause exceptions during style changes, as well as adding other language
style definitions, and was originally distributed with wxPython version
2.4.1.2 for Python 2.2 .

If you do not also receive a copy of `gpl.txt <gpl.txt>`_,
`wxwindows.txt <wxwindows.txt>`_, and `lgpl.txt <lgpl.txt>`_ with your version
of this software, please inform me of the violation at either web page at the
top of this document.

------------
Requirements
------------

Either a machine running Python and wxPython, or a Windows machine that can
run the binaries should be sufficient.  Initial revisions of PyPE were
developed on a PII-400 with 384 megs of ram, but it should work on any machine
that can run the most recent wxPython revisions.  Some portions may be slow
(Document->Wrap Long Lines especially, which is a known issue with the
scintilla text editor control), but it should still be usable.

PyPE 2.x has only been tested on Python 2.3 and wxPython 2.6.3.0.  It should
work on later versions of Python and wxPython.  If you are having issues, file
a bug report on http://sourceforge.net/projects/pype .

------------
Installation
------------

If you have Python 2.3 or later as well as wxPython 2.6.1.0 or later, you can
extract PyPEX.Y.Z-src.zip anywhere and run it by double-clicking on pype.py or
pype.pyw .  If you want to be all official, you can use
'python setup.py install', but that is generally unnecessary.

If you don't have Python 2.3 wxPython 2.6.1.0 or later, and are running
Windows, you should (hopefully) be able to run the Windows binaries.  They are
provided for your convenience (so you don't have to install Python and
wxPython).

If it so happens that the Windows binaries don't work for you, and you have an
installation of Python and wxPython that fits the requirements, why don't you
run the source version?  The only difference is a pass through py2exe, and a
minor loading time speed increase.  Just because the Windows binaries exist,
doesn't mean that you /have/ to run them.


----
Help
----

Why doesn't the Windows install work?
=====================================
Depending on your platform, it may or may not work.  It works for me on
Windows 2k, XP and 98.  Most problems people have is that they mistakenly
extract library.zip, which they shouldn't do.



Why doesn't PyPE work on Linux?
===============================
There have been reports of PyPE segfaulting in certain Linux distributions
when opening a file.  This seems to be caused by icons in the file listing in
the 'Documents' tab on the right (or left) side of the editor (depending on
your preferences), or by icons in the notebook tabs along the top of the
editor.  If You can disable these icons by starting up PyPE, going to
Options->Use Icons, and making sure that it is unchecked.  You should restart
PyPE to make sure that the setting sticks.  PyPE will be uglier, but it should
work.



Using PyPE with ansi or unicode wxPython
========================================
If you start PyPE up with --ansi, it will require the ansi version of
wxPython, informing you if it cannot find it.  If you start PyPE up with
--unicode, it will require the unicode version of wxPython, informing you if
it cannot find it.  If you don't provide a command-line option, it will use
the default wxPython version on your platform.  --ansi and --unicode command
line options will be ignored in the Windows distributions, as well as any
other distributions of PyPE where ``hasattr(sys, 'frozen')`` is true.



Dictionaries and alphabets for the Spell checker
================================================
You can create/delete custom dictionaries via the +/- buttons right next to
the "Custom Dictionaries:" section.  You can add words to these custom
dictionaries by "Check"ing your document for misspellings, checking all of the
words you want to add, clicking "+ ./", then choosing the custom dictionary
you want the words added to.

If you want to use a large primary dictionary, create a 'dictionary.txt' file
that is utf-8 encoded, and place it into the same path that PyPE is.  This
will be far faster for startup, shutdown, and creating the list than manually
adding all of the words to custom dictionaries.  Fairly reasonable word lists
for english (British, Canadian, or American) are available at Kevin's Word 
list page: http://wordlist.sourceforge.net/ Words should be separated by any
standard whitespace character (spaces, tabs, line endings, etc.).

If you want to customize the alphabet that PyPE uses for suggesting spelling,
you can create an 'alphabet.txt' file that is utf-8 encoded, where alphabet
characters separated by commas ',', and place it into the same path that PyPE
is.



How does "One PyPE" work?
=========================
If "One PyPE" is selected, it will remove the file named 'nosocket' from the
path in which PyPE is running from (if it exists), and start a listening
socket on 127.0.0.1:9999 .  If "One PyPE" is deselected, it will create a file
called 'nosocket' in the path from which PyPE is running, and close the
listening socket (if one was listening).

Any new PyPE instances which attempt to open will check for the existence of
the nosocket file.  If it does not find that file, it will attempt to create a
new listening socket on 127.0.0.1:9999 .  If the socket creation fails, it
will attempt to connect to 127.0.0.1:9999 and send the documents provided on
the command-line to the other PyPE instance.  If it found the file, or if it
was able to create the socket, then a new instance of PyPE will be created,
and will use the preferences-defined "One PyPE" (preventing certain issues
involving a read-only path which PyPE is on, or a read-only nosocket file).

If you want to prevent new instances of PyPE from ever creating or using
sockets, create a file called 'nosocket' and make it read-only to PyPE.



What the heck is a Trigger?
===========================
Let us say that you writing a web page from scratch.  Let us also say that
typing in everything has gotten a bit tiresome, so you want to offer yourself
a few macro-like expansions, like 'img' -> '<img src="">'.

1. Go to: Document->Set Triggers.

2. Click on 'New Trigger'.

3. In the 'enter' column of the new trigger, type in 'img' (without quotes).

4. In the 'left' column, type in '<img src="' (without single-quotes).

5. In the 'right' column, type in '">' (without single quotes).

In the future, if you type in 'img' (without quotes) and use
Edit->Perform Trigger, it will expand itself to '<img src="">' (without single
quotes) with your cursor between the two double quotes.

What other nifty things are possible?  How about automatic curly and square
brace matching with [, [, ] and {, {, }?  Note that triggers with a single
character in the 'enter' column are automatically done as you type, but
triggers with multiple characters in the 'enter' column require using
Edit->Perform Trigger (or its equivalent hotkey if you have assigned one).

The semantics for string escapes are identical to that of standard string
escapes in Python.



Find/Replace bars
=================
If you have ' or " as the first character in a find or find/replace entry, and
what you entered is a proper string declaration in Python, PyPE will use the
compiler module to parse and discover the the string.  For example, to
discover LF characters, use ``"\\n"``, including quotes.



What the heck is going on with string escapes in regular expressions and/or multiline searches?
===============================================================================================
You can use standard Python strings with escapes and quote marks just like
when you use the find/replace bars with one minor difference; all searched
data is normalized to have ``\\n`` line endings regardless of the input.  This
means that if you want to find a colon followed by a line ending followed by
a space, you would use ``":\\n "``, including quotes.

If you include line endings in your search string, then multiline searching
will be automatically enabled during the search (but the box will remain
checked or unchecked).



What happens when "Smart Case" is enabled during a replace?
===========================================================
If the found string is all upper or lower case, it will be replaced by a
string that is also all upper or lower case.

Else if the length of the found string is the same length as the replacement
string, you can replace one string for another, preserving capitalization.

For example... ::

    def handleFoo(foo, arg2):
        tfOO = fcn(foo)
        tFOO2 = fcn2(tfOO)
        return fcn3(tfOO, tFOO2, foo)

...becomes... ::

    def handleGoo(goo, arg2):
        tgOO = fcn(goo)
        tGOO2 = fcn2(tgOO)
        return fcn3(tgOO, tGOO2, goo)

...by enabling "Smart Case", and putting 'foo' and 'goo' in the find/replace
boxes.

Otherwise if the first letter of the found string is upper or lowercase, then
its replacement will have the first letter be upper or lowercase respectively.



What is up with the "Enable File Drops" checkbox in the 'Edit' menu?
====================================================================
1. Select some text.

2. Now click on it.

Q: Do you want the selection to go away, and your cursor to be close to where
you clicked?

A1: If yes, uncheck the box and restart if necessary.

A2: If no, check the box and restart if necessary.

(The check is effective for any opened document from then on, but does not
change the behavior of already opened documents.)

One should always be able to drag and drop text.  One should always be able to
drag and drop files everywhere, except for the text editor portion.  If
checked, you can drop files on the editor portion, if unchecked, you won't be
able to drop files on the text editor portion.



How do I use the 'Todo' list?
=============================
On a line by itself (any amount of leading spaces), place something that
matches the following regular expression: ``#([a-zA-Z0-9 ]+):(.*)``

The first group (after a .strip().lower() translation) will become category in
the 'Category' column, the second group (after a .strip()) becomes the todo in
the 'Todo' column, and the number of exclamation points will become the number
in the '!' column.

Well, it is a bit smarter, it tosses all entries with a 'Category' that is
also a keyword (keyword.kwlist), or one of the following: http, ftp, mailto,
news, gopher, and telnet.

The following lines are all valid todos ::

    # todo: fix the code below
            #todo:fix the code below!
        #        TODo: fix the code below
    #bug:I am a big ugly bug...no, I really am, but I'm also a todo
    # this thing can even have spaces: but it cannot have punctuation!
    
    #I am not a valid todo...: because there is punctuation on the left



What are the currently known issues within PyPE's parser?
=========================================================
If given a syntactically correct Python source file, the Python parser will
work without issue, though it may not be fast (where fast is < .1 seconds).

If not given a syntactically correct Python source file, the parser splits the
file into lines, doing a check to see if there is a function, class, or
comment on that line, then saves the hierarchy information based on the level
of indentation and what came before it.  This can be inaccurate, as it will
mistakenly believe that the below function 'enumerate' is a method of
MyException. ::

    class MyException(exceptions.Exception):
        pass
    try:
        enumerate
    except:
        def enumerate(inp):
            return zip(range(len(inp)), inp)

It also doesn't know anything about multi-line strings, so the definition nada
in the following line would be seen as a function, and not part of a string. ::

    old = 'this used to be a function\
    def nada(inp):\
        return None'

Ah well, one has to give up something for speed.  Another thing given up is
that the parser will not pull out doc strings or handle multi-line function
definitions properly.

In the case of C or TeX files, I don't have a real parser for the C, so it
only really extracts todo items, and it only extracts \*section{} definitions
and todo items for TeX files.



How do you get usable Calltips?
===============================
Hit F5.  This will also rebuild the browsable source tree, autocomplete
listing, and todo list.



How do you get autocompletion?
==============================
Easy.  In the 'Document' menu, there is an entry for 'Show autocomplete'.
Make sure there is a check by it, and you are set.  If you want to get a new
listing of functions, hit the F5 key on your keyboard.



CRLF/LF/CR line endings
=======================
PyPE will attempt to figure out what kind of file was opened, it does this by
counting the number of different kinds of line endings.  Which ever line
ending appears the most in an open file will set the line ending support for
viewing and editing in the window.  Also, any new lines will have that line
ending.  New files will have the same line endings as the host operating
system.

Additionally, copying from an open document will not change the line-endings.
Future versions of PyPE may support the automatic translation of text during
copying and pasting to/from the host operating system's native line endings.

Converting between line endings is a menu item that is available in the
'Document' menu.



STCStyleEditor.py
=================
As I didn't write this, I can offer basically no support for it.  It seems to
work to edit python colorings, and if you edit some of the last 30 or so lines
of it, you can actually use the editor to edit some of the other styles that
are included.

If it doesn't work for you, I suggest you revert to the copy of the editor and
stc-styles.rc.cfg that is included with the distribution of PyPE you received.
As it is a known-good version, use it.



Expandable/collapsable/foldable code
====================================
Since the beginning, there have been expandable and collapsable scopes thanks
to wxStyledTextCtrl.  How to use them...
Given the below... ::

    - class nada:
    -     def funct(self):
    -         if 1:
    |             #do something
    |             pass

Shift-clicking the '-' next to the class does this... ::

    - class nada:
    +     def funct(self):

Or really, it's like ctrl-clicking on each of the functions declared in the
scope of the definition.  Shift-clicking on the '-' a second time does
nothing. Shift-clicking on a '+' expands that item completely.

Control-clicking on a '+' or '-' collapses or expands the entirety of the
scopes contained within.

I don't know about you, but I'm a BIG fan of shift-clicking classes.  Yeah.
Play around with them, you may like it.


Converting between tabs and spaces
==================================
So, you got tabs and you want spaces, or you have spaces and want to make them
tabs.  As it is not a menu option, you're probably wondering "how in the hell
am I going to do this".  Well, if you read the above stuff about string
escapes in the find/replace bar, it would be trivial.
Both should INCLUDE the quotation marks.
To convert from tabs to 8 spaces per tab; replace ``"\\t"`` with ``"        "``
To convert from 8 spaces to one tab; replace ``"        "`` with ``"\\t"``



---
FAQ
---

What's the deal with the version numbering scheme?
==================================================
Early in development, PyPE raised version numbers very quickly.  From 1.0 to
1.5, not much more than 2 months passed.  In that time, most of the major
initial architectural changes that were to happen, happened.  This is not the
reason for the version number change.  Really it was so that the MAJOR
versions could have their own point release (1.0 being the first), and minor
bugfixes on the point releases would get a minor release number (like 1.0.1).

Then, at around PyPE 1.4.2, I had this spiffy idea.  What if I were to release
a series of PyPE versions with the same version numbers as classic Doom?  I
remembered updating to 1.1, then to 1.2a, etc.  My favorite was 1.666.  Ah
hah! PyPE 1.6.6.6, the best version of PyPE ever.

I decided that I would slow version number advancement, if only so that people
didn't get sick of new releases of PyPE being numbered so much higher when
there were minimal actual changes.  Then the more I thought about it, the more
I realized that it doesn't matter at all, I mean, Emacs is on version 20+.
\*shrug\*

When PyPE 1.9.3 came out, I had a few other ideas for what I wanted to happen,
but since major changes needed to happen, it really should get a major number
bump to 2.0.  After spending 3 months not working on PyPE May-July 2004, I got
some time to muck around with it here and there.  After another few months of
trying to rebuild it to only require a single STC (with multiple document
pointers, etc.) I realized that I'd have to rebuild too much of PyPE to be
able to get 2.0 out the door by 2010.  So I started modifying 1.9.3.  All in
all, around 85% of what I wanted made it into PyPE 2.0, the rest was either
architectural (ick), or questionable as to whether or not anyone would even
want to use the feature (even me).


How did PyPE come about?
========================
The beginnings of PyPE was written from 10:30PM on the 2nd of July through
10:30PM on the 3rd of July, 2003.  Additional features were put together on
the 4th of July along with some bug fixing and more testing for version 1.0.
Truthfully, I've been using it to edit itself since the morning of the 3rd of
July, and believe it is pretty much feature-complete (in terms of standard
Python source editing).  There are a few more things I think it would be nice
to have, and they will be added in good time (if I have it).

One thing you should never expect is for PyPE to become an IDE.  Don't expect
a UML diagram.  Don't expect a debugger.  Don't expect debugging support
(what, print statements not good enough for you?)

On the most part, this piece of software should work exactly the way you
expect it to...or at least the way I expect it to.  That is the way I wrote
it.  As a result, you don't get much help in using it (mostly because I am
lazy).  There was a discussion of a PyPE wiki a long time ago, but that will
likely never happen.

The majority of the things that this editor can do are in the menus.  Hot-keys
for things that have them are listed next to their menu items, and you can
both rename menu items and change their hotkeys via Options->Change Menus and
Hotkeys.


----------
Thank Yous
----------
Certainly there are some people I should thank, because without them, the
piece of software you are using right now, just wouldn't be possible.

Guido van Rossum - without Guido, not only would I not have Python, I also
wouldn't have had some of the great inspiration that IDLE has offered.  IDLE
is a great editor, has some excellent ideas in terms of functionality, but it
unfortunately does not offer the extended functionality I want, and it hurts
my brain to use tk, so I cannot add it myself.  Guido, my hat goes off to you.

The people writing wxWidgets (previously named wxWindows) and wxPython -
without you, this also would not have been possible.  You have made the most
self-consistent GUI libraries that I have ever used, made them easy to use,
and offer them on every platform that I would ever want or need.  You rock.

Neil Hodgson and others who work on Scintilla.  As wx.StyledTextCtrl is a
binding for scintilla in wxWidgets, which then has bindings for wxPython,
basically ALL the REAL functionality of the editor you are now using is the
result of Scintilla.  The additional things like tabbed editing, hotkeys,
etc., they are mere surface decorations in comparison to what it would take to
write everything required for a text editor from scratch.  Gah, an editor
widget that just works?  Who would have figured?

To everyone who I have already thanked: thank you for making PyPE an almost
trivial task.  It would have been impossible to go so far so fast by hand in
any other language using any other GUI toolkit or bindings.

And my wife - because without her, I would likely be a pathetic shell of a
man...or at least single, bored, and uncouth.
