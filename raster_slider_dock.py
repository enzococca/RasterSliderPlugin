from qgis.PyQt.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QSlider, QLabel, \
    QPushButton, QFileDialog, QMessageBox, QComboBox
from qgis.PyQt.QtCore import Qt

from qgis.core import QgsProject, QgsLayerTreeGroup,QgsLayerTreeLayer, QgsRasterLayer, QgsPrintLayout, QgsLayoutExporter, QgsLayoutItemMap
from qgis.gui import QgsFileWidget


class RasterSliderDock(QDockWidget):
    def __init__(self, iface):
        super().__init__("Raster Slider")
        self.iface = iface
        self.project = QgsProject.instance()

        self.setup_ui()
        self.connect_signals()
        self.populate_groups()
        self.populate_layouts()

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
        self.layout_combo = QComboBox()
        self.main_layout.addWidget(QLabel("Select Layout:"))
        self.main_layout.addWidget(self.layout_combo)

        # Aggiungiamo un selettore per il formato di esportazione
        self.format_combo = QComboBox()
        self.format_combo.addItems(["GeoTIFF", "GeoPDF", "JPG"])
        self.main_layout.addWidget(QLabel("Export Format:"))
        self.main_layout.addWidget(self.format_combo)

        # Aggiungiamo il bottone di esportazione
        self.export_button = QPushButton("Export Images")
        self.main_layout.addWidget(self.export_button)

        self.setWidget(self.main_widget)


    def connect_signals(self):
        self.group_list.itemSelectionChanged.connect(self.update_slider)
        self.slider.valueChanged.connect(self.update_raster_visibility)
        self.export_button.clicked.connect(self.export_images)

    def populate_layouts(self):
        self.layout_combo.clear()
        for layout in self.project.layoutManager().printLayouts():
            self.layout_combo.addItem(layout.name())

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

    def export_images(self):
        selected_layout_name = self.layout_combo.currentText()
        if not selected_layout_name:
            QMessageBox.warning(self, "Error", "Please select a layout.")
            return

        layout = self.project.layoutManager().layoutByName(selected_layout_name)
        if not layout:
            QMessageBox.warning(self, "Error", "Selected layout not found.")
            return

        export_format = self.format_combo.currentText()
        file_filter = {
            "GeoTIFF": "GeoTIFF (*.tif)",
            "GeoPDF": "GeoPDF (*.pdf)",
            "JPG": "JPEG (*.jpg)"
        }[export_format]

        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_dir:
            return

        selected_groups = [item.text() for item in self.group_list.selectedItems()]

        for group_name in selected_groups:
            group = self.project.layerTreeRoot().findGroup(group_name)
            if group:
                raster_layers = [child for child in group.children() if
                                 isinstance(child, QgsLayerTreeLayer) and isinstance(child.layer(), QgsRasterLayer)]
                raster_layers.reverse()

                for i, layer_node in enumerate(raster_layers):
                    # Imposta la visibilità del layer corrente
                    for j, other_layer in enumerate(raster_layers):
                        other_layer.setItemVisibilityChecked(j >= i)

                    # Aggiorna la mappa nel layout
                    for item in layout.items():
                        if isinstance(item, QgsLayoutItemMap):
                            item.zoomToExtent(self.iface.mapCanvas().extent())

                    # Esporta l'immagine
                    exporter = QgsLayoutExporter(layout)
                    filename = f"{output_dir}/{group_name}_{layer_node.layer().name()}.{export_format.lower()}"

                    if export_format == "GeoTIFF":
                        exporter.exportToImage(filename, QgsLayoutExporter.ImageExportSettings())
                    elif export_format == "GeoPDF":
                        exporter.exportToPdf(filename, QgsLayoutExporter.PdfExportSettings())
                    else:  # JPG
                        exporter.exportToImage(filename, QgsLayoutExporter.ImageExportSettings())

        QMessageBox.information(self, "Export Complete", "Images have been exported successfully.")
