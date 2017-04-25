import ckan.plugins.toolkit as tk
import ckan.lib.base as base

import ckan.model as model
import ckan.logic as logic

from ckan.logic.validators import isodate

get_action = logic.get_action
context = tk.c
Base_c = base.c
global_contains_field = []


def get_older_versions(resource_id, package_id):
    ctx = {'model': model}

    pkg = logic.get_action('package_show')(ctx, {'id': package_id})
    resource = logic.get_action('resource_show')(ctx, {'id': resource_id})
    resource_list = pkg['resources']

    versions = []

    # get older versions
    res_helper = resource.copy()
    while res_helper is not None:
        res_id = res_helper['id']
        res_helper = None
        for res in resource_list:
            if 'newer_version' in res and res['newer_version'] == res_id:
                versions.append({'id': res['id'], 'created': isodate(res['created'], ctx), 'current': False})
                res_helper = res.copy()
                break

    # get this version
    versions.insert(0, {'id': resource['id'], 'created': isodate(resource['created'], ctx), 'current': True})

    # get newer versions
    if 'newer_version' in resource and resource['newer_version'] != "":
        newest_resource = tk.get_action('resource_show')(data_dict={'id': resource['newer_version']})

        versions.insert(0, {'id': newest_resource['id'], 'created': isodate(newest_resource['created'], ctx), 'current': False})

        has_newer_version = True
        while has_newer_version is True:
            has_newer_version = False
            for res in resource_list:
                if 'newer_version' in newest_resource and newest_resource['newer_version'] == res['id']:
                    versions.insert(0, {'id': res['id'], 'created': isodate(res['created'], ctx), 'current': False})
                    newest_resource = res.copy()
                    has_newer_version = True
                    break

    return versions


def package_resources_list(package_id):
    ctx = {'model': model}
    return logic.get_action('package_resources_list')(ctx, {'id': package_id})
