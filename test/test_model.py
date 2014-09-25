
import mock

import fixture

from subscription_manager import model


def mock_content(name, content_type="yum"):
    """name also has to work as a label."""
    mock_content = mock.Mock()
    mock_content.name = name
    mock_content.url = "http://mock.example.com/%s/" % name
    mock_content.gpg = "path/to/gpg"
    mock_content.enabled = True
    mock_content.label = name
    mock_content.content_type = content_type
    return mock_content


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


class TestEntitlementCertEntitlement(fixture.SubManFixture):
    def test_from_ent_cert(self):
        c = mock_content('mock_content')
        contents = [c]

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
        self.assertEquals(ece.contents[0].gpg, c.gpg)


class TestEntitlementSource(fixture.SubManFixture):

    def contents_list(self, name):
        return [mock_content(name), mock_content(name)]

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

    def test_find_container_content(self):
        yum_content = mock_content("yum_content", content_type="yum")
        container_content = mock_content("container_content",
            content_type="containerImage")

        ent1 = model.Entitlement(contents=[yum_content])
        ent2 = model.Entitlement(contents=[container_content])

        ent_src = model.EntitlementSource()
        ent_src._entitlements = [ent1, ent2]
        yum_list = ent_src.find_content(content_type='yum')
        self.assertEquals(1, len(yum_list))
        self.assertEquals('yum_content', yum_list[0].name)
        cont_list = ent_src.find_content(content_type='containerImage')
        self.assertEquals(1, len(cont_list))
        self.assertEquals('container_content', cont_list[0].name)
