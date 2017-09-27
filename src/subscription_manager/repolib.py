#
# -*- coding: utf-8 -*-#
from __future__ import print_function, division, absolute_import

# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
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

from iniparse import RawConfigParser as ConfigParser
import logging
import os
import string
import socket
import subscription_manager.injection as inj
from subscription_manager.cache import OverrideStatusCache, WrittenOverrideCache
from subscription_manager import utils
from subscription_manager import model
from subscription_manager.model import ent_cert
from six.moves.urllib.parse import parse_qs, urlparse, urlunparse, urlencode
from six.moves import configparser

from rhsm.config import initConfig, in_container

# FIXME: local imports

from subscription_manager.certlib import ActionReport, BaseActionInvoker
from subscription_manager.certdirectory import Path
from rhsmlib.services import config

from subscription_manager.i18n import ugettext as _

log = logging.getLogger(__name__)

conf = config.Config(initConfig())

ALLOWED_CONTENT_TYPES = ["yum"]

ZYPPER_REPO_DIR = '/etc/rhsm/zypper.repos.d'


def manage_repos_enabled():

    try:
        manage_repos = conf['rhsm'].get_int('manage_repos')
    except ValueError as e:
        log.exception(e)
        return True
    except configparser.Error as e:
        log.exception(e)
        return True
    else:
        if manage_repos is None:
            return True

    return bool(manage_repos)


class YumPluginManager(object):
    """
    Instance of this class is used for automatic enabling of yum plugins.
    """

    YUM_PLUGIN_DIR = '/etc/yum/pluginconf.d'

    # List of yum plugins in YUM_PLUGIN_DIR which are automatically enabled
    # during sub-man CLI/GUI start
    YUM_PLUGINS = ['subscription-manager', 'product-id']

    YUM_PLUGIN_ENABLED = 1
    YUM_PLUGIN_DISABLED = 0

    @staticmethod
    def is_auto_enable_enabled():
        """
        Automatic enabling of yum plugins can be explicitly disabled in /etc/rhsm/rhsm.conf
        Try to get this configuration.
        :return: True, when auto_enable_yum_plugins is enabled. Otherwise False is returned.
        """
        try:
            auto_enable_yum_plugins = conf['rhsm'].get_int('auto_enable_yum_plugins')
        except ValueError as err:
            log.exception(err)
            auto_enable_yum_plugins = True
        except configparser.Error as err:
            log.exception(err)
            auto_enable_yum_plugins = True
        else:
            if auto_enable_yum_plugins is None:
                auto_enable_yum_plugins = True
        return bool(auto_enable_yum_plugins)

    @staticmethod
    def warning_message(enabled_yum_plugins):
        message = _('The yum plugins: %s were automatically enabled for the benefit of '
                    'Red Hat Subscription Management. If not desired, use '
                    '"subscription-manager config --rhsm.auto_enable_yum_plugins=0" to '
                    'block this behavior.\n') % ', '.join(enabled_yum_plugins)
        return message

    @classmethod
    def enable_yum_plugins(cls):
        """
        This function tries to enable yum plugins: subscription-manager and product-id.
        It takes no action, when automatic enabling of yum plugins is disabled in rhsm.conf.
        :return: It returns list of enabled plugins
        """

        # When user doesn't want to automatically enable yum plugins, then return empty list
        if cls.is_auto_enable_enabled() is False:
            log.info('The rhsm.auto_enable_yum_plugins is disabled. Skipping the enablement of yum plugins.')
            return []

        log.debug('The rhsm.auto_enable_yum_plugins is enabled')

        # List of successfully enabled plugins
        enabled_yum_plugins = []

        # Go through the list of yum plugins and try to find configuration
        # file of these plugins.
        for yum_plugin_name in cls.YUM_PLUGINS:
            yum_plugin_file_name = cls.YUM_PLUGIN_DIR + '/' + yum_plugin_name + '.conf'
            yum_plugin_config = ConfigParser()
            try:
                result = yum_plugin_config.read(yum_plugin_file_name)
            except Exception as err:
                # Capture all errors during reading yum plugin conf file
                # report them and skip this conf file
                log.error(
                    "Error during reading yum plugin config file '%s': %s. Skipping this file." %
                    (yum_plugin_file_name, err)
                )
                continue

            if len(result) == 0:
                log.info('Configuration file of yum plugin: "%s" cannot be read' % yum_plugin_file_name)
                continue

            is_plugin_enabled = False
            if not yum_plugin_config.has_section('main'):
                log.warn(
                    'Configuration file of yum plugin: "%s" does not include main section. Adding main section.' %
                    yum_plugin_file_name
                )
                yum_plugin_config.add_section('main')
            elif yum_plugin_config.has_option('main', 'enabled'):
                try:
                    # Options 'enabled' can be 0 or 1
                    is_plugin_enabled = yum_plugin_config.getint('main', 'enabled')
                except ValueError:
                    try:
                        # Options 'enabled' can be also: true or false
                        is_plugin_enabled = yum_plugin_config.getboolean('main', 'enabled')
                    except ValueError:
                        log.warn(
                            "File %s has wrong value of options: 'enabled' in section: 'main' (not a int nor boolean)" %
                            yum_plugin_file_name
                        )

            if is_plugin_enabled == cls.YUM_PLUGIN_ENABLED:
                log.debug('Yum plugin: "%s" already enabled. Nothing to do.' % yum_plugin_file_name)
            else:
                log.warn('Enabling yum plugin: "%s".' % yum_plugin_file_name)
                # Change content of plugin configuration file and enable this plugin.
                with open(yum_plugin_file_name, 'w') as cfg_file:
                    yum_plugin_config.set('main', 'enabled', cls.YUM_PLUGIN_ENABLED)
                    yum_plugin_config.write(cfg_file)
                enabled_yum_plugins.append(yum_plugin_file_name)

        return enabled_yum_plugins


