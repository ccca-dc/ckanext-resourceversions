import ckan.logic as logic
import ckan.authz as authz
import ckan.plugins.toolkit as toolkit
from ckan.logic.auth import get_resource_object
from ckan.lib.base import _
from ckan.logic.auth.create import _check_group_auth
import ckan.logic.auth as logic_auth
from ckanext.thredds import helpers


@logic.auth_allow_anonymous_access
def package_update(context, data_dict):
    user = context.get('user')
    package = logic_auth.get_package_object(context, data_dict)

    if package.owner_org:
        # if there is an owner org then we must have update_dataset
        # permission for that organization
        check1 = authz.has_user_permission_for_group_or_org(
            package.owner_org, user, 'update_dataset'
        )
    else:
        # If dataset is not owned then we can edit if config permissions allow
        if authz.auth_is_anon_user(context):
            check1 = all(authz.check_config_permission(p) for p in (
                'anon_create_dataset',
                'create_dataset_if_not_in_organization',
                'create_unowned_dataset',
                ))
        else:
            check1 = all(authz.check_config_permission(p) for p in (
                'create_dataset_if_not_in_organization',
                'create_unowned_dataset',
                )) or authz.has_user_permission_for_some_org(
                user, 'create_dataset')
    if not check1:
        return {'success': False,
                'msg': _('User %s not authorized to edit package %s') %
                        (str(user), package.id)}
    else:
        check2 = _check_group_auth(context, data_dict)
        if not check2:
            return {'success': False,
                    'msg': _('User %s not authorized to edit these groups') %
                            (str(user))}

    if package.private is not None and package.private is False and data_dict is not None and data_dict.get('private', '') == 'True':
        return {'success': False,
                'msg': 'Public datasets cannot be set private again'}
    elif package.private is not None and package.private is True and data_dict is not None and data_dict.get('private', '') == 'False':
        subset_uniqueness = helpers.check_subset_uniqueness(package.id)

        if len(subset_uniqueness) > 0:
            return {'success': False,
                    'msg': 'Dataset cannot be set public as it contains a subset, which was already published'}

    return {'success': True}


# def resource_update(context, data_dict):
#     model = context['model']
#     user = context.get('user')
#     resource = logic_auth.get_resource_object(context, data_dict)
#
#     # check authentication against package
#     pkg = model.Package.get(resource.package_id)
#     if not pkg:
#         raise logic.NotFound(
#             _('No package found for this resource, cannot check auth.')
#         )
#
#     upload = False
#     if 'upload' in data_dict and data_dict['upload'] != "" or 'upload_local' in data_dict and data_dict['upload_local'] != "" or 'upload_remote' in data_dict and data_dict['upload_remote'] != "":
#         upload = True
#
#     if upload or 'url' in data_dict and "/" in data_dict['url'] and data_dict['url'] != resource.url:
#         # check if resource has a newer version
#         if 'newer_version' in resource.extras and resource.extras['newer_version'] != "":
#             return {'success': False, 'msg': 'Older versions cannot be updated'}
#         # check if this is a subset, then it cannot create a new version like that
#         if 'subset_of' in resource.extras and resource.extras['subset_of'] != "":
#             return {'success': False, 'msg': 'Please create only new versions from the original resource'}
#
#     pkg_dict = {'id': pkg.id}
#     authorized = authz.is_authorized('package_update', context, pkg_dict).get('success')
#
#     if not authorized:
#         return {'success': False,
#                 'msg': _('User %s not authorized to edit resource %s') %
#                         (str(user), resource.id)}
#     else:
#         return {'success': True}
