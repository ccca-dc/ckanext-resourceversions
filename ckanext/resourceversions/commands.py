import ckan.plugins.toolkit as tk
import ckan.lib.base as base

import ckan.model as model
import ckan.logic as logic
import ckan.lib.helpers as h

import ckan.lib.cli as cli
from pprint import pprint

import logging
import re
import json

log = logging.getLogger(__name__)


from ckan.logic.validators import isodate

get_action = logic.get_action
context = tk.c
Base_c = base.c
global_contains_field = []

class ResourceVersionsCommand(cli.CkanCommand):

    '''  A command for working with taxonomies

    Usage::
      ds vpurge [name ohne v]    -  removes ALL  dataset VERSIONS from db entirely
      ds vshow  [name ohne v]    -  show newest version of dataset


    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__

    def __init__(self, name):

        super(ResourceVersionsCommand, self).__init__(name)

    def command(self):
        self._load_config()

        if not self.args:
            print self.usage
        else:
            cmd = self.args[0]

            if cmd == 'vpurge':
                self.vpurge(self.args[1])
            elif cmd == 'vshow':
                self.vshow(self.args[1])

    def _vget(self,name):
        '''Returns a package '''

        import ckan.model as model
        import ckan.logic as logic

        self.context = {'model': model, 'ignore_auth': True }

        try:
            pkg = logic.get_action('package_show')(
                self.context,
                {'id': name})
        except logic.NotFound:
            r1 = re.compile("-v..$")
            if not r1.search(name):
                try:
                    pkg = logic.get_action('package_show')(
                        self.context,
                        {'id': name + '-v01'})
                except logic.NotFound:
                    return pkg

                pkg_save = pkg
                has_newer_version = True
                while has_newer_version is True:
                    has_newer_version = False
                    relations = pkg_save['extras']
                    relations = relations['relations']
                    relations = json.loads(relations)
                    if relations and type(relations) == list and len(relations) > 0 and type(relations[0]) == dict:
                        #print "*************vget***********************2"
                        newer_versions = [element['id'] for element in relations if element['relation'] == 'has_version']
                        if len(newer_versions) > 0:
                            try:
                                pkg = logic.get_action('package_show')(
                                    self.context,
                                    {'id': newer_versions[0]})
                            except logic.NotFound:
                                pkg = pkg_save
                                has_newer_version = False
                                break

                            pkg_save = pkg
                            has_newer_version = True

                        else:
                            pkg = pkg_save
                            has_newer_version = False
                    else:
                        pkg = pkg_save
                        has_newer_version = False

        if pkg['name']:
            print "newest version: " + pkg['name']
        return pkg
    # Todo: Make sure package names can't be changed to look like package IDs?

    def _version_get_dataset(self, dataset_ref):
        import ckan.model as model
        #print dataset_ref
        dataset =self._vget(unicode(dataset_ref))
        assert dataset, 'Could not find dataset matching reference: %r' % dataset_ref
        return dataset

    def vshow(self, dataset_ref):
        import pprint
        dataset = self._version_get_dataset(dataset_ref)
        pprint.pprint(dataset)

    def vpurge(self, dataset_ref):
        import ckan.logic as logic
        # get with newest version
        dataset = self._version_get_dataset(dataset_ref)

        name = dataset['name']
        #print name

        site_user = logic.get_action('get_site_user')({'ignore_auth': True}, {})
        context = {'user': site_user['name']}

        r1 = re.compile("-v..$")
        if r1.search(name):
            print "newest version: " + str(name)

        version = name.split("-v")

        #v = int(version[1])
        #name = version[0]

        # New from Kathi
        v = int(version[-1])
        name = "-v".join(version[:-1])


        for i in range(1, v+1):
            ver = str(i).zfill(2)
            nname = name +   '-v' + ver
            try:
                logic.get_action('dataset_purge')(
                context, {'id': nname})
                print '%s purged' % nname
            except:
                # Exception if not all version numbers exist (subset)
                print "Some exception: " + nname
                pass
