from __future__ import print_function, division, absolute_import

#
# Copyright (c) 2010 - 2012 Red Hat, Inc.
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
import errno
import os
import sys

from six import BytesIO
from zipfile import ZipFile, BadZipfile

from rhsm import certificate

from rct.commands import RCTCliCommand
from rct.printing import xstr
from subscription_manager.cli import InvalidCLIOptionError
from rhsm import ourjson as json

from subscription_manager.i18n import ugettext as _


def get_value(json_dict, path):
    current = json_dict
    for item in path.split("."):
        if item in current:
            current = current[item]
        else:
            return ""

    return current


class ZipExtractAll(ZipFile):
    """extend ZipFile with a safer extractall

    Zipfile() does not support extractall on python2.4, and the 2.6 versions
    are known to be unsafe in how they extract files. 2.6 version does not
    validate that files are within the archive root, or check that files are
    created safely.

    Contains helper methods for manipulating and reading
    the zipfile more easily in memory"""

    inner_zip = None

    def __init__(self, *args, **kwargs):
        """
        Validates the zip file
        """
        try:
            ZipFile.__init__(self, *args, **kwargs)
        except BadZipfile:
            print(_("Manifest zip is invalid."))
            sys.exit(1)

    def _get_inner_zip(self):
        if self.inner_zip is None:
            output = BytesIO(self.read(RCTManifestCommand.INNER_FILE))
            self.inner_zip = ZipExtractAll(output, 'r')
        return self.inner_zip

    def _read_file(self, file_path, is_inner=False):
        try:
            output = BytesIO(self.read(file_path))
            result = output.getvalue()
            output.close()
        except KeyError:
            try:
                if is_inner:
                    raise KeyError
                result = self._get_inner_zip()._read_file(file_path, True)
            except KeyError:
                raise Exception(_('Unable to find file "%s" in manifest.') % file_path)
        return result

    def _get_entitlements(self):
        results = []
        in_zip = self._get_inner_zip()
        for filename in in_zip.namelist():
            (read_path, read_file) = os.path.split(filename)
            if (read_path == os.path.join("export", "entitlements")) and (len(read_file) > 0):
                results.append(filename)
        return results

    def _open_excl(self, path):
        return os.fdopen(os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL), 'wb')

    def _write_file(self, output_path, archive_path):
        outfile = self._open_excl(output_path)
        outfile.write(self.read(archive_path))
        outfile.close()

    def _is_secure(self, base, new_file):
        base_path = os.path.abspath(base)
        new_path = os.path.abspath(new_file)
        if not new_path.startswith(base_path):
            raise Exception(_('Manifest zip attempted to extract outside of the base directory.'))
        #traces symlink to source, and checks that it is valid
        real_new_path = os.path.realpath(new_path)
        if real_new_path != new_path:
            self._is_secure(base, real_new_path)
        elif os.path.islink(new_path):
            raise Exception(_('Unable to trace symbolic link.  Possibly circular linkage.'))

    def extractall(self, location, overwrite=False):
        self._is_secure(location, location)
        for path_name in self.namelist():
            (directory, filename) = os.path.split(path_name)
            directory = os.path.join(location, directory)
            self._is_secure(location, directory)
            if not os.path.exists(directory):
                os.makedirs(directory)
            new_location = os.path.join(directory, filename)
            self._is_secure(location, new_location)
            if (os.path.exists(new_location) and overwrite):
                os.remove(new_location)
            self._write_file(new_location, path_name)


