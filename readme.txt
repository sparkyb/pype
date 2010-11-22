Readme/Help for PyPE 1.2 (Python Programmer's Editor')
http://come.to/josiah

PyPE is copyright (c) 2003 Josiah Carlson.

This software is licensed under the GPL (GNU General Public License) as it
appears here: http://www.gnu.org/copyleft/gpl.html
It is also included with this archive as gpl.txt.

The included STCStyleEditor.py, which is used to support styles, was released
under the wxWindows license and is copyright (c) 2001 - 2002 Riaan Booysen.
The copy included was also distributed with wxPython version 2.4.1.2 for
Python 2.2, and was not modified in any form.

The included stc-styles.rc.cfg was slightly modified from the original version
in order to no cause exceptions during style changes, and was also distributed
with wxPython version 2.4.1.2 for Python 2.2

If you do not also receive a copy of gpl.txt with your version of this
software, please inform the me of the violation at the web page at the top of
this document.

#------------------------------- Requirements --------------------------------
PyPE has only been tested on Python 2.2 and wxPython 2.4.2.1.  It should work
on later versions of Python and wxPython.

#----------------------------------- Help ------------------------------------
The majority of PyPE was written from 10:30PM on the 2nd of July through
10:30PM on the 3rd of July.  Additional features were put together on the 4th
of July along with some bug fixing and more testing for version 1.0.
Truthfully, I've been using it to edit itself since the morning of the 3rd of
July, and believe it is pretty much feature-complete (in terms of standard
Python source editing).  There are a few more things I think it would be nice
to have, and they will be added in good time.

On the most part, this piece of software should work exactly the way you
expect it to.  That is the way I wrote it.  As a result, you don't get much
help in using it (mostly because I am lazy).  When questions are asked, I'll
add the question and answer into the FAQ, which is at the end of this
document.


You'll notice some really useful things, like it remembering which path the
file you have currently open was in (for further opens), or in the case of
new files that have not been saved, the path of the last opened file.  I find
this quite convenient, I hope you do too.


The majority of the things that this editor can do are in the menus.  Hot-keys
for things that have them are listed next to their menu items.  As I am still
learning all the neat things one can do with wxStyledTxtCtrl, I don't know all
the built-in features, and this is likely as much of a learning experience for
me as you.

#-------------------------------- Visual bugs --------------------------------
Save As dialog:
When the Save As dialog opens for you to save a document, rather than 'save',
it lists 'open'.  This is the result of using the standard wxPython browse
dialog, which I use to get a folder and path.  I assure you, it saves your
document properly.  Remember, visual bug, NOT functonality bug.