class RepoActionInvoker(BaseActionInvoker):
    """Invoker for yum repo updating related actions."""
    def __init__(self, cache_only=False, locker=None):
        super(RepoActionInvoker, self).__init__(locker=locker)
        self.cache_only = cache_only
        self.identity = inj.require(inj.IDENTITY)

    def _do_update(self):
        action = RepoUpdateActionCommand(cache_only=self.cache_only)
        res = action.perform()
        return res

    def is_managed(self, repo):
        action = RepoUpdateActionCommand(cache_only=self.cache_only)
        return repo in [c.label for c in action.matching_content()]

    def get_repos(self, apply_overrides=True):
        action = RepoUpdateActionCommand(cache_only=self.cache_only,
                                  apply_overrides=apply_overrides)
        repos = action.get_unique_content()

        current = set()
        # Add the current repo data
        yum_repo_file = YumRepoFile()
        yum_repo_file.read()
        server_value_repo_file = YumRepoFile('var/lib/rhsm/repo_server_val/')
        server_value_repo_file.read()
        for repo in repos:
            existing = yum_repo_file.section(repo.id)
            server_value_repo = server_value_repo_file.section(repo.id)
            # we need a repo in the server val file to match any in
            # the main repo definition file
            if server_value_repo is None:
                server_value_repo = repo
                server_value_repo_file.add(repo)
            if existing is None:
                current.add(repo)
            else:
                action.update_repo(existing, repo, server_value_repo)
                current.add(existing)

        return current

    def get_repo_file(self):
        yum_repo_file = YumRepoFile()
        return yum_repo_file.path

    @classmethod
    def delete_repo_file(cls):
        yum_repo_file = YumRepoFile()
        if os.path.exists(yum_repo_file.path):
            os.unlink(yum_repo_file.path)

        # if we have zypper repo, remove it too.
        if os.path.exists(ZYPPER_REPO_DIR):
            zypper_repo_file = ZypperRepoFile()
            if os.path.exists(zypper_repo_file.path):
                os.unlink(zypper_repo_file.path)

        # When the repo is removed, also remove the override tracker
        WrittenOverrideCache.delete_cache()


