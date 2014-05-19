
import mock

import fixture

from subscription_manager import models


class TestEntitledContents(fixture.SubManFixture):
    def test_empty_init(self):
        ec = models.EntitledContents()
        self.assertTrue(hasattr(ec, 'contents'))

    def test_init_empty_contents(self):
        ec = models.EntitledContents(contents=[])
        self.assertTrue(hasattr(ec, 'contents'))
        self.assertEquals(ec.contents, [])

    def test_contents(self):
        contents = [mock.Mock(), mock.Mock(), mock.Mock()]
        ec = models.EntitledContents(contents=contents)
        self.assertTrue(hasattr(ec, 'contents'))
        self.assertEquals(len(ec.contents), 3)

        for content in ec.contents:
            self.assertTrue(isinstance(content, mock.Mock))

        self.assertTrue(isinstance(ec.contents[0], mock.Mock))


class TestEntitlement(fixture.SubManFixture):
    def test_empty_init(self):
        e = models.Entitlement()
        self.assertTrue(hasattr(e, 'content'))

    def test_init_empty_content(self):
        e = models.Entitlement(content=[])
        self.assertTrue(hasattr(e, 'content'))
        self.assertEquals(e.content, [])

    def test_content(self):
        content = [mock.Mock(), mock.Mock()]
        e = models.Entitlement(content=content)
        self.assertTrue(hasattr(e, 'content'))
        self.assertEquals(len(e.content), 2)

        for a_content in e.content:
            self.assertTrue(isinstance(a_content, mock.Mock))

        self.assertTrue(isinstance(e.content[0], mock.Mock))


class TestEntitlementCertEntitlement(TestEntitlement):
    def test_from_ent_cert(self):
        mock_content = mock.Mock()
        mock_content.name = "mock_content"
        mock_content.url = "http://mock.example.com"
        mock_content.gpg = "path/to/gpg"
        mock_content.enabled = True
        mock_content.content_type = "yum"

        content = [mock_content]

        mock_ent_cert = mock.Mock()
        mock_ent_cert.content = content

        ece = models.EntitlementCertEntitlement.from_ent_cert(mock_ent_cert)

        self.assertEquals(ece.content.contents, content)
        self.assertEquals(len(ece.content), 1)
        self.assertTrue(isinstance(ece.content, models.EntitledContents))

        self.assertEquals(ece.content[0].name, "mock_content")

        # for ostree content, gpg is likely to change
        self.assertEquals(ece.content[0].gpg, "path/to/gpg")


class TestEntitlementSource(fixture.SubManFixture):
    def content_list(self, name):
        return [self.mock_content(name), self.mock_content(name)]

    def mock_content(self, name):
        """name also has to work as a label."""
        mock_content = mock.Mock()
        mock_content.name = "mock_content_%s" % name
        mock_content.url = "http://mock.example.com/%s/" % name
        mock_content.gpg = "path/to/gpg"
        mock_content.enabled = True
        mock_content.label = name
        mock_content.content_type = "yum"
        return mock_content

    def test_empty_init(self):
        es = models.EntitlementSource()
        # NOTE: this is just for testing this impl, the api
        # itself should never reference self.entitlements
        self.assertTrue(hasattr(es, '_entitlements'))

    def test(self):
        cl1 = self.content_list('content1')
        cl2 = self.content_list('content2')
        ent1 = models.Entitlement(content=cl1)
        ent2 = models.Entitlement(content=cl2)

        es = models.EntitlementSource()
        es._entitlements = [ent1, ent2]

        self.assertEquals(len(es), 2)

        for ent in es:
            self.assertTrue(isinstance(ent, models.Entitlement))
            self.assertTrue(len(ent.content), 2)

        self.assertTrue(isinstance(es[0], models.Entitlement))
