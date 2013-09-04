
import mock

import fixture
import stubs

from subscription_manager import entbranding
from subscription_manager import injection as inj


# never write out the file to disk
class TestBrandInstaller(fixture.SubManFixture):
    def setUp(self):
        super(TestBrandInstaller, self).setUp()
        brand_file_write_patcher = mock.patch("subscription_manager.entbranding.BrandFile.write",
                                              name="MockBrandFile.write")
        self.mock_write = brand_file_write_patcher.start()

        brand_file_read_patcher = mock.patch("subscription_manager.entbranding.BrandFile.read",
                                             return_value="The Artist Previously Known as Awesome OS\n",
                                             name="MockBrandFile.read")
        self.mock_brand_read = brand_file_read_patcher.start()

        mock_install_patcher = mock.patch("subscription_manager.entbranding.BrandInstaller._install_rhel_branding",
                                          name="Mock_installed_rhel_branding")

        self.mock_install = mock_install_patcher.start()

    def tearDown(self):
        super(TestBrandInstaller, self).tearDown()
        self.mock_write.stop()
        self.mock_brand_read.stop()
        self.mock_install.stop()

    def test_init_empty_cert_list(self):
        entbranding.BrandInstaller([])

    def test_no_installed_products_no_ent_certs(self):
        brand_installer = entbranding.BrandInstaller([])
        brand_installer.install()

        self.assertFalse(self.mock_install.called)

    def test_no_ent_certs_installed_products(self):
        prod_dir = stubs.StubProductDirectory(pids=[1, 2, 3, 4, 5])
        inj.provide(inj.PROD_DIR, prod_dir)
        brand_installer = entbranding.BrandInstaller([])
        brand_installer.install()

        self.assertFalse(self.mock_install.called)

    @mock.patch("subscription_manager.entbranding.BrandInstaller.get_branded_certs",
                return_value=[(mock.Mock(), mock.Mock()),
                              (mock.Mock(), mock.Mock())])
    def test_more_than_one_ent_cert_with_branding(self, mock_branded_certs):
        brand_installer = entbranding.BrandInstaller([])
        brand_installer.install()

        self.assertFalse(self.mock_install.called)

    @mock.patch("subscription_manager.entbranding.BrandInstaller.get_branded_certs",
                return_value=[])
    def test_branded_certs_returns_empty(self, mock_branded_certs):

        brand_installer = entbranding.BrandInstaller([])
        brand_installer.install()

        self.assertFalse(self.mock_install.called)

    @mock.patch("subscription_manager.entbranding.BrandInstaller.get_branded_certs",
                return_value=[(mock.Mock(), mock.Mock())])
    def test_branded_certs_current_brand_is_none(self, mock_branded_certs):
        brand_installer = entbranding.BrandInstaller([])
        brand_installer.install()

        self.assertTrue(self.mock_install.called)

    def test(self):
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

        self.mock_install.assert_called_with("Awesome OS Super")

    def test_no_os_on_product(self):

        mock_product = mock.Mock(name='MockProduct')
        mock_product.id = 123
        mock_product.name = "Awesome OS Super"
        del mock_product.os

        mock_prod_dir = mock.NonCallableMock(name='MockProductDir')
        mock_prod_dir.get_installed_products.return_value = [mock_product.id]

        inj.provide(inj.PROD_DIR, mock_prod_dir)

        mock_ent_cert = mock.Mock(name='MockEntCert')
        mock_ent_cert.products = [mock_product]

        brand_installer = entbranding.BrandInstaller([mock_ent_cert])
        brand_installer.install()

        self.assertFalse(self.mock_install.called)

        mock_product.os = 'OS'
        mock_product.name = None

        brand_installer = entbranding.BrandInstaller([mock_ent_cert])
        brand_installer.install()

        self.assertFalse(self.mock_install.called)

    def test_multiple_matching_branded_products(self):
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
        self.assertFalse(self.mock_install.called)

    def test_multiple_branded_ent_certs_for_installed_product(self):
        mock_product = mock.Mock(name='MockProduct')
        mock_product.id = 123
        mock_product.os = 'OS'
        mock_product.name = "Awesome OS Super"

        mock_prod_dir = mock.NonCallableMock(name='MockProductDir')
        mock_prod_dir.get_installed_products.return_value = [mock_product.id]

        inj.provide(inj.PROD_DIR, mock_prod_dir)

        mock_ent_cert = mock.Mock(name='MockEntCert')
        mock_ent_cert.products = [mock_product]

        mock_ent_cert_2 = mock.Mock(name='MockEntCert2')
        mock_ent_cert_2.products = [mock_product]

        brand_installer = entbranding.BrandInstaller([mock_ent_cert, mock_ent_cert_2])
        brand_installer.install()

        #FIXME
        #self.assertTrue(self.mock_install.called)

    def test_is_new_branded_name(self):
        bi = entbranding.BrandInstaller
        # current brand is None we consider always new
        self.assertTrue(bi.is_new_branded_name(None, None))
        # new name is None
        self.assertFalse(bi.is_new_branded_name("Awesome OS", None))
        # if old name doesnt exist, new name is newer
        self.assertTrue(bi.is_new_branded_name(None, "Awesome OS"))
        # name is the same, so not new
        self.assertFalse(bi.is_new_branded_name("Awesome OS", "Awesome OS"))
        # a new branded name
        self.assertTrue(bi.is_new_branded_name("Old Awesome OS", "New Awesome OS"))

    def test_is_rhel_branded_product(self):
        bi = entbranding.BrandInstaller([])

        mock_product = mock.Mock(name='MockProduct')
        mock_product.id = 123
        mock_product.os = 'OS'
        mock_product.name = "Awesome OS Super"
        self.assertTrue(bi._is_rhel_branded_product(mock_product))

        mock_unbranded = mock.Mock(name="MockUnbrandedProduct")
        mock_unbranded.id = 123
        mock_unbranded.os = ""
        mock_unbranded.name = "Awesome OS"
        self.assertFalse(bi._is_rhel_branded_product(mock_unbranded))

        mock_no_os = mock.Mock(name="MockNoOsProduct")
        mock_no_os.id = 123
        del mock_no_os.os
        mock_no_os.name = "Awesome NoOS"
        self.assertFalse(bi._is_rhel_branded_product(mock_no_os))


@mock.patch("subscription_manager.entbranding.BrandFile.write",
            name="MockBrandFile.write")
class TestBrand(fixture.SubManFixture):

    def test_init(self, mock_write):
        entbranding.Brand("Awesome OS")

    def test_brand(self, mock_write):
        brand = entbranding.Brand("Awesome OS")
        self.assertEquals("Awesome OS", brand.name)

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
        self.assertEquals("/var/lib/rhsm/branded_name", entbranding.BrandFile.path)

    def test_write(self):
        brand_file = entbranding.BrandFile()
        mo = mock.mock_open()
        with mock.patch('subscription_manager.entbranding.open', mo, create=True):
            brand_file.write("Foo OS")

        mo.assert_called_once_with('/var/lib/rhsm/branded_name', 'w')