# This is $releasever specific, but expanding other vars would be similar,
# just the marker, and get_expansion would change
#
# For example, for full craziness, we could expand facts in urls...
class YumReleaseverSource(object):
    """
    Contains a ReleaseStatusCache and releasever helpers.

    get_expansion() gets 'release' from consumer info from server,
    using the cache as required.
    """
    marker = "$releasever"
    # if all eles fails the default is to leave the marker un expanded
    default = marker

    def __init__(self):

        self.release_status_cache = inj.require(inj.RELEASE_STATUS_CACHE)
        self._expansion = None

        self.identity = inj.require(inj.IDENTITY)
        self.cp_provider = inj.require(inj.CP_PROVIDER)
        self.uep = self.cp_provider.get_consumer_auth_cp()

    # FIXME: these guys are really more of model helpers for the object
    #        represent a release.
    @staticmethod
    def is_not_empty(expansion):
        if expansion is None or len(expansion) == 0:
            return False
        return True

    @staticmethod
    def is_set(result):
        """Check result for existing, and having a non empty value.

        Return True if result has a non empty, non null result['releaseVer']

        False indicates we don't know or it is not set.
        """
        if result is None:
            return False
        try:
            release = result['releaseVer']
            return YumReleaseverSource.is_not_empty(release)
        except Exception:
            return False

    def get_expansion(self):
        # mem cache
        if self._expansion:
            return self._expansion
        # See BZ 1366799.
        # Do not check for any release version set for the host consumer
        # if we are in a container (containers are not considered to be the
        # same consumer as the host they run on. They only have the same
        # access to content as the host they run on.)
        result = None
        if not in_container():
            result = self.release_status_cache.read_status(self.uep,
                                                           self.identity.uuid)

        # status cache returned None, which points to a failure.
        # Since we only have one value, use the default there and cache it
        # NOTE: the _expansion caches exists for the lifetime of the object,
        #       so a new created YumReleaseverSource needs to be created when
        #       you think there may be a new release set. We assume it will be
        #       the same for the lifetime of a RepoUpdateActionCommand
        if not self.is_set(result) or result is None:
            # we got a result indicating we don't know the release, use the
            # default. This could be server error or just an "unset" release.
            self._expansion = self.default
            return self._expansion

        self._expansion = result['releaseVer']
        return self._expansion


class RepoUpdateActionCommand(object):
    """UpdateAction for yum repos.

    Update yum repos when triggered. Generates yum repo config
    based on:
        - entitlement certs
        - repo overrides
        - rhsm config
        - yum config
        - manual changes made to "redhat.repo".

    If the system in question has a zypper repo directory, will also generate
    zypper repo config.

    Returns an RepoActionReport.
    """
    def __init__(self, cache_only=False, apply_overrides=True):
        self.identity = inj.require(inj.IDENTITY)

        # These should probably move closer their use
        self.ent_dir = inj.require(inj.ENT_DIR)
        self.prod_dir = inj.require(inj.PROD_DIR)

        self.ent_source = ent_cert.EntitlementDirEntitlementSource()

        self.cp_provider = inj.require(inj.CP_PROVIDER)
        self.uep = self.cp_provider.get_consumer_auth_cp()

        self.manage_repos = 1
        self.apply_overrides = apply_overrides
        self.manage_repos = manage_repos_enabled()

        self.release = None
        self.overrides = {}
        self.override_supported = False
        try:
            self.override_supported = bool(self.identity.is_valid() and self.uep and self.uep.supports_resource('content_overrides'))
        except socket.error as e:
            # swallow the error to fix bz 1298327
            log.exception(e)
            pass
        self.written_overrides = WrittenOverrideCache()

        # FIXME: empty report at the moment, should be changed to include
        # info about updated repos
        self.report = RepoActionReport()
        self.report.name = "Repo updates"
        # If we are not registered, skip trying to refresh the
        # data from the server
        if not self.identity.is_valid():
            return

        # NOTE: if anything in the RepoActionInvoker init blocks, and it
        #       could, yum could still block. The closest thing to an
        #       event loop we have is the while True: sleep() in lock.py:Lock.acquire()

        # Only attempt to update the overrides if they are supported
        # by the server.
        if self.override_supported:
            self.written_overrides.read_cache_only()

            try:
                override_cache = inj.require(inj.OVERRIDE_STATUS_CACHE)
            except KeyError:
                override_cache = OverrideStatusCache()

            if cache_only:
                status = override_cache.read_cache_only()
            else:
                status = override_cache.load_status(self.uep, self.identity.uuid)

            for item in status or []:
                # Don't iterate through the list
                if item['contentLabel'] not in self.overrides:
                    self.overrides[item['contentLabel']] = {}
                self.overrides[item['contentLabel']][item['name']] = item['value']

    def perform(self):
        # Load the RepoFile from disk, this contains all our managed yum repo sections:
        yum_repo_file = YumRepoFile()
        server_value_repo_file = YumRepoFile('var/lib/rhsm/repo_server_val/')
        zypper_repo_file = None
        if os.path.exists(ZYPPER_REPO_DIR):
            zypper_repo_file = ZypperRepoFile()

        # the [rhsm] manage_repos can be overridden to disable generation of the
        # redhat.repo file:
        if not self.manage_repos:
            log.debug("manage_repos is 0, skipping generation of: %s" %
                    yum_repo_file.path)
            if yum_repo_file.exists():
                log.info("Removing %s due to manage_repos configuration." %
                        yum_repo_file.path)
                RepoActionInvoker.delete_repo_file()
            return 0

        yum_repo_file.read()
        server_value_repo_file.read()
        if zypper_repo_file:
            zypper_repo_file.read()
        valid = set()

        # Iterate content from entitlement certs, and create/delete each section
        # in the RepoFile as appropriate:
        for cont in self.get_unique_content():
            valid.add(cont.id)
            existing = yum_repo_file.section(cont.id)
            server_value_repo = server_value_repo_file.section(cont.id)
            if server_value_repo is None:
                server_value_repo = cont
                server_value_repo_file.add(cont)
            if existing is None:
                yum_repo_file.add(cont)
                self.report_add(cont)
            else:
                # Updates the existing repo with new content
                self.update_repo(existing, cont, server_value_repo)
                yum_repo_file.update(existing)
                server_value_repo_file.update(server_value_repo)
                self.report_update(existing)

            if zypper_repo_file:  # no reporting for zypper, already reported for yum
                zypper_cont = self._zypper_content(cont)
                existing = zypper_repo_file.section(zypper_cont.id)
                if existing is None:
                    zypper_repo_file.add(zypper_cont)
                else:
                    zypper_repo_file.update(zypper_cont)

        for section in yum_repo_file.sections():
            if section not in valid:
                self.report_delete(section)
                yum_repo_file.delete(section)
                server_value_repo_file.delete(section)
                if zypper_repo_file:
                    zypper_repo_file.delete(section)

        # Write new RepoFile to disk:
        yum_repo_file.write()
        server_value_repo_file.write()
        if zypper_repo_file:
            zypper_repo_file.write()
        if self.override_supported:
            # Update with the values we just wrote
            self.written_overrides.overrides = self.overrides
            self.written_overrides.write_cache()
        log.info("repos updated: %s" % self.report)
        return self.report

    def _zypper_content(self, content):
        zypper_cont = content.copy()
        sslverify = zypper_cont['sslverify']
        sslcacert = zypper_cont['sslcacert']
        sslclientkey = zypper_cont['sslclientkey']
        sslclientcert = zypper_cont['sslclientcert']
        proxy = zypper_cont['proxy']
        proxy_username = zypper_cont['proxy_username']
        proxy_password = zypper_cont['proxy_password']

        del zypper_cont['sslverify']
        del zypper_cont['sslcacert']
        del zypper_cont['sslclientkey']
        del zypper_cont['sslclientcert']
        del zypper_cont['proxy']
        del zypper_cont['proxy_username']
        del zypper_cont['proxy_password']
        # NOTE looks like metadata_expire and ui_repoid_vars are ignored by zypper

        # clean up data for zypper
        if zypper_cont['gpgkey'] in ['https://', 'http://']:
            del zypper_cont['gpgkey']

        baseurl = zypper_cont['baseurl']
        parsed = urlparse(baseurl)
        zypper_query_args = parse_qs(parsed.query)
        if sslverify and sslverify in ['1']:
            zypper_query_args['ssl_verify'] = 'host'
        if sslcacert:
            zypper_query_args['ssl_capath'] = os.path.dirname(sslcacert)
        if sslclientkey:
            zypper_query_args['ssl_clientkey'] = sslclientkey
        if sslclientcert:
            zypper_query_args['ssl_clientcert'] = sslclientcert
        if proxy:
            zypper_query_args['proxy'] = proxy
        if proxy_username:
            zypper_query_args['proxyuser'] = proxy_username
        if proxy_password:
            zypper_query_args['proxypass'] = proxy_password
        zypper_query = urlencode(zypper_query_args)

        new_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, zypper_query, parsed.fragment))
        zypper_cont['baseurl'] = new_url

        return zypper_cont

    def get_unique_content(self):
        # FIXME Shouldn't this skip all of the repo updating?
        if not self.manage_repos:
            return []

        # baseurl and ca_cert could be "CDNInfo" or
        # bundle with "ConnectionInfo" etc
        baseurl = conf['rhsm']['baseurl']
        ca_cert = conf['rhsm']['repo_ca_cert']

        content_list = self.get_all_content(baseurl, ca_cert)

        # assumes items in content_list are hashable
        return set(content_list)

    # Expose as public API for RepoActionInvoker.is_managed, since that
    # is used by Openshift tooling.
    # See https://bugzilla.redhat.com/show_bug.cgi?id=1223038
    def matching_content(self):
        return model.find_content(self.ent_source,
                                  content_type="yum")

    def get_all_content(self, baseurl, ca_cert):
        matching_content = self.matching_content()
        content_list = []

        # avoid checking for release/etc if there is no matching_content
        if not matching_content:
            return content_list

        # wait until we know we have content before fetching
        # release. We could make YumReleaseverSource understand
        # cache_only as well.
        release_source = YumReleaseverSource()

        for content in matching_content:
            repo = Repo.from_ent_cert_content(content, baseurl, ca_cert,
                                              release_source)

            # overrides are yum repo only at the moment, but
            # content sources will likely need to learn how to
            # apply overrides as well, perhaps generically
            if self.override_supported and self.apply_overrides:
                repo = self._set_override_info(repo)

            content_list.append(repo)

        return content_list

    def _set_override_info(self, repo):
        # In the disconnected case, self.overrides will be an empty list

        for name, value in list(self.overrides.get(repo.id, {}).items()):
            repo[name] = value

        return repo

    def _is_overridden(self, repo, key):
        return key in self.overrides.get(repo.id, {})

    def _was_overridden(self, repo, key, value):
        written_value = self.written_overrides.overrides.get(repo.id, {}).get(key)
        # Compare values as strings to avoid casting problems from io
        return written_value is not None and value is not None and str(written_value) == str(value)

    def _build_props(self, old_repo, new_repo):
        result = {}
        all_keys = list(old_repo.keys()) + list(new_repo.keys())
        for key in all_keys:
            result[key] = Repo.PROPERTIES.get(key, (1, None))
        return result

    def update_repo(self, old_repo, new_repo, server_value_repo=None):
        """
        Checks an existing repo definition against a potentially updated
        version created from most recent entitlement certificates and
        configuration. Creates, updates, and removes properties as
        appropriate and returns the number of changes made. (if any)
        """
        changes_made = 0
        if server_value_repo is None:
            server_value_repo = {}

        for key, (mutable, _default) in list(self._build_props(old_repo, new_repo).items()):
            new_val = new_repo.get(key)

            # Mutable properties should be added if not currently defined,
            # otherwise left alone. However if we see that the property was overridden
            # but that override has since been removed, we need to revert to the default
            # value.
            if mutable and not self._is_overridden(old_repo, key) \
                    and not self._was_overridden(old_repo, key, old_repo.get(key)):
                if (new_val is not None) and (not old_repo.get(key) or
                        old_repo.get(key) == server_value_repo.get(key)):
                    if old_repo.get(key) == new_val:
                        continue
                    old_repo[key] = new_val
                    changes_made += 1

            # Immutable properties should be always be added/updated,
            # and removed if undefined in the new repo definition.
            else:
                if new_val is None or (str(new_val).strip() == ""):
                    # Immutable property should be removed:
                    if key in list(old_repo.keys()):
                        del old_repo[key]
                        changes_made += 1
                    continue

                # Unchanged:
                if old_repo.get(key) == new_val:
                    continue

                old_repo[key] = new_val
                changes_made += 1

            if (mutable and new_val is not None):
                server_value_repo[key] = new_val

        return changes_made

    def report_update(self, repo):
        self.report.repo_updates.append(repo)

    def report_add(self, repo):
        self.report.repo_added.append(repo)

    def report_delete(self, section):
        self.report.repo_deleted.append(section)


class RepoActionReport(ActionReport):
    """Report class for reporting yum repo updates."""
    name = u"Repo Updates"

    def __init__(self):
        super(RepoActionReport, self).__init__()
        self.repo_updates = []
        self.repo_added = []
        self.repo_deleted = []

    def updates(self):
        """How many repos were updated"""
        return len(self.repo_updates) + len(self.repo_added) + len(self.repo_deleted)

    def format_repos_info(self, repos, formatter):
        indent = '    '
        if not repos:
            return u'%s<NONE>' % indent

        r = []
        for repo in repos:
            r.append(u"%s%s" % (indent, formatter(repo)))
        return u'\n'.join(r)

    def repo_format(self, repo):
        msg = u"[id:%s %s]" % (repo.id,
                               repo['name'])
        return msg.encode('utf8')

    def section_format(self, section):
        return u"[%s]" % section

    def format_repos(self, repos):
        return self.format_repos_info(repos, self.repo_format)

    def format_sections(self, sections):
        return self.format_repos_info(sections, self.section_format)

    def __unicode__(self):
        s = [_('Repo updates') + '\n']
        s.append(_('Total repo updates: %d') % self.updates())
        s.append(_('Updated'))
        s.append(self.format_repos(self.repo_updates))
        s.append(_('Added (new)'))
        s.append(self.format_repos(self.repo_added))
        s.append(_('Deleted'))
        # deleted are former repo sections, but they are the same type
        s.append(self.format_sections(self.repo_deleted))
        return u'\n'.join(s)

    def __str__(self):  # TODO use six.python_2_unicode_compatible instead
        return self.__unicode__().encode('utf-8')


