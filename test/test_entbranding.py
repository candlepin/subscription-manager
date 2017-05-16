
import mock

from . import fixture
from . import stubs

from rhsm import certificate2
from subscription_manager import entbranding
from subscription_manager import rhelentbranding
from subscription_manager import injection as inj


# The certificate2.Product is basically just a data structure
#  so we can use the real one. No methods that need mocking.
class StubProduct(certificate2.Product):
    pass


class DefaultStubProduct(StubProduct):
    def __init__(self, id=123, name="Awesome OS",
                 brand_type='OS', brand_name='Awesome OS super'):

        super(DefaultStubProduct, self).__init__(id=id, name=name, brand_type=brand_type,
                                                 brand_name=brand_name)


# The installed product ids don't have brand_type/brand_name, just the
# Product from the ent cert
class DefaultStubInstalledProduct(StubProduct):
    def __init__(self, id=123, name="Awesome OS",
                 brand_type=None, brand_name=None):

        super(DefaultStubInstalledProduct, self).__init__(id=id, name=name, brand_type=brand_type,
                                                 brand_name=brand_name)


class BaseBrandFixture(fixture.SubManFixture):
    current_brand = "Current Awesome OS Brand"

    def setUp(self):
        super(BaseBrandFixture, self).setUp()
        self.brand_file_write_patcher = mock.patch("subscription_manager.entbranding.BrandFile.write",
                                              name="MockBrandFile.write")
        self.mock_write = self.brand_file_write_patcher.start()

        self.brand_file_read_patcher = mock.patch("subscription_manager.entbranding.BrandFile.read",
                                             return_value="%s\n" % self.current_brand,
                                             name="MockBrandFile.read")
        self.mock_brand_read = self.brand_file_read_patcher.start()

        self.mock_install_patcher = mock.patch("subscription_manager.rhelentbranding.RHELBrandInstaller._install",
                                               name="Mock_install_branding")

        self.mock_install = self.mock_install_patcher.start()

    def tearDown(self):
        super(BaseBrandFixture, self).tearDown()
        self.brand_file_write_patcher.stop()
        self.brand_file_read_patcher.stop()
        self.mock_install_patcher.stop()


# never write out the file to disk
class TestBrandInstaller(BaseBrandFixture):
    brand_installer_class = entbranding.BrandInstaller

    def test_init_empty_cert_list(self):
        self.brand_installer_class([])

    def test_init_no_ent_cert(self):
        self.brand_installer_class()


