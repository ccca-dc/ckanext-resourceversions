import ckan.logic as logic
import ckan.authz as authz
import ckan.plugins.toolkit as toolkit
from ckan.logic.auth import get_resource_object
from ckan.lib.base import _


def package_delete(context, data_dict):
    # Defer authorization for package_delete to package_update, as deletions
    # are essentially changing the state field
    package = toolkit.get_action('package_show')(data_dict={'id': data_dict['id']})

    # check if package is public
    if package['private'] is False:
        return {'success': False, 'msg': 'Public datasets cannot be deleted'}

    return authz.is_authorized('package_update', context, data_dict)


def resource_delete(context, data_dict):
    model = context['model']
    user = context.get('user')
    resource = get_resource_object(context, data_dict)

    # check authentication against package
    pkg = model.Package.get(resource.package_id)
    if not pkg:
        raise logic.NotFound(_('No package found for this resource, cannot check auth.'))

    # check if package is public
    if pkg['private'] is False:
        return {'success': False, 'msg': 'Public resources cannot be deleted'}

    pkg_dict = {'id': pkg.id}
    authorized = authz.is_authorized('package_delete', context, pkg_dict).get('success')

    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to delete resource %s') % (user, resource.id)}
    else:
        return {'success': True}
