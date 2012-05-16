#
# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#
import unittest

from subscription_manager import listing

listing_empty = ""

listing_just_comments = """
#
#
"""

listing_comment_not_first = """
    # something
"""

listing_empty_lines = """


"""

listing_one_release = """
6
"""

listing_one_release_no_eol = """
6"""

listing_multiple_releases = """
6
7
8
"""

listing_multiple_with_comments = """
6
# whatevs
7
8
"""

listing_multiple_unsorted = """
7
6
8
"""

listing_multiple_non_int = """
6
6Awesome
7Amazing
8
"""


class ListingTests(unittest.TestCase):

    def setUp(self):
        self.listing = listing.ListingFile(self.data)


class TestEmptyListing(ListingTests):
    data = listing_empty

    def testEmpty(self):
        self.assertEquals([], self.listing.get_releases())


class TestJustCommentListing(TestEmptyListing):
    data = listing_just_comments


class TestNotFirstCommentListing(TestEmptyListing):
    data = listing_comment_not_first


class TestEmptyLinesListing(TestEmptyListing):
    data = listing_empty_lines


class TestOneRelease(ListingTests):
    data = listing_one_release

    def testOneRelease(self):
        self.assertEquals(['6'], self.listing.get_releases())


class TestOneReleaseNoEOL(TestOneRelease):
    data = listing_one_release_no_eol


class TestMultipleReleases(ListingTests):
    data = listing_multiple_releases

    def testMultipleReleases(self):
        self.assertEquals(['6', '7', '8'], self.listing.get_releases())


class TestMultipleReleaseWithComments(TestMultipleReleases):
    data = listing_multiple_with_comments


class TestMultipleReleasesUnsorted(TestMultipleReleases):
    data = listing_multiple_unsorted


class TestMultipleNonInt(ListingTests):
    data = listing_multiple_non_int

    def testMultipleReleasesNonInt(self):
        self.assertEquals(['6', '6Awesome', '7Amazing', '8'], self.listing.get_releases())
