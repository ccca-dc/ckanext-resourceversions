import ckan.plugins.toolkit as tk
import ckan.lib.base as base

import ckan.model as model
import ckan.logic as logic
import ckan.lib.helpers as h

from ckan.logic.validators import isodate

get_action = logic.get_action
context = tk.c
Base_c = base.c
global_contains_field = []


def get_versions(resource_id):
    ctx = {'model': model}

    resource = logic.get_action('resource_show')(ctx, {'id': resource_id})
    pkg = logic.get_action('package_show')(ctx, {'id': resource['package_id']})
    resource_list = pkg['resources']

    versions = [resource]

    # get older versions
    res_helper = resource.copy()
    while res_helper is not None:
        res_id = res_helper['id']
        res_helper = None
        for res in resource_list:
            if 'newer_version' in res and res['newer_version'] == res_id:
                versions.append(res)
                res_helper = res.copy()
                break

    # get newer versions
    if 'newer_version' in resource and resource['newer_version'] != "":
        newest_resource = tk.get_action('resource_show')(data_dict={'id': resource['newer_version']})

        versions.insert(0, newest_resource)

        has_newer_version = True
        while has_newer_version is True:
            has_newer_version = False
            for res in resource_list:
                if 'newer_version' in newest_resource and newest_resource['newer_version'] == res['id']:
                    versions.insert(0, res)
                    newest_resource = res.copy()
                    has_newer_version = True
                    break

    return versions


def package_resources_list(package_id):
    ctx = {'model': model}
    return logic.get_action('package_resources_list')(ctx, {'id': package_id})


def get_newest_version(resource_id):
    ctx = {'model': model}

    resource = logic.get_action('resource_show')(ctx, {'id': resource_id})
    pkg = logic.get_action('package_show')(ctx, {'id': resource['package_id']})
    resource_list = pkg['resources']

    newest_resource = resource.copy()

    # get newest version
    if 'newer_version' in resource and resource['newer_version'] != "":
        newest_resource = tk.get_action('resource_show')(data_dict={'id': resource['newer_version']})

        has_newer_version = True
        while has_newer_version is True:
            has_newer_version = False
            for res in resource_list:
                if 'newer_version' in newest_resource and newest_resource['newer_version'] == res['id']:
                    newest_resource = res.copy()
                    has_newer_version = True
                    break

    return newest_resource
