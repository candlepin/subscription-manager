import os
import subprocess

from tito.builder.main import Builder
from tito.common import info_out

class ScriptBuilder(Builder):
    """Builder that also runs a script to produce one or more additional tarballs.

    This Builder looks for lines ending in '.tar.gz' in the output of the script, and treats
    those as artifacts of the script.
    """
    def __init__(self, config=None, *args, **kwargs):
        super(ScriptBuilder, self).__init__(config=config, *args, **kwargs)
        if not config.has_option('buildconfig', 'script_builder_script'):
            raise ValueError('Must specify "script_builder_script" property in tito.props')
        self.script = config.get('buildconfig', 'script_builder_script')
        self.tarballs_from_script = []

    def normalize_tarball(self, path):
        destination_file = os.path.join(self.rpmbuild_sourcedir, path)
        if not path.endswith('%s.tar.gz' % self.display_version):
            basename = os.path.basename(path.split('.tar.gz')[0])
            fixed_name = '%s-%s.tar.gz' % (basename, self.display_version)
            destination_file = os.path.join(self.rpmbuild_sourcedir, fixed_name)
            subprocess.check_call('mv %s %s' % (path, destination_file), shell=True)
        subprocess.check_call("cp %s %s/" % (destination_file, self.rpmbuild_basedir), shell=True)
        info_out('Wrote: %s/%s' % (self.rpmbuild_basedir, os.path.basename(destination_file)))
        self.tarballs_from_script.append(destination_file)
        return os.path.join(os.getcwd(), destination_file)

    def tgz(self):
        retval = Builder.tgz(self)
        os.chdir(self.rpmbuild_gitcopy)
        if not os.path.exists(self.script):
            return retval

        if hasattr(subprocess, 'check_output'):
            try:
                output = subprocess.check_output(self.script, shell=True).decode('utf-8')
            except subprocess.CalledProcessError as e:
                print(e.output.decode('utf-8'))
                raise
        else:
            print("Running script_builder_script ...")
            # Run command in subprocess
            process = subprocess.Popen(self.script, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # Print output of command
            output = ""
            for line in process.stdout.readlines():
                output += line
            retval = process.wait()

        print(output)
        additional_tgz = []
        for line in output.split('\n'):
            if line.endswith('.tar.gz'):
                additional_tgz.append(line.strip())
        additional_tgz = [self.normalize_tarball(tgz) for tgz in additional_tgz]
        self.sources += additional_tgz
        self.artifacts += additional_tgz
        return retval

    def _setup_test_specfile(self):
        """Augment parent behavior, also munge Source1 through SourceN where N is the number of tarballs produced by the script."""
        Builder._setup_test_specfile(self)
        if self.test:
            for i, tarball_from_script in enumerate(self.tarballs_from_script):
                num = i + 1
                basename = os.path.basename(tarball_from_script)
                subprocess.call('sed -i "s#Source%s: .*#Source%s: %s#" %s' % (num, num, basename, self.spec_file), shell=True)
