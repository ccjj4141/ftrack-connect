# :coding: utf-8
# :copyright: Copyright (c) 2016 ftrack

import logging
import os

import ftrack_api
#import ftrack_connect.util

import subprocess
import appdirs
import json
import re

class OpenComponentUseToolsSwitchByFileTypeAction(object):
    '''Action to open component directory use tools.'''

    
    

    failed = {
        'success': False,
        'message': ('无法打开文件'),
    }

    def __init__(self, session, logger):
        '''Instantiate action with *session*.'''
        self.session = session
        self.logger = logger
        self.app_name = 'rv'
        self.search_path = "C:\\Program Files\\"
        self.apps = self.getAppInfo()
        
        

    def getAppInfo(self):
        appInfo = []
        cwd = os.path.dirname(__file__)
        app_json = os.path.join(cwd,'app.json')
        apps  = []
        search_path = []
        with open(app_json,'r') as f:
            apps = json.load(f)
        for app in apps['Apps']:
            if len(app['search_path']) > 0:
                for target_path in app['search_path']:
                    for subdirectory in os.listdir(apps['Directory']):
                        if  target_path.lower() in subdirectory.lower():
                            #search_path.append(os.path.join(apps['Directory'],subdirectory))
                            #print(os.path.join(apps['Directory'],subdirectory))
                            for root,dirs,files in os.walk(os.path.join(apps['Directory'],subdirectory)):
                                
                                for file in files:
                                    file_lower = file.lower()
                                    if (file_lower == app["file_name"]+'.exe') or (
                                        file_lower.startswith(app["file_name"]) and bool(re.search(r'\d',file_lower)) and file.endswith('.exe')
                                    ):
                                        #print(file_lower)
                                        _name = self.check_appVersion(app["version_name"],os.path.join(root,file)).replace(" ","")
                                        appInfo.append({"name":_name,
                                                        "path":os.path.join(root,file),
                                                        "identifier":"ftrack-connect-open-component-use-{0}".format(_name),
                                                        "file_type":app["file_type"]}) 
            for _path in app['custom_path']:
                
                if os.path.exists(_path):
                    #print(_path)
                    _name = self.check_appVersion(app["version_name"],_path).replace(" ","")
                    appInfo.append({"name":_name,
                                    "path":_path,
                                    "identifier":"ftrack-connect-open-component-use-{0}".format(_name),
                                    "file_type":app["file_type"]}) 
        #print(appInfo)
        return appInfo    

    def check_appVersion(self,name,path):
            # 获取文件名
        filename = os.path.basename(path)
        # 匹配文件名是否包含"nuke"和数字
        if filename.endswith('.exe'):
            folders = list(reversed(path.split(os.sep)))
            #print(folders)
            while len(folders) > 0:
                
                folder = folders.pop()
                match = any(char.isdigit() for char in folder) and (name in folder.lower())
                if match:
                    if folder.endswith('.exe'):
                        return ".".join(folder.split(".")[:-1])
                    else:
                        return folder
            
            return os.path.splitext(filename)[0]


        
    
        
        


            
                
            


    def discover(self, event):
        '''Discover *event*.'''
        selection = event['data'].get('selection', [])
        if len(selection) == 1 and selection[0]['entityType'] == 'Component':
            path = None
            component_id = selection[0]['entityId']
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
            
            file_type = os.path.splitext(path)[1]
            #print(file_type)

            
            items = []
            for item in self.apps:
                if file_type in item['file_type']:
                    items.append({'label' : item['name'],'actionIdentifier':item['identifier']})
            return {
                'items': items
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
            app_path = ""
            identifier = event['data']['actionIdentifier']
            for app in self.apps:
                if app['identifier'] == identifier:
                    app_path = app['path']
            if app_path != "":
                subprocess.Popen([app_path,path],shell=True)
                return{
                   'success': True,
                   'message': '你已成功打开文件'
                    }
            else:
                return {
                       'success': False,
                       'message': '你需要安装软件'
                       }

            
                    
            
        else:
            # No file, directory or parent directory exists for path.
            self.logger.info(
                'Directory resolved but non-existing {0!r} and {1!r}:'
                '{0!r}'.format(component_id, path)
            )
            return self.failed

        

    def register(self):
        '''Register to event hub.'''
        self.session.event_hub.subscribe(
            u'topic=ftrack.action.discover '
            u'and source.user.username="{0}"'.format(self.session.api_user),
            self.discover,
        )

        for app in self.apps:
            self.session.event_hub.subscribe(
                'topic=ftrack.action.launch and data.actionIdentifier={0} and '
                'source.user.username="{1}"'.format(
                    app['identifier'], self.session.api_user
                ),
                self.launch,
            )


def register(session, **kw):
    '''Register hooks.'''
    
    
    logger = logging.getLogger('ftrack_connect:open-component-use-tools')

    # Validate that session is an instance of ftrack_api.session.Session. If
    # not, assume that register is being called from an old or incompatible API
    # and return without doing anything.
    if not isinstance(session, ftrack_api.Session):
        logger.debug(
            'Not subscribing plugin as passed argument {0!r} is not an '
            'Session instance.'.format(session)
        )
        return

    action = OpenComponentUseToolsSwitchByFileTypeAction(session, logger)
    action.register()
