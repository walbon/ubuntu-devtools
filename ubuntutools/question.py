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

class Question(object):
    def __init__(self, options, show_help=True):
        assert len(options) >= 2
        self.options = map(lambda s: s.lower(), options)
        self.show_help = show_help

    def get_options(self):
        if len(self.options) == 2:
            options = self.options[0] + " or " + self.options[1]
        else:
            options = ", ".join(self.options[:-1]) + ", or " + self.options[-1]
        return options

    def ask(self, question, default=None):
        if default is None:
            default = self.options[0]
        assert default in self.options

        separator = " ["
        for option in self.options:
            if option == default:
                question += separator + option[0].upper()
            else:
                question += separator + option[0]
            separator = "|"
        if self.show_help:
            question += "|?"
        question += "]? "

        selected = None
        while selected not in self.options:
            selected = raw_input(question).strip().lower()
            if selected == "":
                selected = default
            else:
                for option in self.options:
                    # Example: User typed "y" instead of "yes".
                    if selected == option[0]:
                        selected = option
            if selected not in self.options:
                print "Please answer the question with " + \
                      self.get_options() + "."
        return selected


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
