import os
import six
from tito.tagger.main import VersionTagger
from tito.common import info_out, debug, replace_version, run_command


class MultiPythonPackageVersionTagger(VersionTagger):

    def __init__(self, config=None, *args, **kwargs):
        super(MultiPythonPackageVersionTagger, self).__init__(config=config, *args, **kwargs)
        if config.has_option('tagconfig', 'python_subpackages'):
            self.subpackages = config.get('tagconfig', 'python_subpackages').split(',')
        else:
            self.subpackages = []


    def _update_setup_py_in_dir(self, new_version, package_dir=None):
        """
        If this subdir has a setup.py, attempt to update it's version.
        (This is a very minor tweak to the original _update_setup_py method from VersionTagger
        """

        if package_dir is not None:
            full_package_dir = os.path.join(self.full_project_dir, package_dir)
        else:
            full_package_dir = self.full_project_dir

        setup_file = os.path.join(full_package_dir, "setup.py")
        if not os.path.exists(setup_file):
            return

        debug("Found setup.py in {}, attempting to update version.".format(package_dir))

        # We probably don't want version-release in setup.py as release is
        # an rpm concept. Hopefully this assumption on
        py_new_version = new_version.split('-')[0]

        f = open(setup_file, 'r')
        buf = six.StringIO()
        for line in f.readlines():
            buf.write(replace_version(line, py_new_version))
        f.close()

        # Write out the new setup.py file contents:
        f = open(setup_file, 'w')
        f.write(buf.getvalue())
        f.close()
        buf.close()

        run_command("git add %s" % setup_file)

    def _update_setup_py(self, new_version):
        """
        This overridden method allows us to use one spec file to build multiple
        python packages, each with it's own setup.py file, but sharing a version.
        :param new_version: The version to write to the
        :return:
        """
        self._update_version_file(new_version)

        # Update setup.py in root of the project
        self._update_setup_py_in_dir(new_version)

        # Update setup.py for all subpackages
        for subpackage in self.subpackages:
            self._update_setup_py_in_dir(new_version, package_dir=subpackage)
