
import mock

import fixture
import stubs

from subscription_manager import entbranding
from subscription_manager import injection as inj


class BaseBrandFixture(fixture.SubManFixture):
    current_brand = "Current Awesome OS Brand"

    def setUp(self):
        super(BaseBrandFixture, self).setUp()
        brand_file_write_patcher = mock.patch("subscription_manager.entbranding.BrandFile.write",
                                              name="MockBrandFile.write")
        self.mock_write = brand_file_write_patcher.start()

        brand_file_read_patcher = mock.patch("subscription_manager.entbranding.BrandFile.read",
                                             return_value="%s\n" % self.current_brand,
                                             name="MockBrandFile.read")
        self.mock_brand_read = brand_file_read_patcher.start()

        mock_install_patcher = mock.patch("subscription_manager.entbranding.BrandInstaller._install",
                                          name="Mock_install_branding")

        self.mock_install = mock_install_patcher.start()

    def tearDown(self):
        super(BaseBrandFixture, self).tearDown()
        self.mock_write.stop()
        self.mock_brand_read.stop()
        self.mock_install.stop()


# never write out the file to disk
class TestBrandInstaller(BaseBrandFixture):

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

        self.assertTrue(self.mock_install.called)
        call_args = self.mock_install.call_args
        brand_arg = call_args[0][0]
        self.assertTrue(isinstance(brand_arg, entbranding.ProductBrand))
        self.assertEquals("Awesome OS Super", brand_arg.name)

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


class TestBrand(fixture.SubManFixture):
    def test_no_no(self):
        current_brand = entbranding.Brand()
        product_brand = entbranding.Brand()
        # current brand and product none/unset
        self.assertTrue(current_brand.is_outdated_by(product_brand))

    def test_product_brand_none(self):
        # new name is None, so newer consumer > current
        current_brand = entbranding.Brand()
        current_brand.name = "Awesome OS"
        product_brand = entbranding.Brand()
        product_brand.name = None
        self.assertFalse(current_brand.is_outdated_by(product_brand))

    def test_no_current_name(self):
        # if old name doesnt exist, new name is newer
        current_brand = entbranding.Brand()
        product_brand = entbranding.Brand()
        product_brand.name = "Awesome OS"
        self.assertTrue(current_brand.is_outdated_by(product_brand))

    def test_same(self):
        # name is the same, so not new
        current_brand = entbranding.Brand()
        current_brand.name = "Awesome OS"
        product_brand = entbranding.Brand()
        product_brand.name = "Awesome OS"
        self.assertFalse(current_brand.is_outdated_by(product_brand))

    def test_product_name_ne_current_name(self):
        # a new branded name
        current_brand = entbranding.Brand()
        current_brand.name = "Awesome OS"
        product_brand = entbranding.Brand()
        product_brand.name = "New Awesome OS"

        self.assertTrue(current_brand.is_outdated_by(product_brand))