class TestRHELBrandInstaller(BaseBrandFixture):
    brand_installer_class = rhelentbranding.RHELBrandInstaller

    def test_init_empty_cert_list(self):
        self.brand_installer_class([])

    def test_init_no_ent_cert(self):
        self.brand_installer_class()

    def test_no_installed_products_no_ent_certs(self):
        brand_installer = self.brand_installer_class([])
        brand_installer.install()

        self.assertFalse(self.mock_install.called)

    def test_no_ent_certs_installed_products(self):
        prod_dir = stubs.StubProductDirectory(pids=[1, 2, 3, 4, 5])
        inj.provide(inj.PROD_DIR, prod_dir)
        brand_installer = self.brand_installer_class([])
        brand_installer.install()

        self.assertFalse(self.mock_install.called)

    def _inj_mock_ent_dir(self, ents=None):
        ent_list = ents or []
        mock_ent_dir = mock.NonCallableMock(name='MockEntDir')
        mock_ent_dir.list_valid.return_value = ent_list
        inj.provide(inj.ENT_DIR, mock_ent_dir)
        return mock_ent_dir

    def test(self):
        stub_product = DefaultStubProduct()
        stub_installed_product = DefaultStubInstalledProduct()

        mock_prod_dir = mock.NonCallableMock(name='MockProductDir')
        mock_prod_dir.get_installed_products.return_value = [stub_installed_product.id]

        inj.provide(inj.PROD_DIR, mock_prod_dir)

        mock_ent_cert = mock.Mock(name='MockEntCert')
        mock_ent_cert.products = [stub_product]

        self._inj_mock_ent_dir([mock_ent_cert])
        brand_installer = self.brand_installer_class()
        brand_installer.install()

        self.assertTrue(self.mock_install.called)
        call_args = self.mock_install.call_args
        brand_arg = call_args[0][0]
        self.assertTrue(isinstance(brand_arg, entbranding.ProductBrand))
        self.assertTrue(isinstance(brand_arg, rhelentbranding.RHELProductBrand))
        self.assertEqual('Awesome OS super', brand_arg.name)

    def test_no_need_to_update_branding(self):
        stub_product = StubProduct(id=123, brand_type='OS',
                                   name="Some name",
                                   brand_name=self.current_brand)

        stub_installed_product = StubProduct(id=123, name="Some name")

        mock_prod_dir = mock.NonCallableMock(name='MockProductDir')
        mock_prod_dir.get_installed_products.return_value = [stub_installed_product.id]

        inj.provide(inj.PROD_DIR, mock_prod_dir)

        mock_ent_cert = mock.Mock(name='MockEntCert')
        mock_ent_cert.products = [stub_product]

        self._inj_mock_ent_dir([mock_ent_cert])
        brand_installer = self.brand_installer_class()
        brand_installer.install()

        self.assertFalse(self.mock_install.called)

    def test_no_brand_type_on_product(self):
        # no brand_type
        stub_product = StubProduct(id=123, name="Awesome OS Super")
        stub_installed_product = StubProduct(id=123, name="Awesome OS Super")

        # simulate a old style Product, shouldn't happen
        del stub_product.brand_type
        mock_prod_dir = mock.NonCallableMock(name='MockProductDir')
        mock_prod_dir.get_installed_products.return_value = [stub_installed_product.id]

        inj.provide(inj.PROD_DIR, mock_prod_dir)

        mock_ent_cert = mock.Mock(name='MockEntCert')
        mock_ent_cert.products = [stub_product]

        self._inj_mock_ent_dir([mock_ent_cert])
        brand_installer = self.brand_installer_class()
        brand_installer.install()

        self.assertFalse(self.mock_install.called)

    def test_none_product_name_none_brand_name_on_product(self):
        # can't create a certificate2.Product without a name
        # so create it with and undo it. This should never happen
        stub_product = StubProduct(name="placeholder", id=123, brand_type='OS')
        stub_product.name = None
        stub_product.brand_name = None

        stub_installed_product = StubProduct(name="placeholder", id=123)

        mock_prod_dir = mock.NonCallableMock(name='MockProductDir')
        mock_prod_dir.get_installed_products.return_value = [stub_installed_product.id]

        mock_ent_cert = mock.Mock(name='MockEntCert')
        mock_ent_cert.products = [stub_product]
        self._inj_mock_ent_dir([mock_ent_cert])

        brand_installer = self.brand_installer_class()
        brand_installer.install()

        self.assertFalse(self.mock_install.called)

    def test_none_brand_name_on_product(self):
        stub_product = StubProduct(id=123, name="An Awesome OS", brand_type='OS')
        stub_product.name = None

        stub_installed_product = StubProduct(id=123, name="An Awesome OS")

        mock_prod_dir = mock.NonCallableMock(name='MockProductDir')
        mock_prod_dir.get_installed_products.return_value = [stub_installed_product.id]

        mock_ent_cert = mock.Mock(name='MockEntCert')
        mock_ent_cert.products = [stub_product]
        self._inj_mock_ent_dir([mock_ent_cert])

        brand_installer = self.brand_installer_class()
        brand_installer.install()

        self.assertFalse(self.mock_install.called)

    def test_none_brand_type_none_brand_name_on_product(self):
        stub_product = StubProduct(id=123, name="An Awesome OS")
        stub_product.name = None

        mock_prod_dir = mock.NonCallableMock(name='MockProductDir')
        mock_prod_dir.get_installed_products.return_value = [stub_product.id]

        mock_ent_cert = mock.Mock(name='MockEntCert')
        mock_ent_cert.products = [stub_product]
        self._inj_mock_ent_dir([mock_ent_cert])

        brand_installer = self.brand_installer_class()
        brand_installer.install()

        self.assertFalse(self.mock_install.called)

    def test_none_brand_type_brand_name_on_product(self):
        stub_product = StubProduct(id=123, name="An Awesome OS",
                                   brand_name="Branded Awesome OS")
        stub_product.name = None

        stub_installed_product = StubProduct(id=123, name="An Awesome OS")
        mock_prod_dir = mock.NonCallableMock(name='MockProductDir')
        mock_prod_dir.get_installed_products.return_value = [stub_installed_product.id]

        mock_ent_cert = mock.Mock(name='MockEntCert')
        mock_ent_cert.products = [stub_product]
        self._inj_mock_ent_dir([mock_ent_cert])

        brand_installer = self.brand_installer_class()
        brand_installer.install()

        self.assertFalse(self.mock_install.called)

    def test_wrong_brand_type_brand_name_on_product(self):
        stub_product = StubProduct(id=123, name="An Awesome OS",
                                   brand_type='Middleware',
                                   brand_name="Branded Awesome OS")

        stub_installed_product = StubProduct(id=123, name="An Awesome OS")

        mock_prod_dir = mock.NonCallableMock(name='MockProductDir')
        mock_prod_dir.get_installed_products.return_value = [stub_installed_product.id]

        mock_ent_cert = mock.Mock(name='MockEntCert')
        mock_ent_cert.products = [stub_product]
        self._inj_mock_ent_dir([mock_ent_cert])

        brand_installer = self.brand_installer_class()
        brand_installer.install()

        self.assertFalse(self.mock_install.called)

    def test_wrong_brand_type_none_brand_name_on_product(self):
        stub_product = StubProduct(id=123, name="An Awesome OS",
                                   brand_type='Middleware')

        stub_installed_product = StubProduct(id=123, name="An Awesome OS")

        mock_prod_dir = mock.NonCallableMock(name='MockProductDir')
        mock_prod_dir.get_installed_products.return_value = [stub_installed_product.id]

        mock_ent_cert = mock.Mock(name='MockEntCert')
        mock_ent_cert.products = [stub_product]
        self._inj_mock_ent_dir([mock_ent_cert])

        brand_installer = self.brand_installer_class()
        brand_installer.install()

        self.assertFalse(self.mock_install.called)

    def test_multiple_matching_branded_products(self):
        stub_product = DefaultStubProduct()
        stub_installed_product = DefaultStubInstalledProduct()

        stub_product_2 = StubProduct(id=321, brand_type='OS', name="Awesome",
                                     brand_name="Slightly Different Awesome OS Super")

        stub_installed_product_2 = StubProduct(id=321, name="Awesome")

        mock_prod_dir = mock.NonCallableMock(name='MockProductDir')
        mock_prod_dir.get_installed_products.return_value = [stub_installed_product.id,
                                                             stub_installed_product_2.id]

        inj.provide(inj.PROD_DIR, mock_prod_dir)

        mock_ent_cert = mock.Mock(name='MockEntCert')
        mock_ent_cert.products = [stub_product, stub_product_2]

        brand_installer = self.brand_installer_class([mock_ent_cert])
        brand_installer.install()

        # we give up in this case and leave things as is
        self.assertFalse(self.mock_install.called)

    def test_multiple_branded_ent_certs_for_installed_product(self):
        stub_product = DefaultStubProduct()
        stub_installed_product = DefaultStubInstalledProduct()

        mock_prod_dir = mock.NonCallableMock(name='MockProductDir')
        mock_prod_dir.get_installed_products.return_value = [stub_installed_product.id]

        inj.provide(inj.PROD_DIR, mock_prod_dir)

        mock_ent_cert = mock.Mock(name='MockEntCert')
        mock_ent_cert.products = [stub_product]

        mock_ent_cert_2 = mock.Mock(name='MockEntCert2')
        mock_ent_cert_2.products = [stub_product]

        brand_installer = self.brand_installer_class([mock_ent_cert, mock_ent_cert_2])
        brand_installer.install()

        self.assertTrue(self.mock_install.called)


