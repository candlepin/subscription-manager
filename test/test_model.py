
import mock

import fixture

from subscription_manager import model


class TestEntitlement(fixture.SubManFixture):
    def test_empty_init(self):
        e = model.Entitlement()
        self.assertTrue(hasattr(e, 'contents'))

    def test_init_empty_contents(self):
        e = model.Entitlement(contents=[])
        self.assertTrue(hasattr(e, 'contents'))
        self.assertEquals(e.contents, [])

    def test_contents(self):
        contents = [mock.Mock(), mock.Mock()]
        e = model.Entitlement(contents=contents)
        self.assertTrue(hasattr(e, 'contents'))
        self.assertEquals(len(e.contents), 2)

        for a_content in e.contents:
            self.assertTrue(isinstance(a_content, mock.Mock))

        self.assertTrue(isinstance(e.contents[0], mock.Mock))


class TestEntitlementCertEntitlement(TestEntitlement):
    def test_from_ent_cert(self):
        mock_content = mock.Mock()
        mock_content.name = "mock_content"
        mock_content.url = "http://mock.example.com"
        mock_content.gpg = "path/to/gpg"
        mock_content.enabled = True
        mock_content.content_type = "yum"

        contents = [mock_content]

        mock_ent_cert = mock.Mock()
        mock_ent_cert.content = contents

        ece = model.ent_cert.EntitlementCertEntitlement.from_ent_cert(mock_ent_cert)

        self.assertEquals(ece.contents[0].name, contents[0].name)
        self.assertEquals(ece.contents[0].label, contents[0].label)
        self.assertEquals(ece.contents[0].gpg, contents[0].gpg)
        self.assertEquals(ece.contents[0].content_type,
            contents[0].content_type)
        self.assertEquals(len(ece.contents), 1)

        # for ostree content, gpg is likely to change
        self.assertEquals(ece.contents[0].gpg, mock_content.gpg)


class TestEntitlementSource(fixture.SubManFixture):
    def contents_list(self, name):
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
        es = model.EntitlementSource()
        # NOTE: this is just for testing this impl, the api
        # itself should never reference self.entitlements
        self.assertTrue(hasattr(es, '_entitlements'))

    def test(self):
        cl1 = self.contents_list('content1')
        cl2 = self.contents_list('content2')
        ent1 = model.Entitlement(contents=cl1)
        ent2 = model.Entitlement(contents=cl2)

        es = model.EntitlementSource()
        es._entitlements = [ent1, ent2]

        self.assertEquals(len(es), 2)

        for ent in es:
            self.assertTrue(isinstance(ent, model.Entitlement))
            self.assertTrue(len(ent.contents), 2)

        self.assertTrue(isinstance(es[0], model.Entitlement))
