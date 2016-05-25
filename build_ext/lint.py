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
import re
import tokenize

from distutils.spawn import spawn
from distutils.text_file import TextFile

from build_ext.utils import Utils, BaseCommand, memoize

try:
    # These dependencies aren't available in build environments.  We won't need any
    # linting functionality there though, so just create a dummy class so we can proceed.
    from pep8 import Checker, register_check, NEWLINE, expand_indent

    from flake8.main import Flake8Command

    from lxml import etree as ElementTree
except ImportError:
    class Checker(object):
        pass

    class Flake8Command(object):
        pass

    class ElementTree(object):
        @staticmethod
        def parse(*args, **kwargs):
            raise NotImplementedError("lxml could not be imported")


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
        tree = ElementTree.parse(f)

        for x in xpath_expressions:
            # Python 2.6's element tree doesn't support findall with namespaces
            # we aren't currently using namespaces so put in a shim to be compatible
            # If we ever need to specify namespaces, we are not going to be able
            # to run this code on 2.6
            if namespaces:
                elements = tree.findall(x, namespaces)
            else:
                elements = tree.findall(x)

            for e in elements:
                text_file.warn("Found '%s' match" % x, e.sourceline)
        text_file.close()


class GladeLint(FileLint):
    """See BZ #826874.  Certain attributes cause issues on older libglade."""
    description = "check Glade files for common errors"

    def run(self):
        for f in Utils.find_files_of_type('src', '*.glade'):
            self.scan_xml(f, [".//property[@name='orientation']", ".//*[@swapped='no']"])


class AstVisitor(object):
    """Visitor pattern for looking at specific nodes in an AST.  Basically a copy of
    ast.NodeVisitor, but with the additional feature of appending return values onto a result
    list that is ultimately returned.

    I recommend reading http://greentreesnakes.readthedocs.io/en/latest/index.html for a good
    overview of the various Python AST node types.
    """

    def __init__(self):
        self.results = []

    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        r = visitor(node)
        if r is not None:
            self.results.append(r)
        return self.results

    def generic_visit(self, node):
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
            elif isinstance(value, ast.AST):
                self.visit(value)


class WidgetVisitor(AstVisitor):
    """Look for widgets that are used in code but not declared in the Glade files."""
    codes = ['U100']

    class StrVisitor(AstVisitor):
        def visit_Str(self, node):
            return node.s

    class NameVisitor(AstVisitor):
        def visit_Name(self, node):
            return node.id

    def __init__(self, defined_widgets=None):
        super(WidgetVisitor, self).__init__()
        if not defined_widgets:
            defined_widgets = []

        self.defined_widgets = set(defined_widgets)

    def visit_Assign(self, node):
        # Likely not necessary but prudent
        self.generic_visit(node)

        for target in node.targets:
            names = self.NameVisitor().visit(target)
            for name in names:
                if name in ['widget', 'widget_names']:
                    widgets = set(self.StrVisitor().visit(node.value))
                    widgets.difference_update(self.defined_widgets)
                    if widgets:
                        return (node, "U100 widgets %s are not defined in the Glade files" % list(widgets))


class SignalVisitor(AstVisitor):
    """Look for signals that are used in code but not declared in the Glade files."""
    codes = ['U101']

    class DictVisitor(AstVisitor):
        def visit_Dict(self, node):
            # Note this will break if someone uses a Name for a key instead of an Str
            # Hopefully no one will do that because we wouldn't be able to get at the value
            # the Name holds
            return [k.s for k in node.keys]

    def __init__(self, defined_handlers=None):
        super(SignalVisitor, self).__init__()
        if not defined_handlers:
            defined_handlers = []

        self.defined_handlers = set(defined_handlers)

    def visit_Call(self, node):
        self.generic_visit(node)

        func = node.func
        if not isinstance(func, ast.Attribute):
            return

        if func.attr == 'connect_signals':
            keys = self.DictVisitor().visit(node.args[0])
            # Flatten the list of lists
            handlers = set([item for sublist in keys for item in sublist])
            handlers.difference_update(self.defined_handlers)
            if handlers:
                return (node, "U101 handlers %s are not defined in the Glade files" % list(handlers))


