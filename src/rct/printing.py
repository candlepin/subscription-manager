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
import signal

import six

from rhsm.certificate2 import EntitlementCertificate, ProductCertificate, IdentityCertificate

# BZ 973938 python doesn't correctly handle SIGPIPE
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

from subscription_manager.i18n import ugettext as _


# TODO: to be extra paranoid, we could ask to print
#       the attribute of the object, and handle it
#       not existing at all
def xstr(value):
    if value is None:
        return ''
    elif isinstance(value, six.text_type) and six.PY2:
        return value.encode('utf-8')
    else:
        return str(value)


class ProductPrinter(object):

    def as_str(self, product):
        s = []
        s.append("%s:" % _("Product"))
        s.append("\t%s: %s" % (_("ID"), xstr(product.id)))
        s.append("\t%s: %s" % (_("Name"), xstr(product.name)))
        s.append("\t%s: %s" % (_("Version"), xstr(product.version)))
        s.append("\t%s: %s" % (_("Arch"), ",".join(product.architectures)))
        s.append("\t%s: %s" % (_("Tags"), ",".join(product.provided_tags)))

        brand_type = ""
        if hasattr(product, 'brand_type'):
            brand_type = product.brand_type
        s.append("\t%s: %s" % (_("Brand Type"), xstr(brand_type)))

        brand_name = ""
        if hasattr(product, 'brand_name'):
            brand_name = product.brand_name

        s.append("\t%s: %s" % (_("Brand Name"), xstr(brand_name)))

        return "%s\n" % '\n'.join(s)


class OrderPrinter(object):

    def as_str(self, order):

        if order is None:
            return ''

        s = []
        s.append("%s:" % _("Order"))
        s.append("\t%s: %s" % (_("Name"), xstr(order.name)))
        s.append("\t%s: %s" % (_("Number"), xstr(order.number)))
        s.append("\t%s: %s" % (_("SKU"), xstr(order.sku)))
        s.append("\t%s: %s" % (_("Contract"), xstr(order.contract)))
        s.append("\t%s: %s" % (_("Account"), xstr(order.account)))
        s.append("\t%s: %s" % (_("Service Type"), xstr(order.service_type)))
        s.append("\t%s: %s" % (_("Roles"), xstr(order.roles)))
        s.append("\t%s: %s" % (_("Service Level"), xstr(order.service_level)))
        s.append("\t%s: %s" % (_("Usage"), xstr(order.usage)))
        s.append("\t%s: %s" % (_("Add-ons"), xstr(order.addons)))
        quantity = xstr(order.quantity)
        if quantity == '-1':
            quantity = _('Unlimited')
        s.append("\t%s: %s" % (_("Quantity"), quantity))
        s.append("\t%s: %s" % (_("Quantity Used"), xstr(order.quantity_used)))
        s.append("\t%s: %s" % (_("Socket Limit"), xstr(order.socket_limit)))
        s.append("\t%s: %s" % (_("RAM Limit"), xstr(order.ram_limit)))
        s.append("\t%s: %s" % (_("Core Limit"), xstr(order.core_limit)))
        s.append("\t%s: %s" % (_("Virt Only"), xstr(order.virt_only)))
        s.append("\t%s: %s" % (_("Stacking ID"), xstr(order.stacking_id)))
        s.append("\t%s: %s" % (_("Warning Period"), xstr(order.warning_period)))
        s.append("\t%s: %s" % (_("Provides Management"), xstr(order.provides_management)))

        return "%s\n" % '\n'.join(s)


class ContentPrinter(object):

    def as_str(self, content):
        s = []
        s.append("%s:" % _("Content"))
        # content-type is required, no need to xstr
        s.append("\t%s: %s" % (_("Type"), content.content_type))
        s.append("\t%s: %s" % (_("Name"), xstr(content.name)))
        s.append("\t%s: %s" % (_("Label"), xstr(content.label)))
        s.append("\t%s: %s" % (_("Vendor"), xstr(content.vendor)))
        s.append("\t%s: %s" % (_("URL"), xstr(content.url)))
        s.append("\t%s: %s" % (_("GPG"), xstr(content.gpg)))
        s.append("\t%s: %s" % (_("Enabled"), xstr(content.enabled)))
        s.append("\t%s: %s" % (_("Expires"), xstr(content.metadata_expire)))
        s.append("\t%s: %s" % (_("Required Tags"), ", ".join(content.required_tags)))
        s.append("\t%s: %s" % (_("Arches"), ", ".join(content.arches)))

        return '\n'.join(s)


