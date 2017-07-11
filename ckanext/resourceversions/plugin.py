import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckanext.resourceversions import helpers
import ckan.lib.helpers as h
import ckanext.resourceversions.logic.action as action
from ckanext.resourceversions.logic.auth.delete import package_delete
from ckanext.resourceversions.logic.auth.update import resource_update
from ckanext.resourceversions.logic.auth.update import package_update


class ResourceversionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IRoutes, inherit=True)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'resourceversions')

    global new_res_version
    new_res_version = ""

    # IResourceController
    def before_update(self, context, current, resource):
        # toolkit.check_access('package_update', context, resource)
        pkg = toolkit.get_action('package_show')(context, {'id': resource['package_id']})
        global new_res_version

        # "None" if call comes from before_delete
        # subsets should not create versions that are not from the original
        if new_res_version is not None and ('subset_of' not in resource or resource['subset_of'] == ""):
            if ('newer_version' not in resource or resource['newer_version'] == "") and pkg['private'] is False and ('upload' in resource and resource['upload'] != "" or "/" in resource['url'] and current['url'] != resource['url']):
                # create new resource with the new file/link
                new_res_version = resource.copy()
                new_res_version.pop('id', None)
                new_res_version.pop('hash', None)
                new_res_version.pop('iso_resourceURI', None)
                new_res_version.pop('revision_id', None)
                new_res_version.pop('size', None)
                new_res_version.pop('created', None)

                # change the resource that will be updated to the old version
                resource.clear()
                resource.update(current.copy())
            else:
                new_res_version = ""
        else:
            new_res_version = ""

    def after_update(self, context, resource):
        # add new version to package
        global new_res_version

        if new_res_version != "":
            new = toolkit.get_action('resource_create')(context, new_res_version)
            resource['newer_version'] = new['id']
            toolkit.get_action('resource_update')(context, resource)

            # create same views
            views = toolkit.get_action('resource_view_list')(context, {'id': resource['id']})
            default_views = toolkit.get_action('resource_view_list')(context, {'id': new['id']})
            for view in views:
                if view['view_type'] != "gallery_view" and not any(d['view_type'] == view['view_type'] for d in default_views):
                    view.pop('id')
                    view.pop('package_id')
                    view['resource_id'] = new['id']
                    toolkit.get_action('resource_view_create')(context, view)

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
            'subset_has_version': helpers.subset_has_version
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
