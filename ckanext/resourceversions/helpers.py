import ckan.plugins.toolkit as tk
import ckan.lib.base as base

import ckan.model as model
import ckan.logic as logic

get_action = logic.get_action
context = tk.c
Base_c = base.c
global_contains_field = []


def get_versions_list(resource_id, package_id):
    ctx = {'model': model}

    pkg = logic.get_action('package_show')(ctx, {'id': package_id})
    resource = logic.get_action('resource_show')(ctx, {'id': resource_id})
    resource_list = pkg['resources']

    res_helper = resource
    versions = []
    while res_helper is not None:
        res_helper_id = res_helper['id']
        res_helper = None
        for res in resource_list:
            if 'newerVersion' in res and res['newerVersion'] == res_helper_id:
                versions.append({'id': res['id'], 'name': res['name']})
                res_helper = res.copy()
                break
    return versions
