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

import gettext
_ = gettext.gettext

from rhsm.certificate2 import EntitlementCertificate, ProductCertificate, IdentityCertificate


class ProductPrinter(object):

    def as_str(self, product):
        s = []
        s.append("%s:" % _("Product"))
        s.append("\t%s: %s" % (_("ID"), product.id))
        s.append("\t%s: %s" % (_("Name"), product.name))
        s.append("\t%s: %s" % (_("Version"), product.version))
        s.append("\t%s: %s" % (_("Arch"), ",".join(product.architectures)))
        s.append("\t%s: %s" % (_("Tags"), ",".join(product.provided_tags)))
        return "%s\n" % '\n'.join(s)


class OrderPrinter(object):

    def as_str(self, order):
        s = []
        s.append("%s:" % _("Order"))
        s.append("\t%s: %s" % (_("Name"), order.name))
        s.append("\t%s: %s" % (_("Number"), order.number))
        s.append("\t%s: %s" % (_("SKU"), order.sku))
        s.append("\t%s: %s" % (_("Contract"), order.contract))
        s.append("\t%s: %s" % (_("Account"), order.account))
        s.append("\t%s: %s" % (_("Service Level"), order.service_level))
        s.append("\t%s: %s" % (_("Service Type"), order.service_type))
        s.append("\t%s: %s" % (_("Quantity"), order.quantity))
        s.append("\t%s: %s" % (_("Quantity Used"), order.quantity_used))
        s.append("\t%s: %s" % (_("Socket Limit"), order.socket_limit))
        s.append("\t%s: %s" % (_("Virt Limit"), order.virt_limit))
        s.append("\t%s: %s" % (_("Virt Only"), order.virt_only))
        s.append("\t%s: %s" % (_("Subscription"), order.subscription))
        s.append("\t%s: %s" % (_("Stacking ID"), order.stacking_id))
        s.append("\t%s: %s" % (_("Warning Period"), order.warning_period))
        s.append("\t%s: %s" % (_("Provides Management"), order.provides_management))

        return "%s\n" % '\n'.join(s)


class ContentPrinter(object):

    def as_str(self, content):
        s = []
        s.append("%s:" % _("Content"))
        s.append("\t%s: %s" % (_("Name"), content.name))
        s.append("\t%s: %s" % (_("Label"), content.label))
        s.append("\t%s: %s" % (_("Vendor"), content.vendor))
        s.append("\t%s: %s" % (_("URL"), content.url))
        s.append("\t%s: %s" % (_("GPG"), content.gpg))
        s.append("\t%s: %s" % (_("Enabled"), content.enabled))
        s.append("\t%s: %s" % (_("Expires"), content.metadata_expire))
        s.append("\t%s: %s" % (_("Required Tags"), ", ".join(content.required_tags)))

        return '\n'.join(s)


class CertificatePrinter(object):

    def cert_to_str(self, cert):
        s = []
        s.append("\n+-------------------------------------------+")
        s.append("\t%s" % self._get_type_str(cert))
        s.append("+-------------------------------------------+\n")
        s.append(_("Certificate:"))
        s.append("\t%s: %s" % (_("Path"), cert.path))
        s.append("\t%s: %s" % (_("Version"), cert.version))
        s.append("\t%s: %s" % (_("Serial"), cert.serial))
        s.append("\t%s: %s" % (_("Start Date"), cert.start))
        s.append("\t%s: %s" % (_("End Date"), cert.end))
        self._append_to_cert_section(cert, s)
        s.append("\n%s" % self._get_subject(cert))
        return "%s" % '\n'.join(s)

    def printc(self, cert):
        print self.cert_to_str(cert)

    def _get_subject(self, cert):
        s = []
        s.append(_("Subject:"))
        for key in sorted(cert.subject):
            s.append("\t%s: %s" % (key, cert.subject[key]))
        return "%s\n" % '\n'.join(s)

    def _get_type_str(self, cert):
        if isinstance(cert, EntitlementCertificate):
            return _("Entitlement Certificate")
        elif isinstance(cert, ProductCertificate):
            return _("Product Certificate")
        elif isinstance(cert, IdentityCertificate):
            return _("Identity Certificate")
        else:
            return _("Unknown Certificate Type")

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
        str_parts_list.append("\t%s: %s" % (_("Alt Name"), cert.alt_name))


class ProductCertificatePrinter(CertificatePrinter):
    def __init__(self, skip_products=False, **kwargs):
        CertificatePrinter.__init__(self)
        self.skip_products = skip_products

    def cert_to_str(self, cert):
        product_printer = ProductPrinter()
        s = []
        if not self.skip_products:
            for product in cert.products:
                s.append(product_printer.as_str(product))

        return "%s\n%s" % (CertificatePrinter.cert_to_str(self, cert), "".join(s))


class EntitlementCertificatePrinter(ProductCertificatePrinter):
    def __init__(self, skip_content=False, skip_products=False):
        ProductCertificatePrinter.__init__(self, skip_products=skip_products)
        self.skip_content = skip_content

    def cert_to_str(self, cert):
        order_printer = OrderPrinter()
        content_printer = ContentPrinter()

        s = []
        if not self.skip_content:
            # sort content by label - makes content easier to read/locate
            sorted_content = sorted(cert.content, key=lambda content: content.label)
            for c in sorted_content:
                s.append("\n%s" % content_printer.as_str(c))

        return "%s\n%s%s" % (ProductCertificatePrinter.cert_to_str(self, cert),
                           order_printer.as_str(cert.order), "\n".join(s))


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


def printc(cert, **kwargs):
    factory = CertificatePrinterFactory()
    printer = factory.get_printer(cert, **kwargs)
    printer.printc(cert)
