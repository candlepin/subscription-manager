
import mock

import fixture

from subscription_manager import model


def create_mock_content(name=None, url=None, gpg=None, enabled=None, content_type=None, tags=None):
    mock_content = mock.Mock()
    mock_content.name = name or "mock_content"
    mock_content.url = url or "http://mock.example.com"
    mock_content.gpg = gpg or "path/to/gpg"
    mock_content.enabled = enabled or True
    mock_content.content_type = content_type or "yum"
    mock_content.tags = tags or []
    return mock_content


class TestContent(fixture.SubManFixture):
    def test_init(self):
        content = model.Content("content-label",
                                "content name",
                                "http://contenturl.example.com",
                                "/path/to/gpg",
                                ["product-content-tag"],
                                cert=None)

        self._check_attrs(content)
        self.assertTrue(isinstance(content.tags, list))

    def _check_attrs(self, content):
        attrs = ['content_type', 'name', 'label', 'url', 'gpg', 'tags', 'cert']
        for attr in attrs:
            self.assertTrue(hasattr(content, attr))


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


class EntitlementSourceBuilder(object):
    def contents_list(self, name):
        return [self.mock_content(name), self.mock_content(name)]

    def mock_content(self, name):
        """name also has to work as a label."""
        mock_content = create_mock_content(name=name)
        return mock_content

    def ent_source(self):
        cl1 = self.contents_list('content1')
        cl2 = self.contents_list('content2')

        ent1 = model.Entitlement(contents=cl1)
        ent2 = model.Entitlement(contents=cl2)

        es = model.EntitlementSource()
        es._entitlements = [ent1, ent2]
        return es


class TestEntitlementSource(fixture.SubManFixture):
    def test_empty_init(self):
        es = model.EntitlementSource()
        # NOTE: this is just for testing this impl, the api
        # itself should never reference self.entitlements
        self.assertTrue(hasattr(es, '_entitlements'))

    def test(self):
        esb = EntitlementSourceBuilder()
        es = esb.ent_source()

        self.assertEquals(len(es), 2)

        for ent in es:
            self.assertTrue(isinstance(ent, model.Entitlement))
            self.assertTrue(len(ent.contents), 2)

        self.assertTrue(isinstance(es[0], model.Entitlement))


class TestFindContent(fixture.SubManFixture):
    def test(self):
        esb = EntitlementSourceBuilder()
        es = esb.ent_source()

        res = model.find_content(es, content_type="yum")
        self.assertEquals(len(res), 4)

    def test_prod_tags(self):
        esb = EntitlementSourceBuilder()
        es = esb.ent_source()
        es.prod_tags = []

        res = model.find_content(es, content_type="yum")
        self.assertEquals(len(res), 4)

    def test_prod_tags_one_non_match(self):
        esb = EntitlementSourceBuilder()
        es = esb.ent_source()
        es.prod_tags = ['something-random-tag']

        res = model.find_content(es, content_type="yum")
        self.assertEquals(len(res), 4)

    def test_prod_tags_and_content_tags_match(self):
        content = create_mock_content(tags=['awesomeos-ostree-1'],
                                      content_type="ostree")
        content_list = [content]

        entitlement = model.Entitlement(contents=content_list)
        es = model.EntitlementSource()
        es._entitlements = [entitlement]
        es.prod_tags = ['awesomeos-ostree-1']

        res = model.find_content(es, content_type="ostree")

        self.assertEquals(len(res), 1)
        self.assertEquals(res[0], content)

    def test_prod_tags_and_content_tags_no_match(self):
        content1 = create_mock_content(tags=['awesomeos-ostree-23'],
                                      content_type="ostree")
        content2 = create_mock_content(name="more-test-content",
                                       tags=['awesomeos-ostree-24'],
                                       content_type="ostree")
        content_list = [content1, content2]

        entitlement = model.Entitlement(contents=content_list)
        es = model.EntitlementSource()
        es._entitlements = [entitlement]
        es.prod_tags = ['awesomeos-ostree-1']

        res = model.find_content(es, content_type="ostree")

        self.assertEquals(len(res), 0)

    def test_prod_tags_and_content_tags_no_match_no_prod_tags(self):
        content1 = create_mock_content(tags=['awesomeos-ostree-23'],
                                      content_type="ostree")
        content2 = create_mock_content(name="more-test-content",
                                       tags=['awesomeos-ostree-24'],
                                       content_type="ostree")
        content_list = [content1, content2]

        entitlement = model.Entitlement(contents=content_list)
        es = model.EntitlementSource()
        es._entitlements = [entitlement]

        res = model.find_content(es, content_type="ostree")

        self.assertEquals(len(res), 0)

    def test_prod_tags_and_content_tags_no_match_empty_prod_tags(self):
        content1 = create_mock_content(tags=['awesomeos-ostree-23'],
                                      content_type="ostree")
        content2 = create_mock_content(name="more-test-content",
                                       tags=['awesomeos-ostree-24'],
                                       content_type="ostree")
        content_list = [content1, content2]

        entitlement = model.Entitlement(contents=content_list)
        es = model.EntitlementSource()
        es._entitlements = [entitlement]
        es.prod_tags = []

        res = model.find_content(es, content_type="ostree")

        self.assertEquals(len(res), 0)

    def test_prod_tags_and_content_tags_multiple_content_one_match(self):
        content1 = create_mock_content(tags=['awesomeos-ostree-23'],
                                      content_type="ostree")
        content2 = create_mock_content(name="more-test-content",
                                       tags=['awesomeos-ostree-1'],
                                       content_type="ostree")
        content_list = [content1, content2]

        entitlement = model.Entitlement(contents=content_list)
        es = model.EntitlementSource()
        es._entitlements = [entitlement]
        es.prod_tags = ['awesomeos-ostree-1']

        res = model.find_content(es, content_type="ostree")

        self.assertEquals(len(res), 1)
        self.assertEquals(res[0], content2)

    def test_no_content_tags(self):
        content = create_mock_content(content_type="ostree")
        content_list = [content]

        entitlement = model.Entitlement(contents=content_list)
        es = model.EntitlementSource()
        es._entitlements = [entitlement]
        es.prod_tags = ['awesomeos-ostree-1']

        res = model.find_content(es, content_type="ostree")
        self.assertEquals(len(res), 1)
        self.assertEquals(res[0], content)