#------------------------------------ FAQ ------------------------------------
Shell Commands:
I don't know how much other people use this feature, but I use it enough to
warrant the time I spent implementing it.  Basically this allows you to run
shell commands or scripts or even the script you are currently editing.  It
SHOULD just work for most things.  I know that it works on windows, and I
believe that it should work in *nix thanks to os.spawnvp (windows lacks a
os.spawnvp, but this can be basically emulated thanks to os.system and the
often underutilized 'start <cmd>', which will spawn a process...like
os.spawnvp should in windows (with an occasional extra console window floating
around).

Play around with it, and remember to read the titles of the windows.



Code Snippets:
Ahh, what are code snippets?  Basically it is a saved-state multiple-entry
clipboard.  What is the use of that?  Well, let us say that you have a
template for interfaces to, let us say, commands for an interactive online
multiplayer game.  Each command needs to have a specific format, and with this
code snippet support, you don't need to switch to your template file, copy,
switch back and paste.  You can select your insertion point, and double click.
There are, of course, hot-keys for using code snippets while editing your
document.  Why?  Because I like having that option.  You can navigate and
insert code snippets without ever having your hands leave the keyboard.
Deleting a code snippet is a easy as making sure the listbox has keyboard
focus, and hitting 'delete' when the snippet you want to remove is selected.
Play around with it, you will (I believe) come to enjoy it.

Code Snippets are saved at program exit automatically.  If you mess up the
snippets, and want one back, don't close the program.  Open up snippets.py,
copy the code for that snippet.  They are stored in Python string format,
which means tabs are \t, newlines are \n, etc.  A quick;
print eval("python string")
will convert it back into something that you can paste into your code snippets
again.

If there is feedback/desire for being able to reorganize code snippets, I'll
add that support.



Bookmarked Paths:
Everyone will surely notice the menu for Pathmarks.  This menu allows you to
edit and access bookmarked paths with relative ease.  All it really does is
remember the paths you tell it to, and when you use one of the hotkeys or menu
items, it will change the current working directory to that new path. If you
attempt to open a file immediately afterwards, the open dialog will seek to
the path of the just used bookmark.  Nifty eh?  I like to think of it as being
able to have 'projects' without having to specify a project file.  I hate
project files.



Find/Replace dialogs:
One big thing to note is how the find and find/replace dialogs work.  For
those of you who are annoyed with one's normal inability to enter in things
like newlines, this will be a great thing for you.

If you have ' or " as the first character in a find or find/replace dialog,
and what you entered is a proper string declaration in Python, that is the
string that will be found/replaced or replaced with.  Sorry, no raw string
support via r'c:\\new downloads\\readme.txt' so yeah.

As well, I've not implemented the ability to search up in the find dialog.
I may in future versions.  No matter what you have selected, it will always
search forward (and even wrap around if you keep hitting 'find next').

Converting between tabs and spaces:
So, you got tabs and you want spaces, or you have spaces and want to make them
tabs.  As it is not a menu option, you're probably wondering "how in the hell
am I going to do this".  Well, if you read the above stuff about the find and
replace dialogs, it would be trivial.
Both should INCLUDE the quotation marks.
To convert from tabs to 8 spaces per tab; replace "\t" with "        "
To convert from 8 spaces to one tab; replace "        " with "\t"



CRLF/LF/CR line endings:
PyPE will attempt to figure out what kind of file was opened, it does this by
counting the number of different kind of line endings.  Which ever line ending
appears the most in an open file will set the line ending support for viewing
and editing in the window.  Also, any new lines will have that line ending.
New files will have the default line endings as the host operating system, as
given in configuration.py.  The only platforms I don't know for sure are
RISCOS and JAVA, though I assume them to be '\n'.  Any information about what
really is the case would be great.

Additionally, copying from an open document will not change the line-endings.
Future versions of PyPE may support the automatic translation of text during
copying and pasting to the host operating system's native line endings.

Converting between line endings is as easy as the tab and space conversion as
given above.



STCStyleEditor.py:
As I didn't write this, I can offer basically no support for it.  It seems to
work to edit python colorings, and if you edit some of the last 30 or so lines
of it, you can actually use the editor to edit some of the other styles that
are included.

If it just doesn't work for you, I suggest you revert to the copy of the
editor and stc-styles.rc.cfg that is included with the distribution of PyPE
you received.  As it is a known-good version, use it.



Expandable/collapseable scope:
Since the beginning, there have been expandable and collapseale scopes thanks
to wxStyledTxtCtrl.  How to use them...
Given the below...
- class nada:
-     def funct(self):
-         if 1:
|             #do something
|             pass
Shift-clicking the '-' next to the class does this...
- class nada:
+     def funct(self):

Or really, it's like ctrl-clicking on each of the functions declared in the
scope of the definition.
Shift-clicking on the '-' a second time does nothing.
Shift-clicking on a '+' expands that item completely.

Control-clicking on a '+' or '-' collapses or expands the entirety of the
scopes contained within.

I don't know about you, but I'm a BIG fan of shift-clicking classes.  Yeah.
Play around with them, you'll get to loving how they work.

#-------------------------------- Thank You's --------------------------------
Certainly there are some people I should thank, because without them, the
piece of software you are using right now, just wouldn't be possible.

Guido van Rossum - without Guido, not only would I not have Python, I also
wouldn't have had some of the great inspiration that IDLE has offered.  IDLE
is a great editor, has some excellent ideas in terms of functionality, but it
unfortunately does not offer the extended functionality I want, and it hurts
my brain to use tk, so I cannot add it myself.  Guido, my hat comes off for
you.

The people writing wxWindows and wxPython - without you, this also would not
have been possible.  You have made the most self-consistent GUI libraries that
I have ever used, made them easy to use, and offer them on every platform that
I would ever want or need.  You rock.

The people writing Scintilla - as wxStyledTextCtrl is a binding for scitilla
for wxWindows, which then has bindings for wxPython, basically ALL the REAL
functionality of the editor you are now using is the result of Scintilla.
The additional things like tabbed editing, hotkeys, etc., they are mere
surface decorations in comparison to what it would take to write everything
required for a text editor from scratch.  Gah, an editor widget that just
works?  Who would have figured?

To everyone who I have already thanked: thank you for making PyPE an almost
trivial task.  It would have been impossible to go so far so fast in any other
language using any other GUI toolkit or bindings.

My wife - because without her, I would likely be a pathetic shell of a man.
What is funny is that you think I'm kidding.
#------------------------------- End of file. --------------------------------
