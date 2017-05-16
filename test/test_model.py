
import mock

from . import fixture

from subscription_manager import model


def create_mock_content(name=None, url=None, gpg=None, enabled=None, content_type=None, tags=None):
    mock_content = mock.Mock()
    mock_content.name = name or "mock_content"
    mock_content.label = name
    mock_content.url = url or "http://mock.example.com/%s/" % name
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
        self.assertEqual(e.contents, [])

    def test_contents(self):
        contents = [mock.Mock(), mock.Mock()]
        e = model.Entitlement(contents=contents)
        self.assertTrue(hasattr(e, 'contents'))
        self.assertEqual(len(e.contents), 2)

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


class TestContentTagMatch(fixture.SubManFixture):
    def test_empty_content_empty_product(self):
        content_tags = []
        product_tags = []
        matched = model.content_tag_match(content_tags, product_tags)
        # no requires means no missing requires
        self.assertTrue(matched)

    def test_content_empty_product(self):
        content_tags = ["awesomeos-1"]
        product_tags = []
        matched = model.content_tag_match(content_tags, product_tags)
        # content requires 'awesomeos-1" but products do not provide
        self.assertFalse(matched)

    def test_empty_content_product_awesome(self):
        content_tags = []
        product_tags = ["awesomeos-1"]
        matched = model.content_tag_match(content_tags, product_tags)
        # no content requires, so anything matches
        self.assertTrue(matched)

    def test_content_awesome_product_awesome(self):
        content_tags = ["awesomeos-1"]
        product_tags = ["awesomeos-1"]
        matched = model.content_tag_match(content_tags, product_tags)
        # require awesomeos-1, have awesomeos-1
        self.assertTrue(matched)

    def test_content_awesome_product_meh(self):
        content_tags = ["awesomeos-1"]
        product_tags = ["mehos-1"]
        matched = model.content_tag_match(content_tags, product_tags)
        # The requires awesomeos-1 is not provided
        self.assertFalse(matched)

    def test_content_multiple_product_multiple(self):
        content_tags = ["awesomeos-1", "awesomeos-server-1"]
        product_tags = ["awesomeos-1", "awesomeos-server-1"]
        matched = model.content_tag_match(content_tags, product_tags)
        # content requires awesomeos-1 and awesomeos-server-1, and they are
        # provided
        self.assertTrue(matched)

    def test_content_multiple_missing_product_multiple(self):
        content_tags = ["awesomeos-server-1", "awesomeos-1"]
        product_tags = ["awesomeos-1"]
        matched = model.content_tag_match(content_tags, product_tags)
        # content requires os and server, but only server is provided
        self.assertFalse(matched)

    def test_content_all_missing_product_multiple(self):
        content_tags = ["mehos-1", "mehos-doorstop-1"]
        product_tags = ["awesomeos-1", "awesomeos-server-1"]
        matched = model.content_tag_match(content_tags, product_tags)
        # none of the content required tags are provided
        self.assertFalse(matched)

    def test_content_dupes_product_dupes(self):
        content_tags = ["awesomeos-1", "awesomeos-1", "awesomeos-1"]
        product_tags = ["awesomeos-1", "awesomeos-1", "awesomeos-1"]
        matched = model.content_tag_match(content_tags, product_tags)
        # requires met multiple times
        self.assertTrue(matched)


class TestEntitlementSource(fixture.SubManFixture):
    def test_empty_init(self):
        es = model.EntitlementSource()
        # NOTE: this is just for testing this impl, the api
        # itself should never reference self.entitlements
        self.assertTrue(hasattr(es, '_entitlements'))

    def test(self):
        esb = EntitlementSourceBuilder()
        es = esb.ent_source()

        self.assertEqual(len(es), 2)

        for ent in es:
            self.assertTrue(isinstance(ent, model.Entitlement))
            self.assertTrue(len(ent.contents), 2)

        self.assertTrue(isinstance(es[0], model.Entitlement))


