#
# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import gettext

from yum.i18n import utf8_width
from subscription_manager.utils import get_terminal_width

_ = gettext.gettext


def ljust_wide(in_str, padding):
    return in_str + ' ' * (padding - utf8_width(in_str))


def columnize(caption_list, callback, *args, **kwargs):
    """
    Take a list of captions and values and columnize the output so that
    shorter captions are padded to be the same length as the longest caption.
    For example:
        Foo:            Bar
        Something Else: Baz

    This function also takes a callback which is used to render the final line.
    The callback gives us the ability to do things like replacing None values
    with the string "None" (see _none_wrap()).
    """
    indent = kwargs.get('indent', 0)
    caption_list = [" " * indent + caption for caption in caption_list]
    columns = get_terminal_width()
    padding = sorted(map(utf8_width, caption_list))[-1] + 1
    if columns:
        padding = min(padding, int(columns / 2))
    padded_list = []
    for caption in caption_list:
        lines = format_name(caption, indent, padding - 1).split('\n')
        lines[-1] = ljust_wide(lines[-1], padding) + '%s'
        fixed_caption = '\n'.join(lines)
        padded_list.append(fixed_caption)

    lines = zip(padded_list, args)
    output = []
    for (caption, value) in lines:
        if isinstance(value, list):
            if value:
                # Put the first value on the same line as the caption
                formatted_arg = format_name(value[0], padding, columns)
                output.append(callback(caption, formatted_arg))

                for val in value[1:]:
                    formatted_arg = format_name(val, padding, columns)
                    output.append(callback((" " * padding) + "%s", formatted_arg))
            else:
                # Degenerate case of an empty list
                output.append(callback(caption, ""))
        else:
            formatted_arg = format_name(value, padding, columns)
            output.append(callback(caption, formatted_arg))
    return '\n'.join(output)


def format_name(name, indent, max_length):
    """
    Formats a potentially long name for multi-line display, giving
    it a columned effect.  Assumes the first line is already
    properly indented.
    """
    if not name or not max_length or (max_length - indent) <= 2 or not isinstance(name, basestring):
        return name
    if not isinstance(name, unicode):
        name = name.decode("utf-8")
    words = name.split()
    lines = []
    # handle emtpty names
    if not words:
        return name

    # Preserve leading whitespace in front of the first word
    leading_space = len(name) - len(name.lstrip())
    words[0] = name[0:leading_space] + words[0]
    # If there is leading whitespace, we've already indented the word and don't
    # want to double count.
    current = indent - leading_space
    if current < 0:
        current = 0

    def add_line():
        lines.append(' '.join(line))

    line = []
    # Split here and build it back up by word, this way we get word wrapping
    while words:
        word = words.pop(0)
        if current + utf8_width(word) <= max_length:
            current += utf8_width(word) + 1  # Have to account for the extra space
            line.append(word)
        else:
            if line:
                add_line()
            # If the word will not fit, break it
            if indent + utf8_width(word) > max_length:
                split_index = 0
                while(utf8_width(word[:split_index + 1]) + indent <= max_length):
                    split_index += 1
                words.insert(0, word[split_index:])
                word = word[:split_index]
            line = [word]
            if indent and lines:
                line.insert(0, ' ' * (indent - 1))
            current = indent + utf8_width(word) + 1

    add_line()
    return '\n'.join(lines)


def _none_wrap(template_str, *args):
    """
    Takes a template string and arguments and replaces any None arguments
    with the word "None" before rendering the template.  Mainly this is
    a callback meant to be used by columnize().
    """
    arglist = []
    for arg in args:
        if arg is None:
            arg = _("None")
        arglist.append(arg)
    return template_str % tuple(arglist)


def _echo(template_str, *args):
    """
    Just takes a template string and arguments and renders it.  Mainly
    this is a callback meant to be used by columnize().
    """
    return template_str % tuple(args)


# from http://farmdev.com/talks/unicode/
def to_unicode_or_bust(obj, encoding='utf-8'):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj
