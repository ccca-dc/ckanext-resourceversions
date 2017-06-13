import ckan.lib.helpers as h
import ckan.lib.base as base
from urlparse import urlparse, parse_qs
from pylons import config
import ckan.plugins.toolkit as tk

import logging
import ckan.model as model
from ckan.model import (PACKAGE_NAME_MIN_LENGTH, PACKAGE_NAME_MAX_LENGTH)
import ckan.logic as logic
import ckan.lib.uploader as uploader
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.authz as authz
import ckan.lib.navl.dictization_functions as df
from ckan.common import _
from ckanext.resourceversions import helpers

get_action = logic.get_action
parse_params = logic.parse_params
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
check_access = logic.check_access

c = base.c
request = base.request
abort = base.abort
redirect = base.redirect
log = logging.getLogger(__name__)

NotAuthorized = logic.NotAuthorized
NotFound = logic.NotFound
Invalid = df.Invalid

unflatten = df.unflatten


class SubsetVersionController(base.BaseController):

    def create_newest_version_of_subset(self, resource_id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user}

        old_subset = tk.get_action('resource_show')(context, {'id': resource_id})
        original_old_res = tk.get_action('resource_show')(context, {'id': old_subset['subset_of']})

        subset_new_ver = helpers.get_newest_version(resource_id)

        original_new_ver = helpers.get_newest_version(original_old_res['id'])

        if subset_new_ver['subset_of'] != original_new_ver['id']:
            # create new URL with newest resource_id
            old_url = old_subset['url']
            newest_id = original_new_ver['id']
            new_url = self._create_new_url(old_url, newest_id)

            new_subset = tk.get_action('resource_create')(context, {'name': old_subset['name'], 'url': new_url, 'package_id': old_subset['package_id'], 'format': old_subset['format'], 'subset_of': newest_id})
            subset_new_ver['newer_version'] = new_subset['id']
            tk.get_action('resource_update')(context, subset_new_ver)

            h.flash_notice('New version has been created.')
            redirect(h.url_for(controller='package', action='resource_read',
                                   id=new_subset['package_id'], resource_id=new_subset['id']))
        else:
            h.flash_error('Update did not work. Could not find newer version')
            redirect(h.url_for(controller='package', action='resource_read',
                                   id=old_subset['package_id'], resource_id=old_subset['id']))

    def create_new_version_of_subset(self, subset_id, orig_id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user}

        subset = tk.get_action('resource_show')(context, {'id': subset_id})
        orig_res = tk.get_action('resource_show')(context, {'id': orig_id})

        subset_versions = helpers.get_versions(subset_id)
        orig_versions = helpers.get_versions(orig_id)

        orig_index = orig_versions.index(orig_res)

        orig_versions_newer = list(reversed(orig_versions[:orig_index]))
        orig_versions_older = orig_versions[orig_index+1:]

        newer_version_id = ""
        for ver in orig_versions_newer:
            for sub_ver in subset_versions:
                if sub_ver['subset_of'] == ver['id']:
                    newer_version_id = sub_ver['id']
                    break
            if newer_version_id != "":
                break

        older_version = ""
        for ver in orig_versions_older:
            for sub_ver in subset_versions:
                if sub_ver['subset_of'] == ver['id']:
                    older_version = sub_ver
                    break
            if older_version != "":
                break

        new_url = self.create_new_url(subset['url'], orig_id)
        new_subset = tk.get_action('resource_create')(context, {'name': subset['name'], 'url': new_url, 'package_id': subset['package_id'], 'format': subset['format'], 'subset_of': orig_id, 'newer_version': newer_version_id})
        if older_version != "":
            older_version['newer_version'] = new_subset['id']
            tk.get_action('resource_update')(context, older_version)

        h.flash_notice('New version has been created.')
        redirect(h.url_for(controller='package', action='resource_read',
                               id=subset['package_id'], resource_id=subset['id']))

    def create_new_url(self, old_url, new_id):
        url_segments = old_url.split('/')
        params = url_segments[5].split('?')
        params[0] = new_id
        string_params = '?'.join(params)
        url_segments[5] = string_params
        new_url = '/'.join(url_segments)
        return new_url
