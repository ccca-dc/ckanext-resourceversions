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
    versions = []
    pkg = logic.get_action('package_show')(ctx, {'id': package_id})
    resource_list = pkg['resources']
    for resource in resource_list:
        if 'newerVersion' in resource and resource['newerVersion'] == resource_id:
            return resource['id']
    return ""
