# :coding: utf-8
# :copyright: Copyright (c) 2016 ftrack

import logging
import os

import ftrack_api
#import ftrack_connect.util

import subprocess
import appdirs
import json
import glob

class OpenComponentUseToolsAction(object):
    '''Action to open component directory use tools.'''

    identifier = 'ftrack-connect-open-component-use-tools'
    

    failed = {
        'success': False,
        'message': ('Could not open file.'),
    }

    def __init__(self, session, logger):
        '''Instantiate action with *session*.'''
        self.session = session
        self.logger = logger
        self.apps = self.getAppInfo()

    def findApp(self,data):
        app_list = {}
        for app_file in data['Apps']:
            app_list[app_file["name"]]=data['Directory']+app_file["name"]+"*.exe"
            
        app_dir = {}
        for key in list(app_list.keys()):
            appPath = sorted(glob.glob(app_list[key]),reverse = True)
            if len(appPath) > 0:
                app_dir[key] = appPath[0]
            else:
                app_dir[key] = ""
        return app_dir
            
                
         
        
    def getAppInfo(self):
        cwd = os.path.dirname(__file__)
        app_file = os.path.join(cwd,'app.json')
        data  = []
        
        if os.path.exists(app_file):
            with open(app_file, 'r') as f:
                data = json.load(f)
        
        else:
            self.logger.error("没有找到app.json文件")
            return


        file_name = 'appConfig.json'
        file_path = os.path.abspath(
            appdirs.user_data_dir('ftrack-connect', 'ftrack')
            )
        json_file_path = os.path.join(file_path,file_name)
        
        apps = {}
        if os.path.exists(json_file_path):
            with open(json_file_path,'r') as _data:
                apps = json.load(_data)
        else:  
            apps = self.findApp(data)
            with open(json_file_path,'w') as file:
                json.dump(apps,file)
        
        appInfo = []
        for item in data['Apps']:
            appInfo.append(
                {
                "name":item["name"],
                "path":apps[item["name"]],
                "file_type":item["file_type"]
                }
            )
        return appInfo
        
        


            
                
            


    def discover(self, event):
        '''Discover *event*.'''
        selection = event['data'].get('selection', [])
        if len(selection) == 1 and selection[0]['entityType'] == 'Component':
            
                
            return {
                'items': [
                    {
                        'label': 'Open File Use Tools',
                        'actionIdentifier': self.identifier,
                    }
                ]
            }

    def resolve_path(self, component_id):
        '''Return path from *component_id*.'''

        location = None
        component = None
        try:
            component = self.session.get('Component', component_id)
            location = self.session.pick_location(component)
        except Exception:
            self.logger.exception(
                'Could not pick location for component {0!r}'.format(component)
            )

        path = None
        if location:
            try:
                path = location.get_filesystem_path(component)
            except ftrack_api.exception.AccessorUnsupportedOperationError:
                self.logger.warn(
                    'Component {0!r} does not support filesystem access for '
                    '{1!r}'.format(component, location)
                )
            self.logger.info('Location is only in api: {0!r}'.format(location))
        return path
    

    def launch(self, event):
        '''Launch action for *event*.'''
        selection = event['data']['selection'][0]

        if selection['entityType'] != 'Component':
            return

        path = None
        component_id = selection['entityId']
        try:
            path = self.resolve_path(component_id)
        except Exception:
            self.logger.exception(
                'Exception raised while resolving component with id '
                '{0!r}'.format(component_id)
            )

        if path is None:
            self.logger.info(
                'Could not determine a valid file system path for: '
                '{0!r}'.format(component_id)
            )
            return self.failed

        if os.path.exists(path) or os.path.exists(os.path.dirname(path)):
            for item in self.apps:
                subName = os.path.splitext(path)[1]
                #print(subName)
                for file_type in item['file_type']:
                    if subName == file_type:
                        print(item['name'])
                        if item['path'] != "":
                            subprocess.run([item['path'],path])
                        else:
                            return {
                                    'success': False,
                                    'message': '你需要安装 {0}'.format(item['name'])
                            }

            return {
                                    'success': False,
                                    'message': '文件格式不支持，请联系技术支持'
                            }
                    
            
        else:
            # No file, directory or parent directory exists for path.
            self.logger.info(
                'Directory resolved but non-existing {0!r} and {1!r}:'
                '{0!r}'.format(component_id, path)
            )
            return self.failed

        return {
            'success': True,
            'message': 'Successfully open component use tools.',
        }

    def register(self):
        '''Register to event hub.'''
        self.session.event_hub.subscribe(
            u'topic=ftrack.action.discover '
            u'and source.user.username="{0}"'.format(self.session.api_user),
            self.discover,
        )

        self.session.event_hub.subscribe(
            'topic=ftrack.action.launch and data.actionIdentifier={0} and '
            'source.user.username="{1}"'.format(
                self.identifier, self.session.api_user
            ),
            self.launch,
        )


def register(session, **kw):
    '''Register hooks.'''

    logger = logging.getLogger('ftrack_connect:copy-component-directory')

    # Validate that session is an instance of ftrack_api.session.Session. If
    # not, assume that register is being called from an old or incompatible API
    # and return without doing anything.
    if not isinstance(session, ftrack_api.Session):
        logger.debug(
            'Not subscribing plugin as passed argument {0!r} is not an '
            'Session instance.'.format(session)
        )
        return

    action = OpenComponentUseToolsAction(session, logger)
    action.register()
