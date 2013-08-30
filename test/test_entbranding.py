
import mock

import fixture
import stubs

from subscription_manager import entbranding
from subscription_manager import injection as inj


# never write out the file to disk
@mock.patch("subscription_manager.entbranding.BrandFile.write",
            name="MockBrandFile.write")
@mock.patch("subscription_manager.entbranding.BrandInstaller._install_rhel_branding",
            name="Mock_installed_rhel_branding")
class TestBrandInstaller(fixture.SubManFixture):
    def test_init_empty_cert_list(self, mock_install, mock_write):
        entbranding.BrandInstaller([])

    def test_no_installed_products_no_ent_certs(self, mock_install, mock_write):
        brand_installer = entbranding.BrandInstaller([])
        brand_installer.install()

        self.assertFalse(mock_install.called)

    def test_no_ent_certs_installed_products(self, mock_install, mock_write):
        prod_dir = stubs.StubProductDirectory(pids=[1, 2, 3, 4, 5])
        inj.provide(inj.PROD_DIR, prod_dir)
        brand_installer = entbranding.BrandInstaller([])
        brand_installer.install()

        self.assertFalse(mock_install.called)

    @mock.patch("subscription_manager.entbranding.BrandInstaller.get_branded_certs",
                return_value=[mock.Mock(), mock.Mock()])
    def test_more_than_one_ent_cert_with_branding(self, mock_branded_certs, mock_install, mock_write):
        brand_installer = entbranding.BrandInstaller([])
        brand_installer.install()

        self.assertFalse(mock_install.called)

    @mock.patch("subscription_manager.entbranding.BrandInstaller.get_branded_certs",
                return_value=[])
    def test_branded_certs_returns_empty(self, mock_branded_certs, mock_install, mock_write):
        brand_installer = entbranding.BrandInstaller([])
        brand_installer.install()

        self.assertFalse(mock_install.called)

    def test(self, mock_install, mock_write):
        mock_product = mock.Mock(name='MockProduct')
        mock_product.id = 123
        mock_product.os = 'OS'
        mock_product.name = "Awesome OS Super"

        mock_prod_dir = mock.NonCallableMock(name='MockProductDir')
        mock_prod_dir.get_installed_products.return_value = [mock_product.id]

        inj.provide(inj.PROD_DIR, mock_prod_dir)

        mock_ent_cert = mock.Mock(name='MockEntCert')
        mock_ent_cert.products = [mock_product]

        brand_installer = entbranding.BrandInstaller([mock_ent_cert])
        brand_installer.install()

        mock_install.assert_called_with("Awesome OS Super")

    def test_multiple_matching_branded_products(self, mock_install, mock_write):
        mock_product = mock.Mock(name='MockProduct')
        mock_product.id = 123
        mock_product.os = 'OS'
        mock_product.name = "Awesome OS Super"

        mock_product_2 = mock.Mock(name='MockProduct2')
        mock_product_2.id = 321
        mock_product_2.os = 'OS'
        mock_product_2.name = "Slightly Different Awesome OS Super"

        mock_prod_dir = mock.NonCallableMock(name='MockProductDir')
        mock_prod_dir.get_installed_products.return_value = [mock_product.id, mock_product_2.id]

        inj.provide(inj.PROD_DIR, mock_prod_dir)

        mock_ent_cert = mock.Mock(name='MockEntCert')
        mock_ent_cert.products = [mock_product, mock_product_2]

        brand_installer = entbranding.BrandInstaller([mock_ent_cert])
        brand_installer.install()

        # we give up in this case and leave things as is
        self.assertFalse(mock_install.called)


@mock.patch("subscription_manager.entbranding.BrandFile.write",
            name="MockBrandFile.write")
class TestBrand(fixture.SubManFixture):

    def test_init(self, mock_write):
        entbranding.Brand("Awesome OS")

    def test_brand(self, mock_write):
        brand = entbranding.Brand("Awesome OS")
        self.assertEquals("Awesome OS", brand.brand)

    def test_brand_save(self, mock_write):
        brand = entbranding.Brand("Foo")
        brand.save()
        mock_write.assert_called_with("Foo\n")

    def test_format_brand(self, mock_write):
        fb = entbranding.Brand.format_brand('Blip')
        self.assert_string_equals(fb, 'Blip\n')

        fb = entbranding.Brand.format_brand('')
        self.assert_string_equals(fb, '\n')


class TestBrandFile(fixture.SubManFixture):

    def test_init(self):
        entbranding.BrandFile()
        self.assertEquals("/var/lib/rhsm/branded_name", entbranding.BrandFile.brand_path)

    def test_write(self):
        brand_file = entbranding.BrandFile()
        mo = mock.mock_open()
        with mock.patch('subscription_manager.entbranding.open', mo, create=True):
            brand_file.write("Foo OS")

        mo.assert_called_once_with('/var/lib/rhsm/branded_name', 'w')