class TestFindContent(fixture.SubManFixture):
    def test(self):
        esb = EntitlementSourceBuilder()
        es = esb.ent_source()

        res = model.find_content(es, content_type="yum")
        self.assertEqual(len(res), 4)

    def test_product_tags(self):
        esb = EntitlementSourceBuilder()
        es = esb.ent_source()
        es.product_tags = []

        res = model.find_content(es, content_type="yum")
        self.assertEqual(len(res), 4)

    def test_product_tags_one_non_match(self):
        esb = EntitlementSourceBuilder()
        es = esb.ent_source()
        es.product_tags = ['something-random-tag']

        res = model.find_content(es, content_type="yum")
        self.assertEqual(len(res), 4)

    def test_product_tags_and_content_tags_match(self):
        content = create_mock_content(tags=['awesomeos-ostree-1'],
                                      content_type="ostree")
        content_list = [content]

        entitlement = model.Entitlement(contents=content_list)
        es = model.EntitlementSource()
        es._entitlements = [entitlement]
        es.product_tags = ['awesomeos-ostree-1']

        res = model.find_content(es, content_type="ostree")

        self.assertEqual(len(res), 1)
        self.assertEqual(res[0], content)

    def test_product_tags_and_content_tags_no_match(self):
        content1 = create_mock_content(tags=['awesomeos-ostree-23'],
                                      content_type="ostree")
        content2 = create_mock_content(name="more-test-content",
                                       tags=['awesomeos-ostree-24'],
                                       content_type="ostree")
        content_list = [content1, content2]

        entitlement = model.Entitlement(contents=content_list)
        es = model.EntitlementSource()
        es._entitlements = [entitlement]
        es.product_tags = ['awesomeos-ostree-1']

        res = model.find_content(es, content_type="ostree")

        self.assertEqual(len(res), 0)

    def test_product_tags_and_content_tags_no_match_no_product_tags(self):
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

        self.assertEqual(len(res), 0)

    def test_product_tags_and_content_tags_no_match_empty_product_tags(self):
        content1 = create_mock_content(tags=['awesomeos-ostree-23'],
                                      content_type="ostree")
        content2 = create_mock_content(name="more-test-content",
                                       tags=['awesomeos-ostree-24'],
                                       content_type="ostree")
        content_list = [content1, content2]

        entitlement = model.Entitlement(contents=content_list)
        es = model.EntitlementSource()
        es._entitlements = [entitlement]
        es.product_tags = []

        res = model.find_content(es, content_type="ostree")

        self.assertEqual(len(res), 0)

    def test_product_tags_and_content_tags_multiple_content_one_match(self):
        content1 = create_mock_content(tags=['awesomeos-ostree-23'],
                                      content_type="ostree")
        content2 = create_mock_content(name="more-test-content",
                                       tags=['awesomeos-ostree-1'],
                                       content_type="ostree")
        content_list = [content1, content2]

        entitlement = model.Entitlement(contents=content_list)
        es = model.EntitlementSource()
        es._entitlements = [entitlement]
        es.product_tags = ['awesomeos-ostree-1']

        res = model.find_content(es, content_type="ostree")

        self.assertEqual(len(res), 1)
        self.assertEqual(res[0], content2)

    def test_no_content_tags(self):
        content = create_mock_content(content_type="ostree")
        content_list = [content]

        entitlement = model.Entitlement(contents=content_list)
        es = model.EntitlementSource()
        es._entitlements = [entitlement]
        es.product_tags = ['awesomeos-ostree-1']

        res = model.find_content(es, content_type="ostree")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0], content)

    def test_find_container_content(self):
        container_content = create_mock_content(name="container_content",
                                                tags=["awesomeos-1"],
                                                content_type="containerImage")

        ent1 = model.Entitlement(contents=[container_content])

        ent_src = model.EntitlementSource()
        ent_src._entitlements = [ent1]
        ent_src.product_tags = ["awesomeos-1"]

        cont_list = model.find_content(ent_src,
            content_type='containerImage')
        self.assertEqual(1, len(cont_list))
        self.assertEqual('container_content', cont_list[0].name)

    def test_awesomeos_product_tags(self):
        product_tags_beta = ["awesomeos-ostree-beta", "awesomeos-ostree-beta-7"]
        product_tags_htb = ["awesomeos-ostree-htb", "awesomeos-ostree-htb-7"]
        product_tags_os = ["awesomeos-ostree", "awesomeos-ostree-7"]

        content_tags_beta = ["awesomeos-ostree-beta-7"]
        content_tags_htb = ["awesomeos-ostree-htb-7"]
        content_tags_os = ["awesomeos-ostree-7"]

        beta_ostree_content = create_mock_content(name="awesomeos_beta_ostree_content",
                                                  tags=content_tags_beta,
                                                  content_type="ostree")

        htb_ostree_content = create_mock_content(name="awesomeos_htb_ostree_content",
                                                 tags=content_tags_htb,
                                                 content_type="ostree")

        ostree_content = create_mock_content(name="awesomeos_ostree_content",
                                             tags=content_tags_os,
                                             content_type="ostree")

        ent = model.Entitlement(contents=[ostree_content,
                                          htb_ostree_content,
                                          beta_ostree_content])

        ent_src = model.EntitlementSource()
        ent_src._entitlements = [ent]

        # beta product
        ent_src.product_tags = product_tags_beta
        ostree_list = model.find_content(ent_src, content_type='ostree')
        self.assertEqual(1, len(ostree_list))
        self.assertEqual('awesomeos_beta_ostree_content', ostree_list[0].name)

        # htb products
        ent_src.product_tags = product_tags_htb
        ostree_list = model.find_content(ent_src, content_type='ostree')
        self.assertEqual(1, len(ostree_list))
        self.assertEqual('awesomeos_htb_ostree_content', ostree_list[0].name)

        ent_src.product_tags = product_tags_os
        ostree_list = model.find_content(ent_src, content_type='ostree')
        self.assertEqual(1, len(ostree_list))
        self.assertEqual('awesomeos_ostree_content', ostree_list[0].name)

        # beta product, no beta content
        ent = model.Entitlement(contents=[ostree_content])
        ent_src._entitlements = [ent]
        ent_src.product_tags = product_tags_beta
        ostree_list = model.find_content(ent_src, content_type='ostree')
        self.assertEqual(0, len(ostree_list))

        # awesomeos product, no os content, beta, htb content
        ent = model.Entitlement(contents=[htb_ostree_content,
                                          beta_ostree_content])
        ent_src._entitlements = [ent]
        ent_src.product_tags = product_tags_os
        ostree_list = model.find_content(ent_src, content_type='ostree')
        self.assertEqual(0, len(ostree_list))

        # awesomeos and beta product, all content
        ent = model.Entitlement(contents=[ostree_content,
                                          htb_ostree_content,
                                          beta_ostree_content])
        ent_src._entitlements = [ent]
        ent_src.product_tags = product_tags_os + product_tags_beta
        ostree_list = model.find_content(ent_src, content_type='ostree')
        # should be os and beta content
        self.assertEqual(2, len(ostree_list))
        content_names = [x.name for x in ostree_list]
        self.assertTrue('awesomeos_ostree_content' in content_names)
        self.assertTrue('awesomeos_beta_ostree_content' in content_names)
        self.assertFalse('awesomeos_htb_ostree_content' in content_names)

    def test_find_content_everything(self):
        yum_content = create_mock_content(name="yum_content",
                                          tags=["awesomeos-1"],
                                          content_type="yum")
        container_content = create_mock_content(name="container_content",
                                                tags=["awesomeos-1"],
                                                content_type="containerImage")
        ostree_content = create_mock_content(name="ostree_content",
                                             tags=["awesomeos-1"],
                                             content_type="ostree")

        ent1 = model.Entitlement(contents=[yum_content])
        ent2 = model.Entitlement(contents=[container_content, ostree_content])

        ent_src = model.EntitlementSource()
        ent_src._entitlements = [ent1, ent2]
        ent_src.product_tags = ["awesomeos-1"]

        yum_list = model.find_content(ent_src, content_type='yum')
        self.assertEqual(1, len(yum_list))
        self.assertEqual('yum_content', yum_list[0].name)

        cont_list = model.find_content(ent_src,
            content_type='containerImage')
        self.assertEqual(1, len(cont_list))
        self.assertEqual('container_content', cont_list[0].name)

        ostree_list = model.find_content(ent_src,
                                         content_type="ostree")
        self.assertEqual(1, len(ostree_list))
        self.assertEqual('ostree_content', ostree_list[0].name)
