import ckan.logic as logic
import ckan.authz as authz
import ckan.plugins.toolkit as toolkit
from ckan.logic.auth import get_resource_object
from ckan.lib.base import _
import ckan.logic.auth as logic_auth


def resource_update(context, data_dict):
    model = context['model']
    user = context.get('user')
    resource = logic_auth.get_resource_object(context, data_dict)

    # check authentication against package
    pkg = model.Package.get(resource.package_id)
    if not pkg:
        raise logic.NotFound(
            _('No package found for this resource, cannot check auth.')
        )

    # check if resource has a newer version
    if 'newerVersion' in resource.extras and resource.extras['newerVersion'] != "":
        return {'success': False, 'msg': 'Older versions cannot be updated'}

    pkg_dict = {'id': pkg.id}
    authorized = authz.is_authorized('package_update', context, pkg_dict).get('success')

    if not authorized:
        return {'success': False,
                'msg': _('User %s not authorized to edit resource %s') %
                        (str(user), resource.id)}
    else:
        return {'success': True}