class TestBrandsInstaller(TestBrandInstaller):
    brand_installer_class = entbranding.BrandsInstaller


class StubEmptyBrandsInstaller(entbranding.BrandsInstaller):
    def _get_brand_installers(self):
        return []


class TestEmptyBrandsInstaller(TestBrandInstaller):
    brand_installer_class = StubEmptyBrandsInstaller


class StubMultipleBrandsInstaller(entbranding.BrandsInstaller):
    def _get_brand_installers(self):
        mock_brand_installer_1 = mock.Mock()
        mock_brand_installer_2 = mock.Mock()
        return [mock_brand_installer_1, mock_brand_installer_2]


class TestMultipleBrandsInstaller(TestBrandInstaller):
    brand_installer_class = StubMultipleBrandsInstaller


class StubRhelAndMockBrandsInstaller(rhelentbranding.RHELBrandsInstaller):
    def _get_brand_installers(self):
        return [mock.Mock(),
                rhelentbranding.RHELBrandInstaller(self.ent_certs),
                mock.Mock()]


class TestRhelAndMockBrandsInstaller(TestRHELBrandInstaller):
    """Test a BrandsInstaller with a RHELBrandInstaller and a mock"""
    brand_installer_class = StubRhelAndMockBrandsInstaller

    def test(self):
        stub_product = DefaultStubProduct()

        mock_prod_dir = mock.NonCallableMock(name='MockProductDir')
        mock_prod_dir.get_installed_products.return_value = [stub_product.id]

        inj.provide(inj.PROD_DIR, mock_prod_dir)

        mock_ent_cert = mock.Mock(name='MockEntCert')
        mock_ent_cert.products = [stub_product]

        brand_installer = self.brand_installer_class([mock_ent_cert])
        brand_installer.install()

        self.assertTrue(self.mock_install.called)
        call_args = self.mock_install.call_args
        brand_arg = call_args[0][0]
        self.assertTrue(isinstance(brand_arg, entbranding.ProductBrand))
        self.assertTrue(isinstance(brand_arg, rhelentbranding.RHELProductBrand))
        self.assertEqual("Awesome OS super", brand_arg.name)

        # verify the install on all the installers got called
        count = 0
        for bi in brand_installer.brand_installers:
            if isinstance(bi, mock.Mock):
                self.assertTrue(bi.install.called)
                count = count + 1
        self.assertEqual(2, count)


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


