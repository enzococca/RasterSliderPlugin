from qgis.PyQt.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
                                 QListWidget, QSlider, QLabel, QPushButton,
                                 QFileDialog, QMessageBox, QComboBox, QProgressBar,
                                 QListWidgetItem, QCheckBox, QApplication)
from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QPixmap, QIcon
from qgis.core import (QgsProject, QgsLayerTreeGroup, QgsLayerTreeLayer, QgsRasterLayer,
                       QgsPrintLayout, QgsLayoutExporter, QgsLayoutItemMap,
                       QgsVectorLayer)
from qgis.gui import QgsFileWidget

import os


class RasterSliderDock(QDockWidget):
    def __init__(self, iface):
        super().__init__("Raster Slider")
        self.iface = iface
        self.project = QgsProject.instance()

        self.setup_ui()
        self.connect_signals()
        self.populate_groups()
        self.populate_layouts()
        self.populate_vector_layers()

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

        # Aggiungiamo la barra di progresso
        self.progress_bar = QProgressBar()
        self.main_layout.addWidget(self.progress_bar)

        # Aggiungiamo la lista widget per le anteprime
        self.preview_list = QListWidget()
        self.preview_list.setIconSize(QSize(100, 100))  # Imposta la dimensione delle icone
        self.main_layout.addWidget(self.preview_list)

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

        use_atlas = self.use_atlas_checkbox.isChecked()
        coverage_layer_id = self.coverage_layer_combo.currentData() if use_atlas else None

        if use_atlas:
            coverage_layer = self.project.mapLayer(coverage_layer_id)
            if not coverage_layer:
                QMessageBox.warning(self, "Error", "Selected coverage layer not found.")
                return

            layout.atlas().setCoverageLayer(coverage_layer)
            layout.atlas().setEnabled(True)
        else:
            layout.atlas().setEnabled(False)
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

        # Calcola il numero totale di esportazioni
        total_exports = 0
        for group_name in selected_groups:
            group = self.project.layerTreeRoot().findGroup(group_name)
            if group:
                raster_layers = [child for child in group.children() if
                                 isinstance(child, QgsLayerTreeLayer) and isinstance(child.layer(), QgsRasterLayer)]
                total_exports += len(raster_layers)

        if use_atlas:
            total_exports *= coverage_layer.featureCount()

        self.progress_bar.setMaximum(total_exports)
        self.progress_bar.setValue(0)

        self.preview_list.clear()

        export_count = 0
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

                    if use_atlas:
                        layout.atlas().beginRender()
                        for feature in coverage_layer.getFeatures():
                            layout.atlas().seekTo(feature)
                            self.export_single_image(layout, output_dir, group_name, layer_node, export_format,
                                                     f"_{feature.id()}")
                            export_count += 1
                            self.progress_bar.setValue(export_count)
                            QApplication.processEvents()
                        layout.atlas().endRender()
                    else:
                        self.export_single_image(layout, output_dir, group_name, layer_node, export_format)
                        export_count += 1
                        self.progress_bar.setValue(export_count)
                        QApplication.processEvents()

        QMessageBox.information(self, "Export Complete", "Images have been exported successfully.")

    def export_single_image(self, layout, output_dir, group_name, layer_node, export_format, suffix=""):
        exporter = QgsLayoutExporter(layout)
        filename = f"{output_dir}/{group_name}_{layer_node.layer().name()}{suffix}.{export_format.lower()}"

        if export_format == "GeoTIFF":
            exporter.exportToImage(filename, QgsLayoutExporter.ImageExportSettings())
        elif export_format == "GeoPDF":
            exporter.exportToPdf(filename, QgsLayoutExporter.PdfExportSettings())
        else:  # JPG
            image_settings = QgsLayoutExporter.ImageExportSettings()
            image_settings.generateWorldFile = True
            exporter.exportToImage(filename, image_settings)

        self.add_preview_to_list(filename, f"{group_name}: {layer_node.layer().name()}{suffix}")
    def add_preview_to_list(self, image_path, label_text):
        item = QListWidgetItem(label_text)

        # Crea un'anteprima dell'immagine
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item.setIcon(QIcon(pixmap))

        self.preview_list.addItem(item)