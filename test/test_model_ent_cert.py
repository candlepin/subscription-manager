
import mock

import fixture

import test_model

from rhsm import certificate2
from subscription_manager import model
from subscription_manager.model import ent_cert
from subscription_manager import injection as inj


class TestEntitlement(fixture.SubManFixture):
    def test_empty_init(self):
        e = model.Entitlement()
        self.assertTrue(hasattr(e, 'contents'))

    def test_init_empty_contents(self):
        e = model.Entitlement(contents=[])
        self.assertTrue(hasattr(e, 'contents'))
        self.assertEqual(e.contents, [])

    def test_contents(self):
        contents = [mock.Mock(), mock.Mock()]
        e = model.Entitlement(contents=contents)
        self.assertTrue(hasattr(e, 'contents'))
        self.assertEqual(len(e.contents), 2)

        for a_content in e.contents:
            self.assertTrue(isinstance(a_content, mock.Mock))

        self.assertTrue(isinstance(e.contents[0], mock.Mock))


def create_mock_content(name=None, url=None, gpg=None, enabled=None, content_type=None, tags=None):
    mock_content = mock.Mock()
    mock_content.name = name or "mock_content"
    mock_content.url = url or "http://mock.example.com"
    mock_content.gpg = gpg or "path/to/gpg"
    mock_content.enabled = enabled or True
    mock_content.content_type = content_type or "yum"
    mock_content.tags = tags or []
    return mock_content


class TestEntitlementCertContent(test_model.TestContent):
    def test_from_cert_content_yum(self):
        mock_content = create_mock_content()

        ent_cert_content = ent_cert.EntitlementCertContent.from_cert_content(mock_content)
        self._check_attrs(ent_cert_content)

    def test_from_cert_content_ostree(self):
        mock_content = create_mock_content(content_type="ostree")

        ent_cert_content = ent_cert.EntitlementCertContent.from_cert_content(mock_content)
        self._check_attrs(ent_cert_content)

    def test_from_cert_content_ostree_tags(self):
        mock_content = create_mock_content(content_type="ostree", tags=["rhel-7-atomic"])

        ent_cert_content = ent_cert.EntitlementCertContent.from_cert_content(mock_content)
        self._check_attrs(ent_cert_content)


class TestEntitlementCertEntitlement(TestEntitlement):
    def test_from_ent_cert(self):
        mock_content = create_mock_content()

        contents = [mock_content]

        mock_ent_cert = mock.Mock()
        mock_ent_cert.content = contents

        ece = model.ent_cert.EntitlementCertEntitlement.from_ent_cert(mock_ent_cert)

        self.assertEqual(ece.contents[0].name, contents[0].name)
        self.assertEqual(ece.contents[0].label, contents[0].label)
        self.assertEqual(ece.contents[0].gpg, contents[0].gpg)
        self.assertEqual(ece.contents[0].content_type,
            contents[0].content_type)
        self.assertEqual(len(ece.contents), 1)

        # for ostree content, gpg is likely to change
        self.assertEqual(ece.contents[0].gpg, mock_content.gpg)


# FIXME: move to stubs/fixture, copied from ent_branding
# The installed product ids don't have brand_type/brand_name, just the
# Product from the ent cert
class DefaultStubInstalledProduct(certificate2.Product):
    def __init__(self, id=123, name="Awesome OS",
                 provided_tags=None,
                 brand_type=None, brand_name=None):

        tags = provided_tags or ["awesomeos-ostree-1"]
        super(DefaultStubInstalledProduct, self).__init__(id=id, name=name, provided_tags=tags,
                                                          brand_type=brand_type,
                                                          brand_name=brand_name)


class TestEntitlementDirEntitlementSource(test_model.TestEntitlementSource):
    def setUp(self):
        super(TestEntitlementDirEntitlementSource, self).setUp()
        self._inj_mock_dirs()

    def _inj_mock_dirs(self, stub_product=None):

        stub_product = stub_product or DefaultStubInstalledProduct()
        mock_prod_dir = mock.NonCallableMock(name='MockProductDir')
        mock_prod_dir.get_installed_products.return_value = [stub_product.id]
        mock_prod_dir.get_provided_tags.return_value = stub_product.provided_tags

        mock_content = create_mock_content(tags=['awesomeos-ostree-1'])
        mock_cert_contents = [mock_content]

        mock_ent_cert = mock.Mock(name='MockEntCert')
        mock_ent_cert.products = [stub_product]
        mock_ent_cert.content = mock_cert_contents

        mock_ent_dir = mock.NonCallableMock(name='MockEntDir')
        mock_ent_dir.list_valid.return_value = [mock_ent_cert]
        mock_ent_dir.list_valid_with_content_access.return_value = [mock_ent_cert]

        inj.provide(inj.PROD_DIR, mock_prod_dir)
        inj.provide(inj.ENT_DIR, mock_ent_dir)

    def _stub_product(self):
        return DefaultStubInstalledProduct

    def test_init_no_matching(self):
        # add a product that will not match product tags
        self._inj_mock_dirs(stub_product=DefaultStubInstalledProduct(provided_tags=[]))
        ecc = ent_cert.EntitlementDirEntitlementSource()
        self.assertEqual(len(ecc), 1)
        self.assertEqual(len(ecc.product_tags), 1)
