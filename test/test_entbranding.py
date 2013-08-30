
import fixture

from subscription_manager import entbranding


class TestBrand(fixture.SubManFixture):

    def test_init(self):
        entbranding.Brand("Awesome OS")

    def test_brand(self):
        brand = entbranding.Brand("Awesome OS")
        self.assertEquals("Awesome OS", brand.brand)


class TestBrandFile(fixture.SubManFixture):

    def test_init(self):
        entbranding.BrandFile()

    def test_brand_path(self):
        # class method
        self.assertEquals("/var/lib/rhsm/branded_name", entbranding.BrandFile.brand_path())
