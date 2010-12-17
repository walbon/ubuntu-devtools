#
# question.py - Helper class for asking questions
#
# Copyright (C) 2010, Benjamin Drung <bdrung@ubuntu.com>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

def input_number(question, min_number, max_number, default=None):
    if default:
        question += " [%i]? " % (default)
    else:
        question += "? "
    selected = None
    while selected < min_number or selected > max_number:
        selected = raw_input(question).strip()
        if default and selected == "":
            selected = default
        else:
            try:
                selected = int(selected)
                if selected < min_number or selected > max_number:
                    print "Please input a number between %i and %i." % \
                          (min_number, max_number)
            except ValueError:
                print "Please input a number."
    assert type(selected) == int
    return selected

def boolean_question(question, default):
    if default is True:
        question += " [Y/n]? "
    else:
        question += " [y/N]? "
    selected = None
    while type(selected) != bool:
        selected = raw_input(question).strip().lower()
        if selected == "":
            selected = default
        elif selected in ("y", "yes"):
            selected = True
        elif selected in ("n", "no"):
            selected = False
        else:
            print "Please answer the question with yes or no."
    return selected

def yes_edit_no_question(question, default):
    assert default in ("yes", "edit", "no")
    if default == "yes":
        question += " [Y/e/n]? "
    elif default == "edit":
        question += " [y/E/n]? "
    else:
        question += " [y/e/N]? "
    selected = None
    while selected not in ("yes", "edit", "no"):
        selected = raw_input(question).strip().lower()
        if selected == "":
            selected = default
        elif selected in ("y", "yes"):
            selected = "yes"
        elif selected in ("e", "edit"):
            selected = "edit"
        elif selected in ("n", "no"):
            selected = "no"
        else:
            print "Please answer the question with yes, edit, or no."
    return selected