class DebugImportVisitor(AstVisitor):
    """Look for imports of various debug modules"""

    DEBUG_MODULES = ['pdb', 'pudb', 'ipdb', 'pydevd']
    codes = ['D100']

    def visit_Import(self, node):
        # Likely not necessary but prudent
        self.generic_visit(node)

        for alias in node.names:
            module_name = alias.name
            if module_name in self.DEBUG_MODULES:
                return(node, "D100 imports of debug module '%s' should be removed" % module_name)

    def visit_ImportFrom(self, node):
        # Likely not necessary but prudent
        self.generic_visit(node)
        module_name = node.module
        if module_name in self.DEBUG_MODULES:
            return(node, "D100 imports of debug module '%s' should be removed" % module_name)


class GettextVisitor(AstVisitor):
    """Looks for Python string formats that are known to break xgettext.
    Specifically, constructs of the forms:
        _("a" + "b")
        _("a" + \
        "b")
    Also look for _(a) usages
    """
    codes = ['G100', 'G101']

    def visit_Call(self, node):
        # Descend first
        self.generic_visit(node)

        func = node.func
        if not isinstance(func, ast.Name):
            return

        if func.id != '_':
            return

        for arg in node.args:
            # TODO is a BinOp of type Mod acceptable? e.g. _("%s is great" % some_variable)
            # Those constructs exist but may be wrong

            # ProTip: use print(ast.dump(node)) to figure out what the node looks like

            # Things like _("a" + "b") (including such constructs across line continuations
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                return (node, "G100 string concatenation that will break xgettext")

            # Things like _(some_variable)
            if isinstance(arg, ast.Name):
                return (node, "G101 variable reference that will break xgettext")


class AstChecker(Checker):
    def __init__(self, tree, filename, *args, **kwargs):
        self.tree = tree
        self.filename = filename

        widgets = []
        handlers = []
        for f in Utils.find_files_of_type('src', '*.glade', '*.ui'):
            # Note that we are sending in the file name rather than a file handle.  By using
            # the file name, we can take advantage of memoizing on the name instead of on an
            # instance of a file handle
            widgets.extend(self.scan_widgets(f))
            handlers.extend(self.scan_handlers(f))

        self.visitors = [
            (GettextVisitor, {}),
            (DebugImportVisitor, {}),
            (WidgetVisitor, {'defined_widgets': widgets}),
            (SignalVisitor, {'defined_handlers': handlers}),
        ]
        super(AstChecker, self).__init__(filename, *args, **kwargs)

    @staticmethod
    @memoize
    def scan_widgets(f):
        """Scan a file for object elements with a class and id attribute.  Return
        the value of the id attribute.
        """

        # We cache all the results because this class gets instantiated for every
        # source file and this method scans every Glade file.  That would be a lot
        # of redundant XML parsing (N source files * M Glade files) if we didn't memoize it.
        widgets = []
        with open(f, 'r') as f:
            tree = ElementTree.parse(f)
        elements = tree.findall(".//object[@class][@id]")
        for e in elements:
            widgets.append(e.attrib['id'])
        return widgets

    @staticmethod
    @memoize
    def scan_handlers(f):
        handlers = []
        with open(f, 'r') as f:
            tree = ElementTree.parse(f)
        elements = tree.findall(".//signal[@name][@handler]")
        for e in elements:
            handlers.append(e.attrib['handler'])
        return handlers

    def run(self):
        if self.tree:
            for visitor, kwargs in self.visitors:
                result = visitor(**kwargs).visit(self.tree)
                if result:
                    for node, msg in result:
                        yield self.err(node, msg)

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