class Repo(dict):
    # (name, mutable, default) - The mutability information is only used in disconnected cases
    PROPERTIES = {
            'name': (0, None),
            'baseurl': (0, None),
            'enabled': (1, '1'),
            'gpgcheck': (1, '1'),
            'gpgkey': (0, None),
            'sslverify': (1, '1'),
            'sslcacert': (0, None),
            'sslclientkey': (0, None),
            'sslclientcert': (0, None),
            'metadata_expire': (1, None),
            'proxy': (0, None),
            'proxy_username': (0, None),
            'proxy_password': (0, None),
            'ui_repoid_vars': (0, None)}

    def __init__(self, repo_id, existing_values=None):
        # existing_values is a list of 2-tuples
        existing_values = existing_values or []
        self.id = self._clean_id(repo_id)

        # used to store key order, so we can write things out in the order
        # we read them from the config.
        self._order = []

        for key, value in existing_values:
            # only set keys that have a non-empty value, to not clutter the
            # file.
            if value:
                self[key] = value

        # NOTE: This sets the above properties to the default values even if
        # they are not defined on disk. i.e. these properties will always
        # appear in this dict, but their values may be None.
        for k, (_m, d) in list(self.PROPERTIES.items()):
            if k not in list(self.keys()):
                self[k] = d

    def copy(self):
        new_repo = Repo(self.id)
        for key, value in list(self.items()):
            new_repo[key] = value
        return new_repo

    @classmethod
    def from_ent_cert_content(cls, content, baseurl, ca_cert, release_source):
        """Create an instance of Repo() from an ent_cert.EntitlementCertContent().

        And the other out of band info we need including baseurl, ca_cert, and
        the release version string.
        """
        repo = cls(content.label)

        repo['name'] = content.name

        if content.enabled:
            repo['enabled'] = "1"
        else:
            repo['enabled'] = "0"

        expanded_url_path = Repo._expand_releasever(release_source, content.url)
        repo['baseurl'] = utils.url_base_join(baseurl, expanded_url_path)

        # Extract the variables from the url
        repo_parts = repo['baseurl'].split("/")
        repoid_vars = [part[1:] for part in repo_parts if part.startswith("$")]
        if repoid_vars:
            repo['ui_repoid_vars'] = " ".join(repoid_vars)

        # If no GPG key URL is specified, turn gpgcheck off:
        gpg_url = content.gpg
        if not gpg_url:
            repo['gpgkey'] = ""
            repo['gpgcheck'] = '0'
        else:
            repo['gpgkey'] = utils.url_base_join(baseurl, gpg_url)
            # Leave gpgcheck as the default of 1

        repo['sslclientkey'] = content.cert.key_path()
        repo['sslclientcert'] = content.cert.path
        repo['sslcacert'] = ca_cert
        repo['metadata_expire'] = content.metadata_expire

        repo = Repo._set_proxy_info(repo)

        return repo

    @staticmethod
    def _set_proxy_info(repo):
        proxy = ""

        # Worth passing in proxy config info to from_ent_cert_content()?
        # That would decouple Repo some
        proxy_host = conf['server']['proxy_hostname']
        # proxy_port as string is fine here
        proxy_port = conf['server']['proxy_port']
        if proxy_host != "":
            proxy = "https://%s" % proxy_host
            if proxy_port != "":
                proxy = "%s:%s" % (proxy, proxy_port)

        # These could be empty string, in which case they will not be
        # set in the yum repo file:
        repo['proxy'] = proxy
        repo['proxy_username'] = conf['server']['proxy_user']
        repo['proxy_password'] = conf['server']['proxy_password']

        return repo

    @staticmethod
    def _expand_releasever(release_source, contenturl):
        # no $releasever to expand
        if release_source.marker not in contenturl:
            return contenturl

        expansion = release_source.get_expansion()

        # NOTE: This is building a url from external info
        #       so likely needs more validation. In our case, the
        #       external source is trusted (release list from tls
        #       mutually authed cdn, or a tls mutual auth api)
        # NOTE: The on disk cache is more vulnerable, since it is
        #       trusted.
        return contenturl.replace(release_source.marker,
                                  expansion)

    def _clean_id(self, repo_id):
        """
        Format the config file id to contain only characters that yum expects
        (we'll just replace 'bad' chars with -)
        """
        new_id = ""
        valid_chars = string.ascii_letters + string.digits + "-_.:"
        for byte in repo_id:
            if byte not in valid_chars:
                new_id += '-'
            else:
                new_id += byte

        return new_id

    def items(self):
        """
        Called when we fetch the items for this yum repo to write to disk.
        """
        # Skip anything set to 'None' or empty string, as this is likely
        # not intended for a yum repo file. None can result here if the
        # default is None, or the entitlement certificate did not have the
        # value set.
        #
        # all values will be in _order, since the key has to have been set
        # to get into our dict.
        return tuple([(k, self[k]) for k in self._order if
                     k in self and self[k]])

    def __setitem__(self, key, value):
        if key not in self._order:
            self._order.append(key)
        dict.__setitem__(self, key, value)

    def __str__(self):
        s = []
        s.append('[%s]' % self.id)
        for k in self.PROPERTIES:
            v = self.get(k)
            if v is None:
                continue
            s.append('%s=%s' % (k, v))

        return '\n'.join(s)

    def __eq__(self, other):
        return (self.id == other.id)

    def __hash__(self):
        return hash(self.id)


