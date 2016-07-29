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

from distutils.spawn import spawn
from distutils.text_file import TextFile

from build_ext.utils import Utils, BaseCommand, memoize

# These dependencies aren't available in build environments.  We won't need any
# linting functionality there though, so just create a dummy class so we can proceed.
try:
    import pkg_resources
except ImportError:
    pass

try:
    from flake8.main.setuptools_command import Flake8
except ImportError:
    class Flake8(object):
        def __init__(self, *args, **kwargs):
            raise NotImplementedError("flake8 could not be imported")

try:
    from lxml import etree as ElementTree
except ImportError:
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
    codes = ['X100']

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
                        return (node, "X100 widgets %s are not defined in the Glade files" % list(widgets))


class SignalVisitor(AstVisitor):
    """Look for signals that are used in code but not declared in the Glade files."""
    codes = ['X101']

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
                return (node, "X101 handlers %s are not defined in the Glade files" % list(handlers))


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