class RCTManifestCommand(RCTCliCommand):

    INNER_FILE = "consumer_export.zip"

    def __init__(self, name="cli", aliases=None, shortdesc=None, primary=False):
        RCTCliCommand.__init__(self, name=name, aliases=aliases,
                shortdesc=shortdesc, primary=primary)

    def _get_usage(self):
        return _("%%prog %s [OPTIONS] MANIFEST_FILE") % self.name

    def _validate_options(self):
        manifest_file = self._get_file_from_args()
        if not manifest_file:
            raise InvalidCLIOptionError(_("You must specify a manifest file."))

        if not os.path.isfile(manifest_file):
            raise InvalidCLIOptionError(_("The specified manifest file does not exist."))

    def _extract_manifest(self, location, overwrite=False):
        # Extract the outer file
        archive = ZipExtractAll(self._get_file_from_args(), 'r')
        archive.extractall(location, overwrite)

        # now extract the inner file
        if location:
            inner_file = os.path.join(location, self.INNER_FILE)
        else:
            inner_file = self.INNER_FILE

        archive = ZipExtractAll(inner_file, 'r')
        archive.extractall(location, overwrite)

        # Delete the intermediate file
        os.remove(inner_file)


class CatManifestCommand(RCTManifestCommand):

    def __init__(self):
        RCTManifestCommand.__init__(self, name="cat-manifest", aliases=['cm'],
                               shortdesc=_("Print manifest information"),
                               primary=True)
        self.parser.add_option("--no-content", action="store_true",
                               default=False,
                               help=_("skip printing Content Sets"))

    def _print_section(self, title, items, indent=1, whitespace=True):
        # Allow a bit of customization of the tabbing
        pad = "\t" * (indent - 1)
        print(pad + title)
        pad += "\t"
        for item in items:
            if len(item) == 2:
                print("%s%s: %s" % (pad, item[0], xstr(item[1])))
            else:
                print("%s%s" % (pad, item[0]))
        if whitespace:
            print("")

    def _print_general(self, zip_archive):
        # Print out general data
        part = zip_archive._read_file(os.path.join("export", "meta.json"))
        data = json.loads(part)
        to_print = []
        to_print.append((_("Server"), get_value(data, "webAppPrefix")))
        to_print.append((_("Server Version"), get_value(data, "version")))
        to_print.append((_("Date Created"), get_value(data, "created")))
        to_print.append((_("Creator"), get_value(data, "principalName")))
        self._print_section(_("General:"), to_print)

    def _print_consumer(self, zip_archive):
        # Print out the consumer data
        part = zip_archive._read_file(os.path.join("export", "consumer.json"))
        data = json.loads(part)
        to_print = []
        to_print.append((_("Name"), get_value(data, "name")))
        to_print.append((_("UUID"), get_value(data, "uuid")))
        # contentAccessMode is entitlement if null, blank or non-present
        contentAccessMode = 'entitlement'
        if "contentAccessMode" in data and data["contentAccessMode"] == 'org_environment':
            contentAccessMode = 'org_environment'
        to_print.append((_("Content Access Mode"), contentAccessMode))
        to_print.append((_("Type"), get_value(data, "type.label")))
        to_print.append((_("API URL"), get_value(data, "urlApi")))
        to_print.append((_("Web URL"), get_value(data, "urlWeb")))
        self._print_section(_("Consumer:"), to_print)

    def _get_product_attribute(self, name, data):
        return_value = None
        for attr in get_value(data, "pool.productAttributes"):
            if attr["name"] == name:
                return_value = attr["value"]
                break

        return return_value

    def _print_products(self, zip_archive):
        entitlements = zip_archive._get_entitlements()
        if len(entitlements) == 0:
            self._print_section(_("Subscriptions:"), [["None"]], 1, True)
            return

        for ent_file in entitlements:
            part = zip_archive._read_file(ent_file)
            data = json.loads(part)
            to_print = []
            to_print.append((_("Name"), get_value(data, "pool.productName")))
            to_print.append((_("Quantity"), get_value(data, "quantity")))
            to_print.append((_("Created"), get_value(data, "created")))
            to_print.append((_("Start Date"), get_value(data, "startDate")))
            to_print.append((_("End Date"), get_value(data, "endDate")))
            to_print.append((_("Service Level"), self._get_product_attribute("support_level", data)))
            to_print.append((_("Service Type"), self._get_product_attribute("support_type", data)))
            to_print.append((_("Architectures"), self._get_product_attribute("arch", data)))
            to_print.append((_("SKU"), get_value(data, "pool.productId")))
            to_print.append((_("Contract"), get_value(data, "pool.contractNumber")))
            to_print.append((_("Order"), get_value(data, "pool.orderNumber")))
            to_print.append((_("Account"), get_value(data, "pool.accountNumber")))
            virt_limit = self._get_product_attribute("virt_limit", data)
            to_print.append((_("Virt Limit"), virt_limit))
            require_virt_who = False
            if virt_limit:
                require_virt_who = True
            to_print.append((_("Requires Virt-who"), require_virt_who))

            entitlement_file = os.path.join("export", "entitlements", "%s.json" % data["id"])
            to_print.append((_("Entitlement File"), entitlement_file))
            #Get the certificate to get the version
            serial = data["certificates"][0]["serial"]["id"]

            cert_file = os.path.join("export", "entitlement_certificates", "%s.pem" % serial)
            to_print.append((_("Certificate File"), cert_file))

            try:
                cert = certificate.create_from_pem(zip_archive._read_file(cert_file).decode('utf-8'))
            except certificate.CertificateException as ce:
                raise certificate.CertificateException(
                        _("Unable to read certificate file '%s': %s") % (cert_file,
                        ce))
            to_print.append((_("Certificate Version"), cert.version))

            self._print_section(_("Subscription:"), to_print, 1, False)

            # Get the provided Products
            to_print = [(int(pp["productId"]), pp["productName"]) for pp in data["pool"]["providedProducts"]]

            self._print_section(_("Provided Products:"), sorted(to_print), 2, False)

            # Get the derived provided Products (if available)
            if "derivedProvidedProducts" in data["pool"]:
                to_print = [(int(pp["productId"]), pp["productName"]) for pp in data["pool"]["derivedProvidedProducts"]]
                self._print_section(_("Derived Products:"), sorted(to_print), 2, False)

            # Get the Content Sets
            if not self.options.no_content:
                to_print = [[item.url] for item in cert.content]
                self._print_section(_("Content Sets:"), sorted(to_print), 2, True)
            else:  # bz#1369577: print a blank line to separate subscriptions when --no-content in use
                print("")

    def _do_command(self):
        """
        Does the work that this command intends.
        """
        temp = ZipExtractAll(self._get_file_from_args(), 'r')
        # Print out the header
        print("\n+-------------------------------------------+")
        print(_("\tManifest"))
        print("+-------------------------------------------+\n")

        self._print_general(temp)
        self._print_consumer(temp)
        self._print_products(temp)