class TestBrandPicker(BaseBrandFixture):
    def test_init(self):
        entbranding.BrandPicker([])


class TestRHELBrandPicker(BaseBrandFixture):
    @mock.patch("subscription_manager.rhelentbranding.RHELBrandPicker._get_branded_cert_products",
                return_value=[(mock.Mock(name="Mock Certificate 1"), DefaultStubProduct()),
                              (mock.Mock(name="Mock Certificate 2"), DefaultStubProduct())])
    def test_more_than_one_ent_cert_with_branding(self, mock_branded_certs):
        brand_picker = rhelentbranding.RHELBrandPicker([])
        brand = brand_picker.get_brand()
        self.assertEqual("Awesome OS super", brand.name)

    @mock.patch("subscription_manager.rhelentbranding.RHELBrandPicker._get_branded_cert_products",
                return_value=[])
    def test_branded_certs_returns_empty(self, mock_branded_certs):

        brand_picker = rhelentbranding.RHELBrandPicker([])
        brand = brand_picker.get_brand()

        self.assertEqual(None, brand)

    def test_get_brand(self):
        # inj a prod dir with some installed products
        stub_installed_product = DefaultStubInstalledProduct()
        stub_product = DefaultStubProduct()

        mock_product_dir = mock.NonCallableMock()
        mock_product_dir.get_installed_products.return_value = [stub_installed_product.id]
        inj.provide(inj.PROD_DIR, mock_product_dir)

        mock_ent_cert = mock.Mock()
        mock_ent_cert.products = [stub_product]
        ent_certs = [mock_ent_cert]

        brand_picker = rhelentbranding.RHELBrandPicker(ent_certs)
        brand = brand_picker.get_brand()
        self.assertTrue("Mock Product", brand.name)

    def test_get_brand_multiple_ents_with_branding_same_name(self):
        # inj a prod dir with some installed products
        stub_product = DefaultStubProduct()

        stub_product_2 = DefaultStubProduct()

        mock_product_dir = mock.NonCallableMock()
        mock_product_dir.get_installed_products.return_value = [stub_product.id]
        inj.provide(inj.PROD_DIR, mock_product_dir)

        mock_ent_cert = mock.Mock()
        mock_ent_cert.products = [stub_product]

        mock_ent_cert_2 = mock.Mock()
        mock_ent_cert_2.products = [stub_product_2]

        ent_certs = [mock_ent_cert, mock_ent_cert_2]

        brand_picker = rhelentbranding.RHELBrandPicker(ent_certs)
        brand = brand_picker.get_brand()
        self.assertTrue(brand is not None)
        self.assertTrue("Awesome OS", brand.name)

    def test_get_brand_multiple_ents_with_branding_different_branded_name(self):
        # inj a prod dir with some installed products
        stub_product = DefaultStubProduct()

        # same product id, different name
        stub_product_2 = StubProduct(id=123, brand_type='OS',
                                     name='A Different Stub Product',
                                     brand_name='A Different branded Stub Product')

        mock_product_dir = mock.NonCallableMock()
        # note stub_product.id=123 will match the Product from both ents
        mock_product_dir.get_installed_products.return_value = [stub_product.id]
        inj.provide(inj.PROD_DIR, mock_product_dir)

        mock_ent_cert = mock.Mock()
        mock_ent_cert.products = [stub_product]

        mock_ent_cert_2 = mock.Mock()
        mock_ent_cert_2.products = [stub_product_2]
        ent_certs = [mock_ent_cert, mock_ent_cert_2]

        brand_picker = rhelentbranding.RHELBrandPicker(ent_certs)
        brand = brand_picker.get_brand()
        self.assertTrue(brand is None)

    def test_get_brand_not_installed(self):

        stub_product = DefaultStubProduct()

        # note, no 'brand_type' set
        other_stub_product = StubProduct(id=321, name="A Non Branded Product")

        mock_product_dir = mock.NonCallableMock()
        mock_product_dir.get_installed_products.return_value = [other_stub_product.id]
        inj.provide(inj.PROD_DIR, mock_product_dir)

        mock_ent_cert = mock.Mock()
        mock_ent_cert.products = [stub_product]
        ent_certs = [mock_ent_cert]

        brand_picker = rhelentbranding.RHELBrandPicker(ent_certs)
        brand = brand_picker.get_brand()
        self.assertTrue(brand is None)

    def test_get_brand_branded_unknown_brand_type(self):

        stub_installed_product = StubProduct(id=123, name="Stub Product Name")

        # note, no 'brand_type' attribute
        other_stub_installed_product = StubProduct(id=321, name='A Non Branded Product')

        mock_product_dir = mock.NonCallableMock()
        mock_product_dir.get_installed_products.return_value = [stub_installed_product.id,
                                                                other_stub_installed_product.id]
        inj.provide(inj.PROD_DIR, mock_product_dir)

        stub_product = StubProduct(id=123, brand_type="middleware",
                                   name="Stub Product Name", brand_name="Awesome Middleware")
        mock_ent_cert = mock.Mock()
        mock_ent_cert.products = [stub_product]
        ent_certs = [mock_ent_cert]

        # NOTE: this looks like a branded product, except the brand type is one
        # the RHELBrandPicker doesn't know
        brand_picker = rhelentbranding.RHELBrandPicker(ent_certs)
        brand = brand_picker.get_brand()
        self.assertTrue(brand is None)

    def test_is_installed_rhel_branded_product_not_installed(self):
        brand_picker = rhelentbranding.RHELBrandPicker([])
        stub_product = DefaultStubProduct()
        # note no installed products in injected installed products
        irp = brand_picker._is_installed_rhel_branded_product(stub_product)
        self.assertFalse(irp)

    def test_is_installed_rhel_branded_product_is_installed(self):
        stub_product = DefaultStubProduct()

        mock_product_dir = mock.NonCallableMock()
        mock_product_dir.get_installed_products.return_value = [stub_product.id]
        inj.provide(inj.PROD_DIR, mock_product_dir)

        brand_picker = rhelentbranding.RHELBrandPicker([])
        irp = brand_picker._is_installed_rhel_branded_product(stub_product)
        self.assertTrue(irp)

    def test_get_installed_branded_products(self):
        stub_product = DefaultStubProduct()

        mock_product_dir = mock.NonCallableMock()
        mock_product_dir.get_installed_products.return_value = [stub_product.id]
        inj.provide(inj.PROD_DIR, mock_product_dir)

        brand_picker = rhelentbranding.RHELBrandPicker([])
        irp = brand_picker._is_installed_rhel_branded_product(stub_product)
        self.assertTrue(irp)


