import os
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from .raster_slider_dock import RasterSliderDock

class RasterSliderPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.dock = None
        self.action = None

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), 'icon', 'icon.png')
        self.action = QAction(QIcon(icon_path), "Raster Slider", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("Raster Slider", self.action)

    def unload(self):
        self.iface.removePluginMenu("Raster Slider", self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.dock:
            self.iface.removeDockWidget(self.dock)
            self.dock = None

    def run(self):
        if not self.dock:
            from .raster_slider_dock import RasterSliderDock
            self.dock = RasterSliderDock(self.iface)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        else:
            self.dock.close()
            self.dock = None
            self.run()  # Ricrea il dock widget