class TidyWriter(object):

    """
    ini file reader that removes successive newlines,
    and adds a trailing newline to the end of a file.

    used to keep our repo file clean after removals and additions of
    new sections, as iniparser's tidy function is not available in all
    versions.
    """

    def __init__(self, backing_file):
        self.backing_file = backing_file
        self.ends_with_newline = False
        self.writing_empty_lines = False

    def write(self, line):
        lines = line.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            if line == "":
                if i != len(lines) - 1:
                    if not self.writing_empty_lines:
                        self.backing_file.write("\n")
                    self.writing_empty_lines = True
            else:
                self.writing_empty_lines = False
                self.backing_file.write(line)
                if i != len(lines) - 1:
                    self.backing_file.write("\n")

            i += 1

        if lines[-1] == "":
            self.ends_with_newline = True
        else:
            self.ends_with_newline = False

    def close(self):
        if not self.ends_with_newline:
            self.backing_file.write("\n")


class RepoFileBase(object):

    def __init__(self, path=None, name=None):
        # note PATH get's expanded with chroot info, etc
        path = path or self.PATH
        name = name or self.NAME
        self.path = Path.join(path, name)
        self.repos_dir = Path.abs(path)
        self.manage_repos = manage_repos_enabled()
        # Simulate manage repos turned off if no yum.repos.d directory exists.
        # This indicates the corresponding package manager is not installed so
        # clearly no need for us to manage repos.
        if not self.path_exists(self.repos_dir):
            log.warn("%s does not exist, turning manage_repos off." %
                    self.repos_dir)
            self.manage_repos = False
        else:
            self.create()

    # Easier than trying to mock/patch os.path.exists
    def path_exists(self, path):
        "wrapper around os.path.exists"
        return os.path.exists(path)

    def exists(self):
        return self.path_exists(self.path)

    def create(self):
        if self.path_exists(self.path) or not self.manage_repos:
            return
        with open(self.path, 'w') as f:
            f.write(self.REPOFILE_HEADER)


