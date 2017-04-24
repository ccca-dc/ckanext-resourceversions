# encoding: utf-8

import ckan.logic
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

_get_or_bust = ckan.logic.get_or_bust


def package_resources_list(context, data_dict):
    package_id = _get_or_bust(data_dict, 'id')
    all_versions = data_dict.pop('all_versions', False)

    package = toolkit.get_action('package_show')(data_dict={'id': package_id, 'include_tracking': True})

    resources = package['resources']

    newest_versions = []

    if all_versions is False:
        for resource in resources:
            if 'newerVersion' not in resource or resource['newerVersion'] == '':
                newest_versions.append(resource)

    if newest_versions != []:
        return newest_versions
    return resources


def resource_version_number(context, data_dict):
    resource_id = _get_or_bust(data_dict, 'id')

    resource = toolkit.get_action('resource_show')(data_dict={'id': resource_id})
    package = toolkit.get_action('package_show')(data_dict={'id': resource['package_id']})

    resources = package['resources']

    versions = [resource['id']]

    oldest_resource = resource.copy()

    # get older versions
    has_older_version = True
    while has_older_version is True:
        has_older_version = False
        for res in resources:
            if 'newerVersion' in res and res['newerVersion'] == oldest_resource['id']:
                versions.insert(0, res['id'])
                oldest_resource = res.copy()
                has_older_version = True
                break

    return versions.index(resource['id']) + 1