class TestRHELBrandPickerIsRHELBrandedProduct(BaseBrandFixture):
    def setUp(self):
        super(TestRHELBrandPickerIsRHELBrandedProduct, self).setUp()
        self.brand_picker = rhelentbranding.RHELBrandPicker([])

    def _check_branded(self, product):
        return self.brand_picker._is_rhel_branded_product(product)

    def test(self):
        stub_product = DefaultStubProduct()
        self.assertTrue(self._check_branded(stub_product))

    def test_none_brand_type(self):
        # brand_type is set to None (not specified)
        none_brand_type_stub_product = StubProduct(name="Awesome NoOS", id=123)
        self.assertFalse(self._check_branded(none_brand_type_stub_product))

    def test_no_brand_type(self):
        # a Product with no brand_type attribute, like old versions
        # are not branded
        no_brand_type_stub_product = DefaultStubProduct()
        del no_brand_type_stub_product.brand_type
        self.assertFalse(self._check_branded(no_brand_type_stub_product))

    def test_empty_brand_type(self):
        # At the moment, "" != "OS", so brand_type="" is not a rhel
        empty_brand_type_stub_product = DefaultStubProduct(brand_type="")
        self.assertFalse(self._check_branded(empty_brand_type_stub_product))

    def test_none_brand_name(self):
        # product.brand_name is none
        none_brand_name_stub_product = DefaultStubProduct()
        none_brand_name_stub_product.brand_name = None
        self.assertFalse(self._check_branded(none_brand_name_stub_product))

    def test_no_brand_name(self):
        # no Product.brand_name at all, ala old Product objects
        no_brand_name_stub_product = DefaultStubProduct()
        del no_brand_name_stub_product.brand_name
        self.assertFalse(self._check_branded(no_brand_name_stub_product))

    def test_empty_brand_name(self):
        # product.brand_name is ""
        empty_brand_name_stub_product = DefaultStubProduct(brand_name="")
        self.assertFalse(self._check_branded(empty_brand_name_stub_product))


