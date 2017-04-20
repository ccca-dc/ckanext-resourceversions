# encoding: utf-8

import ckan.logic
import ckan.plugins as plugins
from ckan.logic import side_effect_free
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.logic as logic
ValidationError = ckan.logic.ValidationError
NotFound = ckan.logic.NotFound
_check_access = ckan.logic.check_access
_get_or_bust = ckan.logic.get_or_bust
_get_action = ckan.logic.get_action


def package_resources_list(context, data_dict):
    package_id = _get_or_bust(data_dict, 'id')
    all_versions = data_dict.pop('all_versions', False)

    package = logic.get_action('package_show')(context, {'id': package_id, 'include_tracking': True})

    resources = package['resources']

    if all_versions is False:
        for resource in resources:
            if 'newerVersion' in resource and resource['newerVersion'] != '':
                print("true")
                resources.remove(resource)

    return resources