class YumRepoFile(RepoFileBase, ConfigParser):

    PATH = 'etc/yum.repos.d/'
    NAME = 'redhat.repo'
    REPOFILE_HEADER = """#
# Certificate-Based Repositories
# Managed by (rhsm) subscription-manager
#
# *** This file is auto-generated.  Changes made here will be over-written. ***
# *** Use "subscription-manager repo-override --help" if you wish to make changes. ***
#
# If this file is empty and this system is subscribed consider
# a "yum repolist" to refresh available repos
#
"""

    def __init__(self, path=None, name=None):
        ConfigParser.__init__(self)
        RepoFileBase.__init__(self, path, name)

    def read(self):
        ConfigParser.read(self, self.path)

    def _configparsers_equal(self, otherparser):
        if set(otherparser.sections()) != set(self.sections()):
            return False

        for section in self.sections():
            # Sometimes we end up with ints, but values must be strings to compare
            current_items = dict([(str(k), str(v)) for (k, v) in self.items(section)])
            if current_items != dict(otherparser.items(section)):
                return False
        return True

    def _has_changed(self):
        '''
        Check if the version on disk is different from what we have loaded
        '''
        on_disk = ConfigParser()
        on_disk.read(self.path)
        return not self._configparsers_equal(on_disk)

    def write(self):
        if not self.manage_repos:
            log.debug("Skipping write due to manage_repos setting: %s" %
                    self.path)
            return
        if self._has_changed():
            f = open(self.path, 'w')
            tidy_writer = TidyWriter(f)
            ConfigParser.write(self, tidy_writer)
            tidy_writer.close()
            f.close()

    def add(self, repo):
        self.add_section(repo.id)
        self.update(repo)

    def delete(self, section):
        return self.remove_section(section)

    def update(self, repo):
        # Need to clear out the old section to allow unsetting options:
        # don't use remove section though, as that will reorder sections,
        # and move whitespace around (resulting in more and more whitespace
        # as time progresses).
        for (k, v) in self.items(repo.id):
            self.remove_option(repo.id, k)

        for k, v in list(repo.items()):
            ConfigParser.set(self, repo.id, k, v)

    def section(self, section):
        if self.has_section(section):
            return Repo(section, self.items(section))


class ZypperRepoFile(YumRepoFile):

    PATH = 'etc/rhsm/zypper.repos.d'
    NAME = 'redhat.repo'
    REPOFILE_HEADER = """#
# Certificate-Based Repositories
# Managed by (rhsm) subscription-manager
#
# *** This file is auto-generated.  Changes made here will be over-written. ***
# *** Use "subscription-manager repo-override --help" if you wish to make changes. ***
#
# If this file is empty and this system is subscribed consider
# a "zypper lr" to refresh available repos
#
"""

    def __init__(self, path=None, name=None):
        super(ZypperRepoFile, self).__init__(path, name)