def detect_overindent(logical_line, tokens, indent_level, hang_closing, indent_char, noqa, verbose):
    """Flag lines that are overindented.  This includes lines that are indented solely to align
    vertically with an opening brace.  This rule allows continuation lines to be relatively
    indented up to 8 spaces and closes braces to be relatively indented up to 4 spaces.  Heavily
    adapted from pep8's continued_indentation method

    Okay: foo = my_func('hello',
              'world'
              )
    Okay: foo = my_func('hello',
                  'world')

    Okay: foo = my_func('hello',
              )

    E198: foo = my_func('hello',
                       )
    E199: foo = my_func('hello',
                        'world')
    """
    first_row = tokens[0][2][0]
    nrows = 1 + tokens[-1][2][0] - first_row
    if noqa or nrows == 1:
        return

    row = depth = 0

    # relative indents of physical lines
    rel_indent = [0] * nrows
    open_rows = [[0]]
    last_indent = tokens[0][2]
    indent = [last_indent[1]]

    last_token_multiline = False

    if verbose >= 3:
        print(">>> " + tokens[0][4].rstrip())

    for token_type, text, start, end, line in tokens:
        newline = row < start[0] - first_row
        if newline:
            row = start[0] - first_row
            newline = not last_token_multiline and token_type not in NEWLINE

        if newline:
            # this is the beginning of a continuation line.
            last_indent = start
            if verbose >= 3:
                print("... " + line.rstrip())

            # record the initial indent.
            rel_indent[row] = expand_indent(line) - indent_level

            # identify closing bracket
            close_bracket = (token_type == tokenize.OP and text in ']})')

            # is the indent relative to an opening bracket line?
            for open_row in reversed(open_rows[depth]):
                hang = rel_indent[row] - rel_indent[open_row]

            if not close_bracket and hang > 8:
                yield start, "E199 continuation line over-indented"

            if close_bracket and hang > 4:
                yield (start, "E198 closing bracket over-indented")

        # Keep track of bracket depth to check for proper indentation in nested
        # brackets
        # E.g.
        # Okay: foo = [[
        #           '1'
        #       ]]
        #
        # but even though we are nested twice, we should only allow one level of indentation, so:
        #
        # E199: foo = [[
        #               '1'
        #       ]]

        if token_type == tokenize.OP:
            if text in '([{':
                depth += 1
                indent.append(0)
                if len(open_rows) == depth:
                    open_rows.append([])
                open_rows[depth].append(row)
                if verbose >= 4:
                    print("bracket depth %s seen, col %s, visual min = %s" %
                          (depth, start[1], indent[depth]))
            elif text in ')]}' and depth > 0:
                # parent indents should not be more than this one
                prev_indent = indent.pop() or last_indent[1]
                for d in range(depth):
                    if indent[d] > prev_indent:
                        indent[d] = 0
                del open_rows[depth + 1:]
                depth -= 1
            assert len(indent) == depth + 1

        last_token_multiline = (start[0] != end[0])
        if last_token_multiline:
            rel_indent[end[0] - first_row] = rel_indent[row]


class PluginLoadingFlake8Command(Flake8Command):
    """A Flake8 runner that will load our custom plugins.  It's important to note
    that this has to be invoked via `./setup.py flake8`.  Just running `flake8` won't
    cut it.

    Flake8 normally wants to load plugins via entry_points, but as far as I can tell
    that would require packaging our checkers separately.
    """
    def distribution_files(self):
        # By default Flake8Command only runs on packages registered with
        # setuptools.  We want it to look at tests and other things as well
        #
        # Additionally https://gitlab.com/pycqa/flake8/issues/134 causes Flake8
        # to check files in sub-packages multiple times.  Telling it to check
        # only the top level directories fixes the issue.
        for d in ['src', 'test', 'build_ext', 'example-plugins', 'setup.py']:
            yield d

    def run(self):
        codes = DebugImportVisitor.codes + GettextVisitor.codes + WidgetVisitor.codes + SignalVisitor.codes
        register_check(AstChecker, codes=codes)
        register_check(detect_overindent, codes=['E198', 'E199'])
        # To see what Flake8 is actually checking use
        # self.options_dict['verbose'] = 1
        Flake8Command.run(self)
