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
import ckan.lib.base as base

redirect = base.redirect


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

        new_res = current.copy()
        new_res.update(resource.copy())

        global new_pkg_version
        new_pkg_version = ""

        # "None" if call comes from before_delete
        # subsets and versions are already caught in auth function
        if not (authz.is_sysadmin(user) and create_version is False):
            if context.get('create_version', True) is True and pkg['private'] is False:
                if (new_res.get('upload') not in ("", None) or new_res.get('clear_upload') != "" and new_res['url'] != current['url']
                or (new_res.get('upload') in ("", None) and new_res.get('clear_upload') == "" and new_res['url'] != current['url'] and current['url_type'] in ("", None))):
                    new_pkg_version = pkg.copy()
                    new_pkg_version.pop('id')
                    new_pkg_version.pop('resources')
                    new_pkg_version.pop('revision_id')

                    # TODO change field name
                    new_pkg_version['issued'] = new_pkg_version['metadata_created'] = new_pkg_version['metadata_modified'] = datetime.datetime.now()
                    # Just for transfer
                    #new_pkg_version['issued'] = new_pkg_version['metadata_created'] = new_pkg_version['metadata_modified'] = new_res['created']

                    new_res.pop('id')
                    # auskommentieren fuer transfer
                    new_res.pop('created')
                    #nicht kommentieren danach :-)

                    #just for transfer

                    new_res.pop('last_modified', None)

                    new_pkg_version['resources'] = [new_res]

                    versions = helpers.get_versions(pkg['id'])

                    # change name of new version
                    new_pkg_version['name'] = "-v".join(versions[-1]['name'].split("-v")[:-1])

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
            # new_pkg_version contains name without "-v**", this will be added in the version_to_name validator
            new_pkg_version = toolkit.get_action('package_create')(context, new_pkg_version)
            new_resource['package_id'] = new_pkg_version['id']
            new_resource = toolkit.get_action('resource_create')(context, new_resource)

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

            h.flash_notice('New version has been created. <b><a href=%s>Click here</a></b> to see the new version.' % (h.url_for(controller='package', action='resource_read', id=new_pkg_version['name'], resource_id=new_resource['id'])), allow_html=True)

            context['package'] = model.Package.get(new_pkg_version['id'])

            resource.clear()
            resource.update(new_resource.copy())

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'get_versions': helpers.get_versions,
            'get_newest_version': helpers.get_newest_version,
            'get_oldest_version': helpers.get_oldest_version,
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
        # older versions need ignore_capacity_check, newer versions need 'include_private': True in package_search
        context['ignore_capacity_check'] = True
        older_versions = toolkit.get_action('package_search')(context, {'rows': 10000, 'fq': "extras_relations:%s" % (json.dumps('%s' % rel)), 'include_versions': True})

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

    def after_update(self, context, pkg_dict):
        try:
            pkg_dict['relations'] = json.loads(pkg_dict['relations'])
        except (ValueError, TypeError, AttributeError, KeyError):
            pkg_dict['relations'] = []

        if len(pkg_dict['relations']) > 0:
            newer_version_ids = [element['id'] for element in pkg_dict['relations'] if element['relation'] == 'has_version']
            if len(newer_version_ids) > 0:
                version = toolkit.get_action('package_show')(context, {'id': newer_version_ids[0]})
            else:
                version = helpers.get_oldest_version(pkg_dict['id'])

            version_name = "-v".join(version['name'].split("-v")[:-1])
            pkg_name = "-v".join(pkg_dict['name'].split("-v")[:-1])

            if version_name != pkg_name:
                version['name'] = pkg_name
                toolkit.get_action('package_update')(context, version)

    def before_search(self, search_params):
        include_versions = search_params.pop('include_versions', False)
        if not include_versions:
            if search_params.get('fq', '') == '':
                search_params['fq'] = "-relations:*%s*" % ('has_version')
            else:
                search_params['fq'] += (" AND -relations:*%s*" % ('has_version'))
        return search_params
