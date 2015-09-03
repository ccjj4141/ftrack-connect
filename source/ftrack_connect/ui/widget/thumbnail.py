# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import os
import urllib2

from PySide import QtGui, QtCore
import ftrack
import ftrack_connect.worker

# Cache of thumbnail images.
IMAGE_CACHE = dict()


class Base(QtGui.QLabel):
    '''Widget to load thumbnails from ftrack server.'''

    def __init__(self, parent=None):
        super(Base, self).__init__(parent)

        self.thumbnailCache = {}
        self.setFrameStyle(QtGui.QFrame.StyledPanel)
        self.setAlignment(QtCore.Qt.AlignCenter)

        self.placholderThumbnail = (os.environ['FTRACK_SERVER']
                                    + '/img/thumbnail2.png')

        self._worker = None
        self.__loadingReference = None

    def load(self, reference):
        '''Load thumbnail from *reference* and display it.'''
        if reference in IMAGE_CACHE:
            self._updatePixmapData(IMAGE_CACHE[reference])
            return

        if self._worker and self._worker.isRunning():
            while self._worker:
                app = QtGui.QApplication.instance()
                app.processEvents()

        self._worker = ftrack_connect.worker.Worker(
            self._download, [reference], parent=self
        )

        self.__loadingReference = reference
        self._worker.start()
        self._worker.finished.connect(self._workerFinnished)

    def _workerFinnished(self):
        '''Handler worker finished event.'''
        if self._worker:
            IMAGE_CACHE[self.__loadingReference] = self._worker.result
            self._updatePixmapData(self._worker.result)

        self._worker = None
        self.__loadingReference = None

    def _updatePixmapData(self, data):
        '''Update thumbnail with *data*.'''
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(data)
        self._scaleAndSetPixmap(pixmap)

    def _scaleAndSetPixmap(self, pixmap):
        '''Scale and set *pixmap*.'''
        scaledPixmap = pixmap.scaledToWidth(
            self.width(),
            mode=QtCore.Qt.SmoothTransformation
        )
        self.setPixmap(scaledPixmap)

    def _download(self, url):
        '''Return thumbnail file from *url*.'''
        if url is None:
            url = self.placholderThumbnail

        ftrackProxy = os.getenv('FTRACK_PROXY', '')
        ftrackServer = os.getenv('FTRACK_SERVER', '')
        if ftrackProxy != '':
            if ftrackServer.startswith('https'):
                httpHandle = 'https'
            else:
                httpHandle = 'http'

            proxy = urllib2.ProxyHandler({httpHandle: ftrackProxy})
            opener = urllib2.build_opener(proxy)
            response = opener.open(url)
            html = response.read()
        else:
            response = urllib2.urlopen(url)
            html = response.read()

        return html

class EllipseBase(Base):
    '''Thumbnail which is drawn as an ellipse.'''

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHints(
            QtGui.QPainter.Antialiasing,
            True
        )

        brush = QtGui.QBrush(
            self.pixmap()
        )

        painter.setBrush(brush)

        painter.setPen(
            QtGui.QPen(
                QtGui.QColor(0, 0, 0, 0)
            )
        )

        painter.drawEllipse(
            QtCore.QRectF(
                0, 0,
                self.width(), self.height()
            )
        )

class User(EllipseBase):

    def _download(self, reference):
        url = ftrack.User(reference).getThumbnail()
        return super(User, self)._download(url)

class ActionIcon(Base):
    '''Widget to load action icons over HTTP.'''

    #: Available icons on ftrack server.
    AVAILABLE_ICONS = {
        'hiero': '/application_icons/hiero.png',
        'hieroplayer': '/application_icons/hieroplayer.png',
        'nukex': '/application_icons/nukex.png',
        'nuke': '/application_icons/nuke.png',
        'nuke_studio': '/application_icons/nuke_studio.png',
        'premiere': '/application_icons/premiere.png',
        'maya': '/application_icons/maya.png',
        'cinesync': '/application_icons/cinesync.png',
        'photoshop': '/application_icons/photoshop.png',
        'prelude': '/application_icons/prelude.png',
        'after_effects': '/application_icons/after_effects.png'
    }

    def __init__(self, parent=None):
        '''Initialize action icon.'''
        super(ActionIcon, self).__init__(parent)
        self.setFrameStyle(QtGui.QFrame.NoFrame)

    def setIcon(self, icon):
        '''Set *icon* to a supported icon or show the standard icon.

        *icon* may be one of the following.

            * A URL to load the image from starting with 'http'.
            * One of the predefined icons in AVAILABLE_ICONS
        '''
        if icon and icon[:4] == 'http':
            self.load(icon)
        elif self.AVAILABLE_ICONS.get(icon):
            url = os.environ['FTRACK_SERVER'] + self.AVAILABLE_ICONS[icon]
            self.load(url)
        else:
            self.loadResource(':/ftrack/image/light/action')

    def loadResource(self, resource):
        '''Update current pixmap using *resource*.'''
        pixmap = QtGui.QPixmap(
            QtCore.QSize(self.width(), self.height())
        )
        pixmap.load(resource)
        self._scaleAndSetPixmap(pixmap)

    def _scaleAndSetPixmap(self, pixmap):
        '''Scale *pixmap* to fit within current bounds'''
        scaledPixmap = pixmap.scaled(
            self.width(), self.height(), QtCore.Qt.KeepAspectRatio, 
            QtCore.Qt.SmoothTransformation
        )
        self.setPixmap(scaledPixmap)
