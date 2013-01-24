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

import os
import simplejson as json
import shutil
import tempfile
from zipfile import ZipFile
from rhsm import certificate
from rct.commands import RCTCliCommand
from rct.printing import xstr


import gettext
from subscription_manager.cli import InvalidCLIOptionError
_ = gettext.gettext


class RCTManifestCommand(RCTCliCommand):

    INNER_FILE = "consumer_export.zip"

    def __init__(self, name="cli", aliases=[], shortdesc=None, primary=False):
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

    def _extract_manifest(self, location):
        # Extract the outer file
        archive = ZipFile(self._get_file_from_args(), 'r')
        archive.extractall(location)

        # now extract the inner file
        if location:
            inner_file = os.path.join(location, self.INNER_FILE)
        else:
            inner_file = self.INNER_FILE

        archive = ZipFile(inner_file, 'r')
        archive.extractall(location)

        # Delete the intermediate file
        os.remove(inner_file)


class CatManifestCommand(RCTManifestCommand):

    def __init__(self):
        RCTManifestCommand.__init__(self, name="cat-manifest", aliases=['cm'],
                               shortdesc=_("Print manifest information"),
                               primary=True)

    def _print_section(self, title, items, indent=1, whitespace=True):
        # Allow a bit of customization of the tabbing
        pad = ""
        for x in range(0, indent - 1):
            pad = pad + "\t"
        print(pad + title)
        pad = pad + "\t"
        for item in items:
            if len(item) == 2:
                print("%s%s: %s" % (pad, item[0], xstr(item[1])))
            else:
                print("%s%s" % (pad, item[0]))
        if whitespace:
            print ""

    def _print_general(self, location):
        # Print out general data
        part = open(os.path.join(location, "export", "meta.json"))
        data = json.loads(part.read())
        to_print = []
        to_print.append((_("Server"), data["webAppPrefix"]))
        to_print.append((_("Server Version"), data["version"]))
        to_print.append((_("Date Created"), data["created"]))
        to_print.append((_("Creator"), data["principalName"]))
        self._print_section(_("General:"), to_print)
        part.close()

    def _print_consumer(self, location):
        # Print out the consumer data
        part = open(os.path.join(location, "export", "consumer.json"))
        data = json.loads(part.read())
        to_print = []
        to_print.append((_("Name"), data["name"]))
        to_print.append((_("UUID"), data["uuid"]))
        to_print.append((_("Type"), data["type"]["label"]))
        self._print_section(_("Consumer:"), to_print)
        part.close()

    def _get_product_attribute(self, name, data):
        return_value = None
        for attr in data["pool"]["productAttributes"]:
            if attr["name"] == name:
                return_value = attr["value"]
                break

        return return_value

    def _print_products(self, location):
        ent_dir = os.path.join(location, "export", "entitlements")
        for ent_file in os.listdir(ent_dir):
            part = open(os.path.join(ent_dir, ent_file))
            data = json.loads(part.read())
            to_print = []
            to_print.append((_("Name"), data["pool"]["productName"]))
            to_print.append((_("Quantity"), data["quantity"]))
            to_print.append((_("Created"), data["created"]))
            to_print.append((_("Start Date"), data["startDate"]))
            to_print.append((_("End Date"), data["endDate"]))
            to_print.append((_("Suport Level"), self._get_product_attribute("support_level", data)))
            to_print.append((_("Suport Type"), self._get_product_attribute("support_type", data)))
            to_print.append((_("Architectures"), self._get_product_attribute("arch", data)))
            to_print.append((_("Product Id"), data["pool"]["productId"]))
            to_print.append((_("Contract"), data["pool"]["contractNumber"]))
            to_print.append((_("Subscription Id"), data["pool"]["subscriptionId"]))

            entitlement_file = os.path.join("export", "entitlements", "%s.json" % data["id"])
            to_print.append((_("Entitlement File"), entitlement_file))
            #Get the certificate to get the version
            serial = data["certificates"][0]["serial"]["id"]

            cert_file = os.path.join("export", "entitlement_certificates", "%s.pem" % serial)
            to_print.append((_("Certificate File"), cert_file))
            cert_file = os.path.join(location, cert_file)

            try:
                cert = certificate.create_from_file(cert_file)
            except certificate.CertificateException, ce:
                raise certificate.CertificateException(
                        _("Unable to read certificate file '%s': %s") % (cert_file,
                        ce))
            to_print.append((_("Certificate Version"), cert.version))

            self._print_section(_("Subscription:"), to_print, 1, False)

            # Get the provided Products
            to_print = []
            for pp in data["pool"]["providedProducts"]:
                to_print.append((int(pp["productId"]), pp["productName"]))

            self._print_section(_("Provided Products:"), sorted(to_print), 2, False)

            # Get the Content Sets
            to_print = []
            for item in cert.content:
                to_print.append([item.url])
            self._print_section(_("Content Sets:"), sorted(to_print), 2, True)
            part.close()

    def _do_command(self):
        """
        Does the work that this command intends.
        """
        temp = tempfile.mkdtemp()
        self._extract_manifest(temp)
        # Print out the header
        print("\n+-------------------------------------------+")
        print(_("\tManifest"))
        print("+-------------------------------------------+\n")

        self._print_general(temp)
        self._print_consumer(temp)
        self._print_products(temp)

        shutil.rmtree(temp)


class DumpManifestCommand(RCTManifestCommand):

    def __init__(self):
        RCTManifestCommand.__init__(self, name="dump-manifest", aliases=['dm'],
                               shortdesc=_("Dump the contents of a manifest"),
                               primary=True)

        self.parser.add_option("--destination", dest="destination",
                               help=_("directory to extract the manifest to"))

    def _do_command(self):
        """
        Does the work that this command intends.
        """
        self._extract_manifest(self.options.destination)
        if self.options.destination:
            print _("The manifest has been dumped to the %s directory" % self.options.destination)
        else:
            print _("The manifest has been dumped to the current directory")
