import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckanext.resourceversions import helpers
import ckan.lib.helpers as h
import ckanext.resourceversions.logic.action as action
from ckanext.resourceversions.logic.auth.delete import package_delete
# from ckanext.resourceversions.logic.auth.update import resource_update
from ckanext.resourceversions.logic.auth.update import package_update
import ckan.authz as authz
import datetime
import json
import ckan.model as model


class ResourceversionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IRoutes, inherit=True)
    # moved functions to ckanext-iauth
    # plugins.implements(plugins.IAuthFunctions)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'resourceversions')

    global new_pkg_version
    new_pkg_version = ""

    # IResourceController
    def before_update(self, context, current, resource):
        # toolkit.check_access('package_update', context, resource)
        user = context.get('user')

        pkg = toolkit.get_action('package_show')(context, {'id': resource['package_id']})

        # sysadmins should have the option to modify resource without version
        # therefore they can add a parameter "create_version"
        create_version = resource.get('create_version', True)
        if 'create_version' in resource:
            resource.pop('create_version')

        # added this so users can just pass parameters they want to have changed
        # new_res = current.copy()
        # for key in resource:
        #     new_res[key] = resource[key]
        new_res = resource.copy()

        global new_pkg_version
        new_pkg_version = ""

        # "None" if call comes from before_delete
        # subsets and versions are already caught in auth function
        if not (authz.is_sysadmin(user) and create_version is False):
            if context.get('create_version', True) is True and pkg['private'] is False:
                if new_res.get('upload') != "" or new_res.get('clear_upload') != "" and new_res['url'] != current['url'] or (new_res.get('upload') == "" and new_res.get('clear_upload') == "" and new_res['url'] != current['url'] and current['url_type'] == ""):
                    new_pkg_version = pkg.copy()
                    new_pkg_version.pop('id')
                    new_pkg_version.pop('resources')
                    new_pkg_version.pop('groups')
                    new_pkg_version.pop('revision_id')

                    # TODO change field name
                    new_pkg_version['iso_mdDate'] = new_pkg_version['metadata_created'] = new_pkg_version['metadata_modified'] = datetime.datetime.now()

                    new_res.pop('id')
                    new_pkg_version['resources'] = [new_res]

                    versions = helpers.get_versions(pkg['id'])

                    # change name of new version
                    new_pkg_version['name'] = versions[-1]['name'] + '-v' + str(helpers.get_version_number(pkg['id'])+1).zfill(2)

                    # add relation
                    new_pkg_version['relations'] = [{'relation': 'is_version_of', 'id': current['package_id']}]

                    # change the resource that will be updated to the old version
                    resource.clear()
                    resource.update(current.copy())

    def after_update(self, context, resource):
        # add new version to package
        global new_pkg_version

        pkg = toolkit.get_action('package_show')(context, {'id': resource['package_id']})
        if new_pkg_version != "":
            # need to pop package otherwise it overwrites the current pkg
            context.pop('package')
            new_resource = new_pkg_version.pop('resources')[0]
            new_pkg_version = toolkit.get_action('package_create')(context, new_pkg_version)
            new_resource['package_id'] = new_pkg_version['id']
            toolkit.get_action('resource_create')(context, new_resource)

            # TODO change this to append to relations
            pkg['relations'].append({'relation': 'has_version', 'id': new_pkg_version['id']})
            toolkit.get_action('package_update')(context, pkg)

            # # create same views
            # views = toolkit.get_action('resource_view_list')(context, {'id': resource['id']})
            # default_views = toolkit.get_action('resource_view_list')(context, {'id': new['id']})
            # for view in views:
            #     if view['view_type'] != "gallery_view" and not any(d['view_type'] == view['view_type'] for d in default_views):
            #         view.pop('id')
            #         view.pop('package_id')
            #         view['resource_id'] = new['id']
            #         toolkit.get_action('resource_view_create')(context, view)

            h.flash_notice('New version has been created.')

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'get_versions': helpers.get_versions,
            'get_newest_version': helpers.get_newest_version,
            'get_version_number': helpers.get_version_number,
            'version_has_subset': helpers.version_has_subset
            }

    # IActions
    def get_actions(self):
        actions = {
            'resource_version_number': action.resource_version_number
            }
        return actions

    # IAuthFunctions
    def get_auth_functions(self):
        """Implements IAuthFunctions.get_auth_functions"""
        return {
            'package_delete': package_delete,
            'package_update': package_update,
            'resource_update': resource_update
            }

    # IRoutes
    def before_map(self, map):
        map.connect('create_newest_version_of_subset', '/create_newest_version_of_subset/{resource_id}',
                    controller='ckanext.resourceversions.controllers.subset_version:SubsetVersionController',
                    action='create_newest_version_of_subset')
        map.connect('create_new_version_of_subset', '/create_new_version_of_subset/{subset_id}/{orig_id}',
                    controller='ckanext.resourceversions.controllers.subset_version:SubsetVersionController',
                    action='create_new_version_of_subset')
        return map


class ResourceversionsPackagePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IPackageController, inherit=True)

    def after_delete(self, context, pkg_dict):
        pkg = toolkit.get_action('package_show')(context, {'id': pkg_dict['id']})

        rel = {'relation': 'has_version', 'id': str(pkg['id'])}
        older_versions = toolkit.get_action('package_search')(context, {'include_private': True, 'rows': 10000, 'fq': "extras_relations:%s" % (json.dumps('%s' % rel))})

        global new_pkg_version
        new_pkg_version = ""

        try:
            newer_versions = [element['id'] for element in pkg['relations'] if element['relation'] == 'has_version']
        except:
            newer_versions = []

        # check if package has a newer version, then add newer_version['id'] to older_version['relation']
        # otherwise remove older_version['relation']
        if len(newer_versions) > 0:
            newer_version = toolkit.get_action('package_show')(context, {'id': newer_versions[0]})
            print(newer_version)
            newer_ver_relations = newer_version['relations']
            newer_version['relations'] = [r for r in newer_ver_relations if r['relation'] != 'is_version_of']

            if older_versions['count'] > 0:
                older_version = older_versions['results'][0]
                newer_version['relations'].append({'relation': 'is_version_of', 'id': older_version['id']})

            toolkit.get_action('package_update')(context, newer_version)

        if older_versions['count'] > 0:
            older_version = older_versions['results'][0]
            older_version['relations'].remove(rel)

            if len(newer_versions) > 0:
                older_version['relations'].append({'relation': 'has_version', 'id': newer_versions[0]})

            toolkit.get_action('package_update')(context, older_version)