class TestProductBrand(BaseBrandFixture):
    brand_class = entbranding.ProductBrand

    def test_init(self):
        self.brand_class("Awesome OS")

    def test_brand(self):
        brand = self.brand_class("Awesome OS")
        self.assertEqual("Awesome OS", brand.name)

    def test_brand_save(self):
        brand = self.brand_class("Foo")
        brand.save()
        self.mock_write.assert_called_with("Foo\n")

    def test_exception_on_save(self):
        self.mock_write.side_effect = IOError
        brand = self.brand_class("Foo")
        self.assertRaises(IOError, brand.save)

    def test_from_product(self):
        stub_product = DefaultStubProduct()
        brand = self.brand_class.from_product(stub_product)
        self.assertEqual(stub_product.brand_name, brand.name)

    def test_from_product_brand_name_none(self):
        stub_product = DefaultStubProduct(brand_name=None)
        brand = self.brand_class.from_product(stub_product)
        self.assertEqual(stub_product.brand_name, brand.name)
        self.assertTrue(brand.name is None)

    # ProductBrand shouldn't care about the Product.brand_type,
    # that's BrandPicker's job
    def test_from_product_brand_type_none(self):
        stub_product = DefaultStubProduct(brand_type=None)
        brand = self.brand_class.from_product(stub_product)
        self.assertEqual(stub_product.brand_name, brand.name)

    # An empty string is just a name, a poor name
    # ie, no casting to None, etc.
    # NOTE: we basically ignore brand_name="" in RHELBrandPicker
    # so we can't install a branded name of "", which is okay
    # since brandbot doesn't know what to do with that.
    def test_from_product_brand_name_empty_string(self):
        stub_product = DefaultStubProduct(brand_name="")
        brand = self.brand_class.from_product(stub_product)
        self.assertEqual(stub_product.brand_name, brand.name)
        self.assertEqual("", brand.name)

    # see comment about test_from_product_brand_type_none
    def test_from_product_brand_type_empty_string(self):
        stub_product = DefaultStubProduct(brand_type="")
        brand = self.brand_class.from_product(stub_product)
        self.assertEqual(stub_product.brand_name, brand.name)

    def test_format_brand(self):
        fb = self.brand_class.format_brand('Blip')
        self.assert_string_equals(fb, 'Blip\n')

        fb = self.brand_class.format_brand('')
        self.assert_string_equals(fb, '\n')

        fb = self.brand_class.format_brand('Foo\n')
        self.assert_string_equals(fb, 'Foo\n')


