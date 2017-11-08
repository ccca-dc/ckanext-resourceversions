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

        try:
            subsets = [element['id'] for element in pkg['relations'] if element['relation'] == 'is_part_of']
        except:
            subsets = []
        try:
            newer_versions = [element['id'] for element in pkg['relations'] if element['relation'] == 'has_version']
        except:
            newer_versions = []

        # sysadmins should have the option to modify resource without version
        # therefore they can add a parameter "create_version"
        create_version = resource.get('create_version', True)
        if 'create_version' in resource:
            resource.pop('create_version')

        # added this so users can just pass parameters they want to have changed
        new_res = current.copy()
        for key in resource:
            new_res[key] = resource[key]

        global new_pkg_version

        # "None" if call comes from before_delete
        # subsets should not create versions that are not from the original
        if new_pkg_version is not None and (len(subsets) == 0) and not (authz.is_sysadmin(user) and create_version is False):
            if (len(newer_versions) == 0) and pkg['private'] is False and ('upload' in new_res and new_res['upload'] != "" or "/" in new_res['url'] and current['url'] != new_res['url']):
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

                # TODO change to real version
                new_pkg_version['name'] = versions[-1]['name'] + '-v' + str(helpers.get_version_number(pkg['id'])+1).zfill(2)

                # change the resource that will be updated to the old version
                resource.clear()
                resource.update(current.copy())

            else:
                new_pkg_version = ""
                # add resource clear
        else:
            new_pkg_version = ""
            # only if sysadmin no resource clear

    def after_update(self, context, resource):
        # add new version to package
        global new_pkg_version

        pkg = toolkit.get_action('package_show')(context, {'id': resource['package_id']})
        if new_pkg_version != "":
            # need to pop package otherwise it overwrites the current pkg
            context.pop('package')
            new_resource = new_pkg_version['resources'][0]
            new_pkg_version = toolkit.get_action('package_create')(context, new_pkg_version)
            new_resource['package_id'] = new_pkg_version['id']

            # TODO change this to append to relations
            pkg['relations'] = [{'relation': 'has_version', 'id': new_pkg_version['id']}]
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

    def before_delete(self, context, resource, resources):
        res_delete = toolkit.get_action('resource_show')(context, {'id': resource['id']})
        global new_res_version
        new_res_version = ""

        for r in resources:
            # check if resource has versions
            if 'newer_version' in r and r['newer_version'] == res_delete['id']:
                # set new_res_version to None so that it does not create new version in update
                new_res_version = None
                if 'newer_version' in res_delete:
                    r['newer_version'] = res_delete['newer_version']
                else:
                    r['newer_version'] = ""
                toolkit.get_action('resource_update')(context, r)
                break

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'get_versions': helpers.get_versions,
            'package_resources_list': helpers.package_resources_list,
            'get_newest_version': helpers.get_newest_version,
            'subset_has_version': helpers.subset_has_version,
            'get_version_number': helpers.get_version_number,
            }

    # IActions
    def get_actions(self):
        actions = {
            'package_resources_list': action.package_resources_list,
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
