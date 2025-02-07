# :coding: utf-8
# :copyright: Copyright (c) 2016 ftrack

import logging
import os

import ftrack_api
#import ftrack_connect.util
import pyperclip


class CopyComponentDirectoryAction(object):
    '''Action to copy component directory to clipboard.'''

    identifier = 'ftrack-connect-copy-component-directory'

    failed = {
        'success': False,
        'message': ('Could not copy component directory.'),
    }

    def __init__(self, session, logger):
        '''Instantiate action with *session*.'''
        self.session = session
        self.logger = logger

    def discover(self, event):
        '''Discover *event*.'''
        selection = event['data'].get('selection', [])
        if len(selection) == 1 and selection[0]['entityType'] == 'Component':
            return {
                'items': [
                    {
                        'label': 'Copy Directory',
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

        if path != None or path != '':
            # File or directory exists.
            pyperclip.copy(path)
        else:
            # No file, directory or parent directory exists for path.
            self.logger.info(
                'Directory  non-existing {0!r} and {1!r}:'
                '{0!r}'.format(component_id, path)
            )
            return self.failed

        return {
            'success': True,
            'message': 'Successfully copyed component directory.',
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

    action = CopyComponentDirectoryAction(session, logger)
    action.register()