class TestRHELProductBrand(TestProductBrand):
    brand_class = rhelentbranding.RHELProductBrand


class TestCurrentBrand(BaseBrandFixture):
    brand_class = entbranding.CurrentBrand

    def test_init(self):
        self.brand_class()

    def test_load(self):
        cb = self.brand_class()
        self.assertEqual(self.current_brand, cb.name)

    def test_unformat_brand(self):
        self.assertEqual("foo", self.brand_class.unformat_brand("foo"))
        self.assertEqual("foo", self.brand_class.unformat_brand("foo\n"))

    def test_unformat_brand_none(self):
        self.assertTrue(self.brand_class.unformat_brand(None) is None)

    def test_io_exception_on_brandfile_read(self):
        self.mock_brand_read.side_effect = IOError
        cb = self.brand_class()
        self.assertTrue(cb.name is None)

    def test_exception_on_brandfile_read(self):
        self.mock_brand_read.side_effect = Exception
        self.assertRaises(Exception, self.brand_class)


class TestRHELCurrentBrand(TestCurrentBrand):
    brand_class = rhelentbranding.RHELCurrentBrand


class TestBrandFile(fixture.SubManFixture):
    brandfile_class = entbranding.BrandFile

    def test_init(self):
        self.brandfile_class()
        self.assertEqual("/var/lib/rhsm/branded_name", self.brandfile_class.path)

    def test_write(self):
        brand_file = self.brandfile_class()
        mo = mock.mock_open()
        with mock.patch('subscription_manager.entbranding.open', mo, create=True):
            brand_file.write("Foo OS")
        mo.assert_called_once_with('/var/lib/rhsm/branded_name', 'w')

    def test_read(self):
        brand_file = self.brandfile_class()
        brand_string = "Some Branding Info"
        mo = mock.mock_open(read_data=brand_string)
        with mock.patch('subscription_manager.entbranding.open', mo, create=True):
            b = brand_file.read()
        self.assert_string_equals(brand_string, b)


class TestRHELBrandFile(TestBrandFile):
    brandfile_class = rhelentbranding.RHELBrandFile
