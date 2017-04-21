import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckanext.resourceversions import helpers
import ckanext.resourceversions.logic.action as action
from ckanext.resourceversions.logic.auth.delete import package_delete


class ResourceversionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'resourceversions')

    new_res_version = ""

    # IResourceController
    def before_update(self, context, current, resource):
        # toolkit.check_access('package_update', context, resource)
        pkg = toolkit.get_action('package_show')(context, {'id': resource['package_id']})
        if resource['newerVersion'] == "" and pkg['private'] is False and 'upload' in resource and (resource['upload'] != "" or "/" in resource['url'] and current['url'] != resource['url']):
            # create new resource with the new file/link
            global new_res_version
            new_res_version = resource.copy()
            new_res_version.pop('id', None)
            new_res_version['package_id'] = current['package_id']
            new_res_version['name'] = "new version"

            # change the resource that will be updated to the old version
            resource.clear()
            resource.update(current.copy())

    def after_update(self, context, resource):
        # add new version to package
        pkg = toolkit.get_action('package_show')(context, {'id': resource['package_id']})
        if pkg['private'] is False and resource['newerVersion'] == "":
            new = toolkit.get_action('resource_create')(context, new_res_version)
            resource['newerVersion'] = new['id']
            toolkit.get_action('resource_update')(context, resource)

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'get_versions_list': helpers.get_versions_list,
            'package_resources_list': helpers.package_resources_list
            }

    # IActions
    def get_actions(self):
        actions = {'package_resources_list': action.package_resources_list}
        return actions

    # IAuthFunctions
    def get_auth_functions(self):
        """Implements IAuthFunctions.get_auth_functions"""
        return {
            'package_delete': package_delete
            }
