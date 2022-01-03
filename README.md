# `show`

Ever put so many debug `print` statements in your code that you have trouble
figuring out which one the output is coming from so now you start prefixing them
with `"foo"`, `"bar"`, `"qux"`, `"yolo"`, `"foo1"`, `"foo2"`, `"foo5"`?  Yeah,
me neither.  Anyway, I made this thing.

# What does it do?

Like `print`, `show` will print its arguments.  But it will also print the
expressions that produced those arguments (unless and argument is given by
keyword, in which case the keyword is printed).  Oh, and it also has colors.
And it prints the source location of the `show` statement.

# How do I use it?

Instead of `print` you write `show`.  That's it.

# Limitations

It only works if you call `show` as `show`, that is, no passing around function
pointers (or whatever they're called in Python).  Only one `show` statement is
allowed per line.  It doesn't work in a REPL.  And then there's all the bugs I
haven't found.