class TestProductBrandPicker(BaseBrandFixture):
    @mock.patch("subscription_manager.entbranding.BrandPicker._get_branded_certs",
                return_value=[(mock.Mock(), mock.Mock()),
                              (mock.Mock(), mock.Mock())])
    def test_more_than_one_ent_cert_with_branding(self, mock_branded_certs):
        brand_picker = entbranding.BrandPicker([])
        brand = brand_picker.get_brand()
        self.assertEquals(None, brand)

    @mock.patch("subscription_manager.entbranding.BrandPicker._get_branded_certs",
                return_value=[])
    def test_branded_certs_returns_empty(self, mock_branded_certs):

        brand_picker = entbranding.BrandPicker([])
        brand = brand_picker.get_brand()

        self.assertEquals(None, brand)

    def test_get_brand(self):
        # inj a prod dir with some installed products
        mock_product = mock.Mock(id=123)
        mock_product.name = "Mock Product"
        mock_product.os = "OS"

        mock_product_dir = mock.NonCallableMock()
        mock_product_dir.get_installed_products.return_value = [mock_product.id]
        inj.provide(inj.PROD_DIR, mock_product_dir)

        mock_ent_cert = mock.Mock()
        mock_ent_cert.products = [mock_product]
        ent_certs = [mock_ent_cert]

        brand_picker = entbranding.BrandPicker(ent_certs)
        brand = brand_picker.get_brand()
        self.assertTrue("Mock Product", brand.name)

    def test_get_brand_multiple_ents_with_branding_same_name(self):
        # inj a prod dir with some installed products
        mock_product = mock.Mock(id=123)
        mock_product.name = "Mock Product"
        mock_product.os = "OS"

        mock_product_dir = mock.NonCallableMock()
        mock_product_dir.get_installed_products.return_value = [mock_product.id]
        inj.provide(inj.PROD_DIR, mock_product_dir)

        mock_ent_cert = mock.Mock()
        mock_ent_cert.products = [mock_product]

        mock_ent_cert_2 = mock.Mock()
        mock_ent_cert_2.products = [mock_product]
        ent_certs = [mock_ent_cert, mock_ent_cert_2]

        brand_picker = entbranding.BrandPicker(ent_certs)
        brand = brand_picker.get_brand()
        self.assertFalse("Mock Product", brand.name)

    def test_get_brand_multiple_ents_with_branding_different_branded_name(self):
        # inj a prod dir with some installed products
        mock_product = mock.Mock(id=123)
        mock_product.name = "Mock Product"
        mock_product.os = "OS"

        # same product id, different name
        mock_product_2 = mock.Mock(id=123)
        mock_product_2.name = "Different Mock Product"
        mock_product.os = "OS"

        mock_product_dir = mock.NonCallableMock()
        # note mock_product.id=123 will match the Product from both ents
        mock_product_dir.get_installed_products.return_value = [mock_product.id]
        inj.provide(inj.PROD_DIR, mock_product_dir)

        mock_ent_cert = mock.Mock()
        mock_ent_cert.products = [mock_product]

        mock_ent_cert_2 = mock.Mock()
        mock_ent_cert_2.products = [mock_product_2]
        ent_certs = [mock_ent_cert, mock_ent_cert_2]

        brand_picker = entbranding.BrandPicker(ent_certs)
        brand = brand_picker.get_brand()
        self.assertFalse("Mock Product", brand.name)

    def test_get_brand_not_installed(self):

        mock_product = mock.Mock(id=123)
        mock_product.name = "Mock Product"
        mock_product.os = "OS"

        mock_other_product = mock.Mock(id=321)
        mock_other_product.name = "A Non Branded Product"

        mock_product_dir = mock.NonCallableMock()
        mock_product_dir.get_installed_products.return_value = [mock_other_product.id]
        inj.provide(inj.PROD_DIR, mock_product_dir)

        mock_ent_cert = mock.Mock()
        mock_ent_cert.products = [mock_product]
        ent_certs = [mock_ent_cert]

        brand_picker = entbranding.BrandPicker(ent_certs)
        brand = brand_picker.get_brand()
        self.assertTrue(brand is None)

    def test_get_brand_branded(self):

        mock_product = mock.Mock(id=123)
        mock_product.name = "Mock Product"
        mock_product.os = "Awesome Middleware"

        mock_other_product = mock.Mock(id=321)
        mock_other_product.name = "A Non Branded Product"

        mock_product_dir = mock.NonCallableMock()
        mock_product_dir.get_installed_products.return_value = [mock_product.id, mock_other_product.id]
        inj.provide(inj.PROD_DIR, mock_product_dir)

        mock_ent_cert = mock.Mock()
        mock_ent_cert.products = [mock_product]
        ent_certs = [mock_ent_cert]

        brand_picker = entbranding.BrandPicker(ent_certs)
        brand = brand_picker.get_brand()
        self.assertTrue(brand is None)

    def test_is_installed_rhel_branded_product_not_installed(self):
        brand_picker = entbranding.BrandPicker([])
        mock_product = mock.Mock(id=123)
        irp = brand_picker._is_installed_rhel_branded_product(mock_product)
        self.assertFalse(irp)

    def test_is_installed_rhel_branded_product_is_installed(self):
        mock_product = mock.Mock(id=123)
        mock_product.name = "Mock Product"

        mock_product_dir = mock.NonCallableMock()
        mock_product_dir.get_installed_products.return_value = [mock_product.id]
        inj.provide(inj.PROD_DIR, mock_product_dir)

        brand_picker = entbranding.BrandPicker([])
        irp = brand_picker._is_installed_rhel_branded_product(mock_product)
        self.assertTrue(irp)

    def test_get_installed_branded_products(self):
        mock_product = mock.Mock(id=123)
        mock_product.name = "Mock Product"

        mock_product_dir = mock.NonCallableMock()
        mock_product_dir.get_installed_products.return_value = [mock_product.id]
        inj.provide(inj.PROD_DIR, mock_product_dir)

        brand_picker = entbranding.BrandPicker([])
        irp = brand_picker._is_installed_rhel_branded_product(mock_product)
        self.assertTrue(irp)

    def test_is_rhel_branded_product(self):
        brand_picker = entbranding.BrandPicker([])

        mock_product = mock.Mock(name='MockProduct')
        mock_product.id = 123
        mock_product.os = 'OS'
        mock_product.name = "Awesome OS Super"
        self.assertTrue(brand_picker._is_rhel_branded_product(mock_product))

        mock_unbranded = mock.Mock(name="MockUnbrandedProduct")
        mock_unbranded.id = 123
        mock_unbranded.os = ""
        mock_unbranded.name = "Awesome OS"
        self.assertFalse(brand_picker._is_rhel_branded_product(mock_unbranded))

        mock_no_os = mock.Mock(name="MockNoOsProduct")
        mock_no_os.id = 123
        del mock_no_os.os
        mock_no_os.name = "Awesome NoOS"
        self.assertFalse(brand_picker._is_rhel_branded_product(mock_no_os))


