import ckan.plugins.toolkit as tk
import ckan.lib.base as base

import ckan.model as model
import ckan.logic as logic
import ckan.lib.helpers as h
import json

from ckan.logic.validators import isodate

get_action = logic.get_action
context = tk.c
Base_c = base.c
global_contains_field = []


def get_versions(package_id):
    ctx = {'model': model}

    pkg = logic.get_action('package_show')(ctx, {'id': package_id})

    versions = [pkg]

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
    if type(pkg['relations']) == list and type(pkg['relations'][0]) == dict:
        newer_versions = [element['id'] for element in pkg['relations'] if element['relation'] == 'has_version']
        if len(newer_versions) > 0:
            newest_package = tk.get_action('package_show')(ctx, {'id': newer_versions[0]})

            versions.insert(0, newest_package)

            has_newer_version = True
            while has_newer_version is True:
                has_newer_version = False

                if 'relations' in newest_package and type(newest_package['relations']) == list and type(newest_package['relations'][0]) == dict:
                    search_results = [element['id'] for element in newest_package['relations'] if element['relation'] == 'has_version']

                    if len(search_results) > 0:
                        has_newer_version = True
                        newest_package = search_results['results'][0]
                        versions.insert(0, newest_package)

    return versions


def package_resources_list(package_id):
    ctx = {'model': model}
    return logic.get_action('package_resources_list')(ctx, {'id': package_id})


def get_newest_version(package_id):
    ctx = {'model': model}

    newest_package = logic.get_action('package_show')(ctx, {'id': package_id})

    # get newer versions
    if 'relations' in newest_package and type(newest_package['relations']) == list and type(newest_package['relations'][0]) == dict:
        newer_versions = [element['id'] for element in newest_package['relations'] if element['relation'] == 'has_version']
        if len(newer_versions) > 0:
            newest_package = tk.get_action('package_show')(ctx, {'id': newer_versions[0]})

            has_newer_version = True
            while has_newer_version is True:
                has_newer_version = False

                if 'relations' in newest_package and type(newest_package['relations']) == list and type(newest_package['relations'][0]) == dict:
                    search_results = [element['id'] for element in newest_package['relations'] if element['relation'] == 'has_version']

                    if len(search_results) > 0:
                        has_newer_version = True
                        newest_package = search_results['results'][0]

    return newest_package


def get_version_number(package_id):
    ctx = {'model': model}

    version_number = 1

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
