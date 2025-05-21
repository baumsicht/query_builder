from qgis.PyQt.QtWidgets import QAction, QMessageBox
from .querybuilder_dialog import QueryBuilderDialog

class QueryBuilder:
    def __init__(self, iface):
        self.iface = iface
        self.action = None

    def initGui(self):
        self.action = QAction("QueryBuilder", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("QueryBuilder", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu("QueryBuilder", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        layer = self.iface.activeLayer()
        if not layer:
            QMessageBox.warning(None, "QueryBuilder", "Kein aktiver Layer gefunden.")
            return
        dialog = QueryBuilderDialog(layer)
        dialog.show()
