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
    ctx = {'model': model, 'ignore_capacity_check': True}

    pkg = logic.get_action('package_show')(ctx, {'id': package_id})

    versions = [pkg]

    # get older versions
    pkg_helper = pkg.copy()
    while pkg_helper is not None:
        pkg_id = pkg_helper['id']
        pkg_helper = None

        rel = {'relation': 'has_version', 'id': str(pkg_id)}
        # TODO remove include_private for older CKAN versions
        search_results = tk.get_action('package_search')(ctx, {'include_private': True, 'rows': 10000, 'fq': "extras_relations:%s" % (json.dumps('%s' % rel))})

        if search_results['count'] > 0:
            versions.append(search_results['results'][0])
            pkg_helper = search_results['results'][0].copy()

    # get newer versions
    if 'relations' in pkg and type(pkg['relations']) == list and len(pkg['relations']) > 0 and type(pkg['relations'][0]) == dict:
        newer_versions = [element['id'] for element in pkg['relations'] if element['relation'] == 'has_version']
        if len(newer_versions) > 0:
            newest_package = tk.get_action('package_show')(ctx, {'id': newer_versions[0]})

            versions.insert(0, newest_package)

            has_newer_version = True
            while has_newer_version is True:
                has_newer_version = False

                if 'relations' in newest_package and type(newest_package['relations']) == list and len(newest_package['relations']) > 0 and type(newest_package['relations'][0]) == dict:
                    search_results = [element['id'] for element in newest_package['relations'] if element['relation'] == 'has_version']

                    if len(search_results) > 0:
                        has_newer_version = True
                        newest_package = tk.get_action('package_show')(ctx, {'id': search_results[0]})
                        versions.insert(0, newest_package)

    return versions


def get_newest_version(package_id):
    ctx = {'model': model}

    newest_package = logic.get_action('package_show')(ctx, {'id': package_id})

    # get newer versions
    if 'relations' in newest_package and type(newest_package['relations']) == list and len(newest_package['relations']) > 0 and type(newest_package['relations'][0]) == dict:
        newer_versions = [element['id'] for element in newest_package['relations'] if element['relation'] == 'has_version']
        if len(newer_versions) > 0:
            newest_package = tk.get_action('package_show')(ctx, {'id': newer_versions[0]})

            has_newer_version = True
            while has_newer_version is True:
                has_newer_version = False

                if 'relations' in newest_package and type(newest_package['relations']) == list and len(newest_package['relations']) > 0 and type(newest_package['relations'][0]) == dict:
                    search_results = [element['id'] for element in newest_package['relations'] if element['relation'] == 'has_version']

                    if len(search_results) > 0:
                        has_newer_version = True
                        newest_package = tk.get_action('package_show')(ctx, {'id': search_results[0]})

    return newest_package


def get_oldest_version(package_id):
    ctx = {'model': model}

    oldest_package = logic.get_action('package_show')(ctx, {'id': package_id})

    # get newer versions
    if 'relations' in oldest_package and type(oldest_package['relations']) == list and len(oldest_package['relations']) > 0 and type(oldest_package['relations'][0]) == dict:
        older_versions = [element['id'] for element in oldest_package['relations'] if element['relation'] == 'is_version_of']
        if len(older_versions) > 0:
            oldest_package = tk.get_action('package_show')(ctx, {'id': older_versions[0]})

            has_older_version = True
            while has_older_version is True:
                has_older_version = False

                if 'relations' in oldest_package and type(oldest_package['relations']) == list and len(oldest_package['relations']) > 0 and type(oldest_package['relations'][0]) == dict:
                    search_results = [element['id'] for element in oldest_package['relations'] if element['relation'] == 'is_version_of']

                    if len(search_results) > 0:
                        has_older_version = True
                        oldest_package = tk.get_action('package_show')(ctx, {'id': search_results[0]})

    return oldest_package


def get_version_number(pkg):
    ctx = {'model': model}

    version_number = 1

    # get newer versions
    if 'relations' in pkg and type(pkg['relations']) == list and len(pkg['relations']) > 0 and type(pkg['relations'][0]) == dict:
        older_versions = [element['id'] for element in pkg['relations'] if element['relation'] == 'is_version_of']
        if len(older_versions) > 0:
            oldest_package = tk.get_action('package_show')(ctx, {'id': older_versions[0]})
            version_number += 1

            first_version = False
            while not first_version:
                if 'relations' in oldest_package and type(oldest_package['relations']) == list and len(oldest_package['relations']) > 0 and type(oldest_package['relations'][0]) == dict:
                    older_versions = [element['id'] for element in oldest_package['relations'] if element['relation'] == 'is_version_of']

                    if len(older_versions) > 0:
                        oldest_package = tk.get_action('package_show')(ctx, {'id': older_versions[0]})
                        version_number += 1
                    else:
                        first_version = True
                else:
                    first_version = True

    return version_number


def version_has_subset(subset_id, original_id):
    subset_versions = get_versions(subset_id)

    for subset in subset_versions:
        search_results = [element for element in subset['relations'] if element['relation'] == 'is_part_of' and element['id'] == original_id]

        if len(search_results) > 0:
            return subset

    return None
