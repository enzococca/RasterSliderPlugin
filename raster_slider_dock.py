from qgis.PyQt.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QSlider, QLabel
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject, QgsLayerTreeGroup, QgsRasterLayer, QgsLayerTreeLayer


class RasterSliderDock(QDockWidget):
    def __init__(self, iface):
        super().__init__("Raster Slider")
        self.iface = iface
        self.project = QgsProject.instance()

        self.setup_ui()
        self.connect_signals()
        self.populate_groups()

    def setup_ui(self):
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout()
        self.main_widget.setLayout(self.main_layout)

        self.group_list = QListWidget()
        self.group_list.setSelectionMode(QListWidget.MultiSelection)
        self.main_layout.addWidget(self.group_list)

        self.slider_layout = QHBoxLayout()
        self.main_layout.addLayout(self.slider_layout)

        self.slider = QSlider(Qt.Horizontal)
        self.slider_layout.addWidget(self.slider)

        self.raster_label = QLabel()
        self.main_layout.addWidget(self.raster_label)

        self.setWidget(self.main_widget)

    def connect_signals(self):
        self.group_list.itemSelectionChanged.connect(self.update_slider)
        self.slider.valueChanged.connect(self.update_raster_visibility)

    def populate_groups(self):
        root = self.project.layerTreeRoot()
        for child in root.children():
            if isinstance(child, QgsLayerTreeGroup):
                self.group_list.addItem(child.name())

    def update_slider(self):
        selected_groups = [item.text() for item in self.group_list.selectedItems()]
        max_rasters = max(self.count_rasters(group_name) for group_name in selected_groups) if selected_groups else 0

        self.slider.setMaximum(max_rasters)
        self.slider.setValue(max_rasters)
        self.update_raster_visibility()

    def count_rasters(self, group_name):
        group = self.project.layerTreeRoot().findGroup(group_name)
        return len(
            [child.layer() for child in group.children() if isinstance(child.layer(), QgsRasterLayer)]) if group else 0

    def update_raster_visibility(self):
        selected_groups = [item.text() for item in self.group_list.selectedItems()]
        active_rasters = []
        root = QgsProject.instance().layerTreeRoot()
        for group_name in selected_groups:
            group = root.findGroup(group_name)
            if group:
                raster_layers = [child for child in group.children() if
                                 isinstance(child,  QgsLayerTreeLayer) and isinstance(child.layer(),QgsRasterLayer) ]
                #raster_layers.reverse()
                for i, layer in enumerate(raster_layers):
                    layer.setItemVisibilityChecked(i >= len(raster_layers) - self.slider.value())
                    if i == len(raster_layers) - self.slider.value():
                        active_rasters.append(f"{group_name}: {layer.layer().name()}")

        self.raster_label.setText("\n".join(active_rasters))
        self.iface.mapCanvas().refresh()