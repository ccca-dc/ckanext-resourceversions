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
            print(resource['name'])
            if 'newerVersion' not in resource or resource['newerVersion'] == '':
                newest_versions.append(resource)

    if newest_versions != []:
        return newest_versions
    return resources
