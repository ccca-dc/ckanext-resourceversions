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


def get_versions(package_id):
    ctx = {'model': model}

    pkg = logic.get_action('package_show')(ctx, {'id': package_id})

    versions = [pkg]

    import json

    # get older versions
    pkg_helper = pkg.copy()
    while pkg_helper is not None:
        pkg_id = pkg_helper['id']
        pkg_helper = None

        d = {'relation': 'has_version', 'id': str(pkg_id)}
        search_results = tk.get_action('package_search')(ctx, {'fq': "relations:*%s*" % (json.dumps(str(d)))})

        if search_results['count'] > 0:
            versions.append(search_results['results'][0])
            pkg_helper = search_results['results'][0].copy()

    # get newer versions
    newer_versions = [element['id'] for element in pkg['relations'] if element['relation'] == 'has_version']
    if len(newer_versions) > 0:
        newest_package = tk.get_action('package_show')(ctx, {'id': newer_versions[0]})

        versions.insert(0, newest_package)

        has_newer_version = True
        while has_newer_version is True:
            has_newer_version = False

            search_results = [element['id'] for element in newest_package['relations'] if element['relation'] == 'has_version']

            if search_results['count'] > 0:
                has_newer_version = True
                newest_package = search_results['results'][0]
                versions.insert(0, newest_package)

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


def get_version_number(package_id):
    ctx = {'model': model}

    version_number = 1
    import json

    helper_pkg_id = package_id
    first_version = False
    while not first_version:
        d = {'relation': 'has_version', 'id': str(helper_pkg_id)}
        search_results = tk.get_action('package_search')(ctx, {'fq': "relations:*%s*" % (json.dumps(str(d)))})

        if search_results['count'] > 0:
            helper_pkg_id = search_results['results'][0]['id']
            version_number += 1
        else:
            first_version = True

    return version_number


def subset_has_version(subset_id, original_id):
    subset_versions = get_versions(subset_id)

    for subset in subset_versions:
        if 'subset_of' in subset and subset['subset_of'] == original_id:
            return subset

    return None
