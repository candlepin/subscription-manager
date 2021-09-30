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
import tokenize

from distutils.spawn import spawn

from build_ext.utils import Utils, BaseCommand

# These dependencies aren't available in build environments.  We won't need any
# linting functionality there though, so just create a dummy class so we can proceed.
try:
    import pycodestyle
except ImportError:
    pycodestyle = None

try:
    import pkg_resources
except ImportError:
    pkg_resources = None

try:
    from flake8.main.setuptools_command import Flake8
except ImportError:
    class Flake8(object):
        def __init__(self, *args, **kwargs):
            raise NotImplementedError("flake8 could not be imported")


class Lint(BaseCommand):
    description = "examine code for errors"

    def has_pure_modules(self):
        return self.distribution.has_pure_modules()

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
        ('lint_rpm', has_spec_file),
        ('flake8', has_pure_modules),
    ]


class RpmLint(BaseCommand):
    description = "run rpmlint on spec files"

    def run(self):
        for f in Utils.find_files_of_type('.', '*.spec'):
            spawn(['rpmlint', '--file=rpmlint.config', f])


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


class DebugImportVisitor(AstVisitor):
    """Look for imports of various debug modules"""

    DEBUG_MODULES = ['pdb', 'pudb', 'ipdb', 'pydevd']
    codes = ['X200']

    def visit_Import(self, node):
        # Likely not necessary but prudent
        self.generic_visit(node)

        for alias in node.names:
            module_name = alias.name
            if module_name in self.DEBUG_MODULES:
                return(node, "X200 imports of debug module '%s' should be removed" % module_name)

    def visit_ImportFrom(self, node):
        # Likely not necessary but prudent
        self.generic_visit(node)
        module_name = node.module
        if module_name in self.DEBUG_MODULES:
            return(node, "X200 imports of debug module '%s' should be removed" % module_name)


class GettextVisitor(AstVisitor):
    """Looks for Python string formats that are known to break xgettext.
    Specifically, constructs of the forms:
        _("a" + "b")
        _("a" + \
        "b")
    Also look for _(a) usages
    """
    codes = ['X300', 'X301', 'X302']

    def visit_Call(self, node):
        # Descend first
        self.generic_visit(node)

        func = node.func
        if not isinstance(func, ast.Name):
            return

        if func.id != '_':
            return

        for arg in node.args:
            # ProTip: use print(ast.dump(node)) to figure out what the node looks like

            # Things like _("a" + "b") (including such constructs across line continuations
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                return (node, "X300 string concatenation that will break xgettext")

            # Things like _(some_variable)
            if isinstance(arg, ast.Name):
                return (node, "X301 variable reference that will break xgettext")

            # _("%s is great" % some_variable) should be _("%s is great") % some_variable
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
                return (node, "X302 string formatting within gettext function: _('%s' % foo) should be _('%s') % foo")


class AstChecker(object):
    name = "SubscriptionManagerAstChecker"
    version = "1.0"

    def __init__(self, tree, filename):
        self.tree = tree
        self.filename = filename

        self.visitors = [
            (GettextVisitor, {}),
            (DebugImportVisitor, {}),
        ]

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

        lineno = getattr(node, "lineno", 1)
        col_offset = getattr(node, "col_offset", 0)

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
    adapted from pycodestyle's continued_indentation method

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
            newline = not last_token_multiline and token_type not in pycodestyle.NEWLINE

        if newline:
            # this is the beginning of a continuation line.
            last_indent = start
            if verbose >= 3:
                print("... " + line.rstrip())

            # record the initial indent.
            rel_indent[row] = pycodestyle.expand_indent(line) - indent_level

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


class PluginLoadingFlake8(Flake8):
    """A Flake8 runner that will load our custom plugins.  It's important to note
    that this has to be invoked via `./setup.py flake8`.  Just running `flake8` won't
    cut it.

    Flake8 normally wants to load plugins via entry_points, but as far as I can tell
    that would require packaging our checkers separately.  Instead, we create a phony
    pkg_resources Distribution that loads up the build_ext directory.  That directory
    has some metadata files that associate the AstChecker class with the flake8.extension
    entry point.

    See http://peak.telecommunity.com/DevCenter/PkgResources
    """
    def __init__(self, *args, **kwargs):
        ext_dir = pkg_resources.normalize_path('build_ext')
        dist = pkg_resources.Distribution(
            ext_dir,
            project_name='build_ext',
            metadata=pkg_resources.PathMetadata(ext_dir, ext_dir)
        )
        pkg_resources.working_set.add(dist)
        Flake8.__init__(self, *args, **kwargs)

    def distribution_files(self):
        # By default Flake8 only runs on packages registered with
        # setuptools.  We want it to look at tests and other things as well
        for d in ['src', 'test', 'build_ext', 'example-plugins', 'setup.py']:
            yield d

    def run(self):
        # Flake8.run(self)  - use when issue 199 is fixed
        # Required until https://gitlab.com/pycqa/flake8/issues/199 is fixed
        self.flake8.run_checks(list(self.distribution_files()))
        self.flake8.formatter.start()
        self.flake8.report_errors()
        self.flake8.report_statistics()
        self.flake8.report_benchmarks()
        self.flake8.formatter.stop()
        self.flake8.exit()
