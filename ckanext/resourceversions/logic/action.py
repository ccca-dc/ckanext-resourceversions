# encoding: utf-8

import ckan.logic
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

_get_or_bust = ckan.logic.get_or_bust


# TODO change or remove
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
            if 'newer_version' in res and res['newer_version'] == oldest_resource['id']:
                versions.insert(0, res['id'])
                oldest_resource = res.copy()
                has_older_version = True
                break

    return versions.index(resource['id']) + 1
