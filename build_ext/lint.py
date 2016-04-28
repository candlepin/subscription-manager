# Copyright (c) 2016 Red Hat, Inc.
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
import ast
import flake8.main
import pep8
import re

from collections import deque

from distutils.spawn import spawn
from distutils.text_file import TextFile

from flake8.util import iter_child_nodes

from xml.etree import ElementTree

from build_ext.utils import Utils, BaseCommand, LineNumberingParser


class Lint(BaseCommand):
    description = "examine code for errors"

    def has_pure_modules(self):
        return self.distribution.has_pure_modules()

    def has_glade_files(self):
        try:
            next(Utils.find_files_of_type('src', '*.glade'))
            return True
        except StopIteration:
            return False

    def has_spec_file(self):
        try:
            next(Utils.find_files_of_type('.', '*.spec'))
            return True
        except StopIteration:
            return False

    def run(self):
        for cmd_name in self.get_sub_commands():
            self.run_command(cmd_name)

    # Defined at the end since it references unbound methods
    sub_commands = [
        ('lint_glade', has_glade_files),
        ('lint_gettext', has_pure_modules),
        ('lint_rpm', has_spec_file),
        ('flake8', has_pure_modules),
    ]


class RpmLint(BaseCommand):
    description = "run rpmlint on spec files"

    def run(self):
        for f in Utils.find_files_of_type('.', '*.spec'):
            spawn(['rpmlint', '--file=rpmlint.config', f])


class FileLint(BaseCommand):
    def scan_file(self, f, regexs):
        # Use TextFile since it has a nice function to print a warning with the
        # offending line's number.
        text_file = TextFile(f)

        # Thanks to http://stackoverflow.com/a/17502838/6124862
        contents = '\n'.join(text_file.readlines())
        for r in regexs:
            regex = re.compile(r, flags=re.MULTILINE | re.DOTALL)
            for match in regex.finditer(contents):
                lineno = contents.count('\n', 0, match.start())
                text_file.warn("Found '%s' match" % r, lineno)
        text_file.close()

    def scan_xml(self, f, xpath_expressions, namespaces=None):
        if not namespaces:
            namespaces = {}

        text_file = TextFile(f)
        tree = ElementTree.parse(f, parser=LineNumberingParser())

        for x in xpath_expressions:
            elements = tree.findall(x, namespaces)
            for e in elements:
                text_file.warn("Found '%s' match" % x, e._start_line_number)
        text_file.close()


class GladeLint(FileLint):
    """See BZ #826874.  Certain attributes cause issues on older libglade."""
    description = "check Glade files for common errors"

    def run(self):
        for f in Utils.find_files_of_type('src', '*.ui'):
            self.scan_xml(f, ["//property[@name='orientation']", "//*[@swapped='no']"])


class AstChecker(pep8.Checker):
    _error_tmpl = "Error found"

    def __init__(self, tree, filename):
        self.tree = tree
        self.filename = filename
        self.parents = deque()

    # Thanks to https://bitbucket.org/takluyver/greentreesnakes/src/default/astpp.py
    def dump(self, node, annotate_fields=True, include_attributes=False, indent='  '):
        """
        Return a formatted dump of the tree in *node*.  This is mainly useful for
        debugging purposes.  The returned string will show the names and the values
        for fields.  This makes the code impossible to evaluate, so if evaluation is
        wanted *annotate_fields* must be set to False.  Attributes such as line
        numbers and column offsets are not dumped by default.  If this is wanted,
        *include_attributes* can be set to True.
        """
        def _format(node, level=0):
            if isinstance(node, ast.AST):
                fields = [(a, _format(b, level)) for a, b in ast.iter_fields(node)]
                if include_attributes and node._attributes:
                    fields.extend([(a, _format(getattr(node, a), level))
                                   for a in node._attributes])
                return ''.join([
                    node.__class__.__name__,
                    '(',
                    ', '.join(('%s=%s' % field for field in fields)
                               if annotate_fields else
                               (b for a, b in fields)),
                    ')'])
            elif isinstance(node, list):
                lines = ['[']
                lines.extend((indent * (level + 2) + _format(x, level + 2) + ','
                             for x in node))
                if len(lines) > 1:
                    lines.append(indent * (level + 1) + ']')
                else:
                    lines[-1] += ']'
                return '\n'.join(lines)
            return repr(node)

        if not isinstance(node, ast.AST):
            raise TypeError('expected AST, got %r' % node.__class__.__name__)
        return _format(node)

    def run(self):
        return self.visit_tree(self.tree) if self.tree else ()

    def visit_tree(self, node):
        for error in self.visit_node(node):
            yield error
        self.parents.append(node)
        for child in iter_child_nodes(node):
            for error in self.visit_tree(child):
                yield error
        self.parents.pop()

    def visit_node(self, node):
        return

    def err(self, node, msg=None):
        if not msg:
            msg = self._error_tmpl

        lineno = node.lineno
        col_offset = node.col_offset

        # Adjust line number and offset if a decorator is applied
        if isinstance(node, ast.ClassDef):
            lineno += len(node.decorator_list)
            col_offset += 6
        elif isinstance(node, ast.FunctionDef):
            lineno += len(node.decorator_list)
            col_offset += 4

        ret = (lineno, col_offset, msg, self)
        return ret


class GettextChecker(AstChecker):
    """Looks for Python string formats that are known to break xgettext.
    Specifically, constructs of the forms:
        _("a" + "b")
        _("a" + \
        "b")
    Also look for _(a) usages
    """
    _error_tmpl = 'G100 string concatenation that will break xgettext'

    def visit_node(self, node):
        if not isinstance(node, ast.Call):
            return

        func = node.func
        if not isinstance(func, ast.Name):
            return

        if func.id != '_':
            return

        for arg in node.args:
            # TODO is a BinOp of type Mod acceptable? e.g. _("%s is great" % some_variable)
            # Those constructs exist but may be wrong

            # Things like _("a" + "b") (including such constructs across line continuations
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                yield self.err(node, "G100 string concatenation that will break xgettext")

            # Things like _(some_variable)
            if isinstance(arg, ast.Name):
                yield self.err(node, "G101 variable reference that will break xgettext")


class PluginLoadingFlake8Command(flake8.main.Flake8Command):
    """A Flake8 runner that will load our custom plugins.  It's important to note
    that this has to be invoked via `./setup.py flake8`.  Just running `flake8` won't
    cut it.

    Flake8 normally wants to load plugins via entry_points, but as far as I can tell
    that would require packaging our checkers separately.
    """

    def run(self):
        pep8.register_check(GettextChecker, codes='G100')
        flake8.main.Flake8Command.run(self)