class CertificatePrinter(object):

    def cert_to_str(self, cert):
        s = []
        s.append("\n+-------------------------------------------+")
        s.append("\t%s" % type_to_string(cert))
        s.append("+-------------------------------------------+\n")
        s.append(_("Certificate:"))
        s.append("\t%s: %s" % (_("Path"), xstr(cert.path)))
        s.append("\t%s: %s" % (_("Version"), xstr(cert.version)))
        s.append("\t%s: %s" % (_("Serial"), xstr(cert.serial)))
        s.append("\t%s: %s" % (_("Start Date"), xstr(cert.start)))
        s.append("\t%s: %s" % (_("End Date"), xstr(cert.end)))
        self._append_to_cert_section(cert, s)
        s.append("\n%s" % xstr(self._get_subject(cert)))
        s.append("%s" % xstr(self._get_issuer(cert)))
        return "%s" % '\n'.join(s)

    def printc(self, cert):
        print(self.cert_to_str(cert))

    def _get_subject(self, cert):
        s = []
        s.append(_("Subject:"))
        for key in sorted(cert.subject):
            s.append("\t%s: %s" % (key, cert.subject[key]))
        return "%s\n" % '\n'.join(s)

    def _get_issuer(self, cert):
        s = []
        s.append(_("Issuer:"))
        for key in sorted(cert.issuer):
            s.append("\t%s: %s" % (key, cert.issuer[key]))
        return "%s\n" % '\n'.join(s)

    def _append_to_cert_section(self, cert, str_parts_list):
        """
        Allows appending to the main 'Certificate:' section
        before printing Subject.
        """
        pass


class IdentityCertPrinter(CertificatePrinter):

    def __init__(self, **kwargs):
        CertificatePrinter.__init__(self)

    def cert_to_str(self, cert):
        return CertificatePrinter.cert_to_str(self, cert)

    def _append_to_cert_section(self, cert, str_parts_list):
        # must account for old format and new
        str_parts_list.append("\t%s: %s" % (_("Alt Name"), cert.alt_name))


class ProductCertificatePrinter(CertificatePrinter):
    def __init__(self, skip_products=False, **kwargs):
        CertificatePrinter.__init__(self)
        self.skip_products = skip_products

    def cert_to_str(self, cert):
        product_printer = ProductPrinter()
        s = []
        if not self.skip_products:
            for product in sorted(cert.products, key=self.product_id_int):
                s.append(product_printer.as_str(product))

        return "%s\n%s" % (CertificatePrinter.cert_to_str(self, cert), "\n".join(s))

    @staticmethod
    def product_id_int(product):
        try:
            return int(product.id)
        except ValueError:
            return product.id


class EntitlementCertificatePrinter(ProductCertificatePrinter):
    def __init__(self, skip_content=False, skip_products=False):
        ProductCertificatePrinter.__init__(self, skip_products=skip_products)
        self.skip_content = skip_content

    def cert_to_str(self, cert):
        order_printer = OrderPrinter()
        content_printer = ContentPrinter()

        s = []
        if not self.skip_content:
            try:
                s.append("\n%s" % xstr(self._get_paths(cert)))
            except AttributeError:
                # v1 certificates won't have this data and some v3 certificates have empty extensions.
                pass

            if cert.content:
                # sort content by label - makes content easier to read/locate
                sorted_content = sorted(cert.content, key=lambda content: content.label)
                for c in sorted_content:
                    s.append("\n%s" % content_printer.as_str(c))

        return "%s\n%s%s" % (ProductCertificatePrinter.cert_to_str(self, cert),
                           order_printer.as_str(cert.order), "\n".join(s))

    def _append_to_cert_section(self, cert, str_parts_list):
        pool_id = _("Not Available")
        if hasattr(cert.pool, "id"):
            pool_id = cert.pool.id
        str_parts_list.append("\t%s: %s" % (_("Pool ID"), pool_id))

    def _get_paths(self, cert):
        s = []
        s.append(_("Authorized Content URLs:"))
        for p in sorted(cert.provided_paths):
            s.append("\t%s" % p)
        return "%s" % '\n'.join(s)


class CertificatePrinterFactory(object):

    def get_printer(self, cert, **kwargs):
        if isinstance(cert, EntitlementCertificate):
            return EntitlementCertificatePrinter(**kwargs)
        elif isinstance(cert, ProductCertificate):
            return ProductCertificatePrinter(**kwargs)
        elif isinstance(cert, IdentityCertificate):
            return IdentityCertPrinter(**kwargs)
        else:
            return CertificatePrinter()


def type_to_string(cert):
    if isinstance(cert, EntitlementCertificate):
        return _("Entitlement Certificate")
    elif isinstance(cert, ProductCertificate):
        return _("Product Certificate")
    elif isinstance(cert, IdentityCertificate):
        return _("Identity Certificate")
    else:
        return _("Unknown Certificate Type")


def printc(cert, **kwargs):
    factory = CertificatePrinterFactory()
    printer = factory.get_printer(cert, **kwargs)
    printer.printc(cert)
