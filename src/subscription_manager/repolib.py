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
import subscription_manager.injection as inj
from subscription_manager.cache import OverrideStatusCache, WrittenOverrideCache
from subscription_manager import model
from subscription_manager.model import ent_cert
from subscription_manager.repofile import Repo, manage_repos_enabled, get_repo_file_classes
from subscription_manager.repofile import YumRepoFile
from subscription_manager.capabilities import ServerCache

from rhsm.config import initConfig, in_container
import six
from six.moves import configparser

# FIXME: local imports

from subscription_manager.certlib import ActionReport, BaseActionInvoker
from rhsmlib.services import config

from subscription_manager.i18n import ugettext as _

log = logging.getLogger(__name__)

conf = config.Config(initConfig())

ALLOWED_CONTENT_TYPES = ["yum", "deb"]


class YumPluginManager(object):
    """
    Instance of this class is used for automatic enabling of yum plugins.
    """

    YUM_PLUGIN_DIR = '/etc/yum/pluginconf.d'
    DNF_PLUGIN_DIR = '/etc/dnf/plugins'

    # List of yum plugins in YUM_PLUGIN_DIR which are automatically enabled
    # during sub-man CLI/GUI start
    PLUGINS = ['subscription-manager', 'product-id']

    PLUGIN_ENABLED = 1
    PLUGIN_DISABLED = 0

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
        message = _('The yum/dnf plugins: %s were automatically enabled for the benefit of '
                    'Red Hat Subscription Management. If not desired, use '
                    '"subscription-manager config --rhsm.auto_enable_yum_plugins=0" to '
                    'block this behavior.') % ', '.join(enabled_yum_plugins)
        return message

    @classmethod
    def _enable_plugins(cls, pkg_mgr_name, plugin_dir):
        """
        This class method tries to enable plugins for DNF or YUM
        :param pkg_mgr_name: It can be "dnf" or "yum"
        :type pkg_mgr_name: str
        :param plugin_dir: Directory with configuration files for (dnf/yum) plugins
        :type plugin_dir: str
        :return:
        """
        # List of successfully enabled plugins
        enabled_lugins = []
        # Go through the list of yum plugins and try to find configuration
        # file of these plugins.
        for plugin_name in cls.PLUGINS:
            plugin_file_name = plugin_dir + '/' + plugin_name + '.conf'
            plugin_config = ConfigParser()
            try:
                result = plugin_config.read(plugin_file_name)
            except Exception as err:
                # Capture all errors during reading yum plugin conf file
                # report them and skip this conf file
                log.error(
                    "Error during reading %s plugin config file '%s': %s. Skipping this file." %
                    (pkg_mgr_name, plugin_file_name, err)
                )
                continue

            if len(result) == 0:
                log.warn('Configuration file of %s plugin: "%s" cannot be read' %
                         (pkg_mgr_name, plugin_file_name))
                continue

            is_plugin_enabled = False
            if not plugin_config.has_section('main'):
                log.warning(
                    'Configuration file of %s plugin: "%s" does not include main section. Adding main section.' %
                    (pkg_mgr_name, plugin_file_name)
                )
                plugin_config.add_section('main')
            elif plugin_config.has_option('main', 'enabled'):
                try:
                    # Options 'enabled' can be 0 or 1
                    is_plugin_enabled = plugin_config.getint('main', 'enabled')
                except ValueError:
                    try:
                        # Options 'enabled' can be also: true or false
                        is_plugin_enabled = plugin_config.getboolean('main', 'enabled')
                    except ValueError:
                        log.warning(
                            "File %s has wrong value of options: 'enabled' in section: 'main' (not a int nor boolean)" %
                            plugin_file_name
                        )

            if is_plugin_enabled == cls.PLUGIN_ENABLED:
                log.debug('%s plugin: "%s" already enabled. Nothing to do.' %
                          (pkg_mgr_name, plugin_file_name))
            else:
                log.warning('Enabling %s plugin: "%s".' % (pkg_mgr_name, plugin_file_name))
                # Change content of plugin configuration file and enable this plugin.
                with open(plugin_file_name, 'w') as cfg_file:
                    plugin_config.set('main', 'enabled', cls.PLUGIN_ENABLED)
                    plugin_config.write(cfg_file)
                enabled_lugins.append(plugin_file_name)

        return enabled_lugins

    @classmethod
    def enable_pkg_plugins(cls):
        """
        This function tries to enable dnf/yum plugins: subscription-manager and product-id.
        It takes no action, when automatic enabling of yum plugins is disabled in rhsm.conf.
        :return: It returns list of enabled plugins
        """

        # When user doesn't want to automatically enable yum plugins, then return empty list
        if cls.is_auto_enable_enabled() is False:
            log.debug('The rhsm.auto_enable_yum_plugins is disabled. Skipping the enablement of yum plugins.')
            return []

        log.debug('The rhsm.auto_enable_yum_plugins is enabled')

        enabled_plugins = []

        enabled_plugins.extend(cls._enable_plugins("dnf", cls.DNF_PLUGIN_DIR))

        enabled_plugins.extend(cls._enable_plugins("yum", cls.YUM_PLUGIN_DIR))

        return enabled_plugins


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
        for repo_class, _dummy in get_repo_file_classes():
            repo_file = repo_class()
            if os.path.exists(repo_file.path):
                os.unlink(repo_file.path)
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
            uep = self.cp_provider.get_consumer_auth_cp()
            result = self.release_status_cache.read_status(uep, self.identity.uuid)

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

        log.debug("Updating repo triggered with following attributes: cache_only=%s, apply_overrides=%s" %
                  (str(cache_only), str(apply_overrides)))

        self.identity = inj.require(inj.IDENTITY)

        # These should probably move closer their use
        self.ent_dir = inj.require(inj.ENT_DIR)
        self.prod_dir = inj.require(inj.PROD_DIR)

        self.ent_source = ent_cert.EntitlementDirEntitlementSource()

        self.cp_provider = inj.require(inj.CP_PROVIDER)

        self.manage_repos = 1
        self.apply_overrides = apply_overrides
        self.manage_repos = manage_repos_enabled()

        self.release = None
        self.overrides = {}
        self.override_supported = False

        if not cache_only:
            self.uep = self.cp_provider.get_consumer_auth_cp()
        else:
            self.uep = None

        if self.identity.is_valid():
            supported_resources = ServerCache.get_supported_resources(self.identity.uuid, self.uep)
            self.override_supported = 'content_overrides' in supported_resources

        self.written_overrides = WrittenOverrideCache()

        # FIXME: empty report at the moment, should be changed to include
        # info about updated repos
        self.report = RepoActionReport()
        self.report.name = "Repo updates"
        # If we are not registered, skip trying to refresh the
        # data from the server
        if not self.identity.is_valid():
            log.debug("The system is not registered. Skipping refreshing data from server.")
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
        # the [rhsm] manage_repos can be overridden to disable generation of the
        # redhat.repo file:
        if not self.manage_repos:
            log.debug("manage_repos is 0, skipping generation of repo files")
            for repo_class, _dummy in get_repo_file_classes():
                repo_file = repo_class()
                if repo_file.exists():
                    log.info("Removing %s due to manage_repos configuration." %
                            repo_file.path)
            RepoActionInvoker.delete_repo_file()
            return 0

        repo_pairs = []
        for repo_class, server_val_repo_class in get_repo_file_classes():
            # Load the RepoFile from disk, this contains all our managed yum repo sections.
            # We want to instantiate late because having a long-lived instance creates the possibility
            # of reading the file twice.  Despite it's name, the RepoFile object corresponds more to a
            # dictionary of config settings than a single file.  Doing a double read can result in comments
            # getting loaded twice.  A feedback loop can result causing the repo file to grow at O(n^2).
            # See BZ 1658409
            repo_pairs.append((repo_class(), server_val_repo_class()))

        for repo_file, server_val_repo_file in repo_pairs:
            repo_file.read()
            server_val_repo_file.read()
        valid = set()

        # Iterate content from entitlement certs, and create/delete each section
        # in the RepoFile as appropriate:
        for cont in self.get_unique_content():
            valid.add(cont.id)

            for repo_file, server_value_repo_file in repo_pairs:
                if cont.content_type in repo_file.CONTENT_TYPES:
                    fixed_cont = repo_file.fix_content(cont)
                    existing = repo_file.section(fixed_cont.id)
                    server_value_repo = server_value_repo_file.section(fixed_cont.id)
                    if server_value_repo is None:
                        server_value_repo = fixed_cont
                        server_value_repo_file.add(fixed_cont)
                    if existing is None:
                        repo_file.add(fixed_cont)
                        self.report_add(fixed_cont)
                    else:
                        # Updates the existing repo with new content
                        self.update_repo(existing, fixed_cont, server_value_repo)
                        repo_file.update(existing)
                        server_value_repo_file.update(server_value_repo)
                        self.report_update(existing)

        for repo_file, server_value_repo_file in repo_pairs:
            for section in server_value_repo_file.sections():
                if section not in valid:
                    self.report_delete(section)
                    server_value_repo_file.delete(section)
                    repo_file.delete(section)

            # Write new RepoFile(s) to disk:
            server_value_repo_file.write()
            repo_file.write()

        if self.override_supported:
            # Update with the values we just wrote
            self.written_overrides.overrides = self.overrides
            self.written_overrides.write_cache()
        log.info("repos updated: %s" % self.report)
        return self.report

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
        content = []
        for content_type in ALLOWED_CONTENT_TYPES:
            content += model.find_content(self.ent_source,
                                          content_type=content_type)
        return content

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

            if mutable and new_val is not None:
                server_value_repo[key] = new_val

        return changes_made

    def report_update(self, repo):
        self.report.repo_updates.append(repo)

    def report_add(self, repo):
        self.report.repo_added.append(repo)

    def report_delete(self, section):
        self.report.repo_deleted.append(section)


@six.python_2_unicode_compatible
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

    def __str__(self):
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