class TestProductBrand(BaseBrandFixture):

    def test_init(self):
        entbranding.ProductBrand("Awesome OS")

    def test_brand(self):
        brand = entbranding.ProductBrand("Awesome OS")
        self.assertEquals("Awesome OS", brand.name)

    def test_brand_save(self):
        brand = entbranding.ProductBrand("Foo")
        brand.save()
        self.mock_write.assert_called_with("Foo\n")

    def test_exception_on_save(self):
        self.mock_write.side_effect = IOError
        brand = entbranding.ProductBrand("Foo")
        self.assertRaises(IOError, brand.save)

    def test_from_product(self):
        product_name = "Awesome Mock OS"
        mock_product = mock.Mock()
        mock_product.id = 123
        mock_product.name = product_name

        brand = entbranding.ProductBrand.from_product(mock_product)
        self.assertEquals(product_name, brand.name)

    def test_format_brand(self):
        fb = entbranding.ProductBrand.format_brand('Blip')
        self.assert_string_equals(fb, 'Blip\n')

        fb = entbranding.ProductBrand.format_brand('')
        self.assert_string_equals(fb, '\n')

        fb = entbranding.ProductBrand.format_brand('Foo\n')
        self.assert_string_equals(fb, 'Foo\n')


class TestCurrentBrand(BaseBrandFixture):
    def test_init(self):
        entbranding.CurrentBrand()

    def test_load(self):
        cb = entbranding.CurrentBrand()
        self.assertEquals(self.current_brand, cb.name)

    def test_unformat_brand(self):
        cb_class = entbranding.CurrentBrand
        self.assertEquals("foo", cb_class.unformat_brand("foo"))
        self.assertEquals("foo", cb_class.unformat_brand("foo\n"))

    def test_unformat_brand_none(self):
        cb_class = entbranding.CurrentBrand
        self.assertTrue(cb_class.unformat_brand(None) is None)

    def test_io_exception_on_brandfile_read(self):
        self.mock_brand_read.side_effect = IOError
        cb = entbranding.CurrentBrand()
        self.assertTrue(cb.name is None)

    def test_exception_on_brandfile_read(self):
        self.mock_brand_read.side_effect = Exception
        self.assertRaises(Exception, entbranding.CurrentBrand)


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