class DumpManifestCommand(RCTManifestCommand):

    def __init__(self):
        RCTManifestCommand.__init__(self, name="dump-manifest", aliases=['dm'],
                               shortdesc=_("Dump the contents of a manifest"),
                               primary=True)

        self.parser.add_option("--destination", dest="destination",
                               help=_("directory to extract the manifest to"))
        self.parser.add_option("-f", "--force", action="store_true",
                               dest="overwrite_files", default=False,
                               help=_("overwrite files which may exist"))

    def _extract(self, destination, overwrite):
        try:
            self._extract_manifest(destination, overwrite)
        except EnvironmentError as e:
            # IOError/OSError base class
            if e.errno == errno.EEXIST:
                # useful error for file already exists
                print(_('File "%s" exists. Use -f to force overwriting the file.') % e.filename)
            else:
                # generic error for everything else
                print(_("Manifest could not be written:"))
                print(e.strerror)
                if e.filename:
                    print(e.filename)
            return False
        return True

    def _do_command(self):
        """
        Does the work that this command intends.
        """
        if self.options.destination:
            if self._extract(self.options.destination, self.options.overwrite_files):
                print(_("The manifest has been dumped to the %s directory") % self.options.destination)
        else:
            if self._extract(os.getcwd(), self.options.overwrite_files):
                print(_("The manifest has been dumped to the current directory"))
