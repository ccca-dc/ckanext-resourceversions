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
from ckanext.thredds.logic.action import get_ncss_subset_params
from ckanext.thredds.logic.action import send_email
from ckanext.thredds.helpers import get_query_params
import datetime

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
            new_url = self.create_new_url(old_url, newest_id)

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
                   'user': c.user, 'ignore_capacity_check': True}

        subset = tk.get_action('package_show')(context, {'id': subset_id})
        orig_pkg = tk.get_action('package_show')(context, {'id': orig_id})

        new_ver_name = subset['name'][:subset['name'].rfind("-v") + 2] + str(helpers.get_version_number(orig_pkg['id'])).zfill(2)

        # TODO remove include_private for older CKAN versions
        search_results = tk.get_action('package_search')(context, {'include_private': True, 'rows': 10000, 'fq': "name:%s" % (new_ver_name)})

        if search_results['count'] > 0:
            h.flash_error('The new version could not be created as another package already has the name "%s". Please create a new subset from the original package.' % (new_ver_name))
        else:
            try:
                enqueue_job = tk.enqueue_job
            except AttributeError:
                from ckanext.rq.jobs import enqueue as enqueue_job
            enqueue_job(create_new_version_of_subset_job, [subset, orig_pkg])

            h.flash_notice('Your version is being created. This might take a while, you will receive an E-Mail when your version is available.')
        redirect(h.url_for(controller='package', action='read', id=subset_id))


def create_new_version_of_subset_job(subset, orig_pkg):
    context = {'model': model, 'session': model.Session,
               'user': c.user, 'auth_user_obj': c.userobj}

    subset_versions = helpers.get_versions(subset['id'])
    orig_versions = helpers.get_versions(orig_pkg['id'])

    orig_index = orig_versions.index(orig_pkg)

    orig_versions_newer = list(reversed(orig_versions[:orig_index]))
    orig_versions_older = orig_versions[orig_index+1:]

    newer_version = None
    for ver in orig_versions_newer:
        for sub_ver in subset_versions:
            search_results = [element['id'] for element in sub_ver['relations'] if element['relation'] == 'is_part_of' and element['id'] == ver['id']]
            if len(search_results) > 0:
                newer_version = sub_ver
                break
        if newer_version is not None:
            break

    older_version = None
    for ver in orig_versions_older:
        for sub_ver in subset_versions:
            search_results = [element['id'] for element in sub_ver['relations'] if element['relation'] == 'is_part_of' and element['id'] == ver['id']]
            if len(search_results) > 0:
                older_version = sub_ver
                break
        if older_version is not None:
            break

    # get NetCDF resource of original package
    orig_netcdf_resources = [res['id'] for res in orig_pkg['resources'] if res['format'].lower() == 'netcdf']

    metadata = tk.get_action('thredds_get_metadata_info')(context, {'id': orig_netcdf_resources[0]})
    # get params from metadata
    params = get_query_params(subset)
    params['accept'] = 'netcdf'

    # TODO make request
    corrected_params, subset_hash = get_ncss_subset_params(orig_netcdf_resources[0], params, False, metadata)

    return_dict = dict()

    if 'error' not in corrected_params:

        if subset_hash is not None:
            search_results = tk.get_action('package_search')(context, {'rows': 10000, 'fq':
                            'res_hash:%s' % (subset_hash)})

            if search_results['count'] > 0:
                return_dict['existing_package'] = search_results['results'][0]

        if 'existing_package' not in return_dict or subset['private'].lower() is True:

            # creating new package from the older version with few changes
            if older_version is not None:
                new_package = older_version.copy()
            else:
                new_package = newer_version.copy()
            new_package.update(corrected_params)
            new_package.pop('id')
            new_package['resources'] = []
            new_package.pop('groups')
            new_package.pop('revision_id')

            new_package['name'] = subset['name'][:subset['name'].rfind("-v") + 2] + str(helpers.get_version_number(orig_pkg['id'])).zfill(2)

            new_package['iso_mdDate'] = new_package['metadata_created'] = new_package['metadata_modified'] = datetime.datetime.now()

            new_package['relations'] = [{'relation': 'is_part_of', 'id': orig_pkg['id']}]
            if newer_version is not None:
                new_package['relations'].append({'relation': 'has_version', 'id': newer_version['id']})

            if subset_hash is not None:
                new_package['hash'] = subset_hash

            # append resources
            resources = older_version['resources'] if older_version is not None else newer_version['resources']
            for resource in resources:
                resource['url'] = create_new_url(resource['url'], orig_pkg['id'])
                new_package['resources'].append(resource)

            new_package = tk.get_action('package_create')(context, new_package)
            return_dict['new_package'] = new_package

            # change has_version in older package
            if older_version is not None:
                older_ver_relations = older_version['relations']
                older_version['relations'] = [r for r in older_ver_relations if r['relation'] != 'has_version']
                older_version['relations'].append({'relation': 'has_version', 'id': new_package['id']})
                tk.get_action('package_update')(context, older_version)

    location = corrected_params['location']
    error = corrected_params.get('error', None)
    new_package = return_dict.get('new_package', None)
    existing_package = return_dict.get('existing_package', None)

    send_email(location, error, new_package, existing_package)


def create_new_url(old_url, new_id):
    url_segments = old_url.split('/')
    print(url_segments)
    url_segments[4] = new_id
    new_url = '/'.join(url_segments)
    return new_url
