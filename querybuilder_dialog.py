import json
import random
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTextEdit, QLineEdit, QWidget, QDateEdit, QFrame, QFileDialog,
    QMessageBox, QCompleter, QScrollArea, QToolButton, QMenu
)
from qgis.PyQt.QtCore import Qt, QDate
from qgis.PyQt.QtGui import QGuiApplication
from qgis.core import QgsProject, QgsField, QgsVectorLayer, QgsFeatureRequest


class QueryBuilderDialog(QDialog):
    def __init__(self, layer):
        super().__init__()

        # 80 % der Bildschirmgröße
        screen = QGuiApplication.primaryScreen().availableGeometry()
        w = int(screen.width() * 0.8)
        h = int(screen.height() * 0.8)
        self.resize(w, h)

        # Minimieren/Maximieren erlauben
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
        )

        self.setWindowTitle("QueryBuilder  –  v0.2.8")
        self.layout = QVBoxLayout(self)

        # Layer-Auswahl
        hl_layer = QHBoxLayout()
        hl_layer.addWidget(QLabel("Layer:"))
        self.layer_combo = QComboBox()
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer):
                self.layer_combo.addItem(lyr.name(), lyr.id())
        idx = self.layer_combo.findData(layer.id())
        if idx != -1:
            self.layer_combo.setCurrentIndex(idx)
        hl_layer.addWidget(self.layer_combo)
        self.layout.addLayout(hl_layer)
        self.layer_combo.currentIndexChanged.connect(self.on_layer_change)
        self.layer = layer

        # Save/Load Buttons
        hl_top = QHBoxLayout()
        btn_save = QPushButton("💾 Filter speichern")
        btn_load = QPushButton("📂 Filter laden")
        hl_top.addWidget(btn_save)
        hl_top.addWidget(btn_load)
        hl_top.addStretch()
        self.layout.addLayout(hl_top)
        btn_save.clicked.connect(self.save_filter)
        btn_load.clicked.connect(self.load_filter)

        # ScrollArea für Gruppen
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.groups_container = QVBoxLayout(scroll_content)
        scroll_content.setLayout(self.groups_container)
        scroll.setWidget(scroll_content)
        self.layout.addWidget(scroll)

        # Warn-Label bei UND-Falle
        self.warn_label = QLabel(
            "⚠️ Achtung: Alle Gruppen sind mit UND verknüpft –\n"
            "nur Datensätze, die alle Bedingungen erfüllen, bleiben übrig."
        )
        self.warn_label.setStyleSheet("color: #e0a800;")
        self.warn_label.setWordWrap(True)
        self.warn_label.hide()
        self.layout.addWidget(self.warn_label)

        # Ausdrucksvorschau
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.layout.addWidget(QLabel("Erzeugter Ausdruck:"))
        self.layout.addWidget(self.preview)

        # Generate / Copy / Apply Buttons
        btns = QHBoxLayout()
        btn_generate = QPushButton("Ausdruck erzeugen")
        btn_copy    = QPushButton("📋 Kopieren")
        btn_apply   = QPushButton("Filter anwenden (Objekte markieren)")
        btn_generate.clicked.connect(self.generate_expression)
        btn_copy.clicked.connect(self.copy_expression)
        btn_apply.clicked.connect(self.apply_filter)
        btns.addWidget(btn_generate)
        btns.addWidget(btn_copy)
        btns.addWidget(btn_apply)
        self.layout.addLayout(btns)

        # Hinweis am Fuß
        hint = QLabel("Hinweis: Bitte überprüfe den erzeugten Ausdruck auf Richtigkeit.")
        hint.setStyleSheet("color: #888888; font-size: 10pt;")
        hint.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(hint)

        # interne Gruppen-Liste & globaler Button
        self.groups = []
        self.add_group()
        btn_add_group = QPushButton("+ Gruppe hinzufügen")
        btn_add_group.clicked.connect(self.add_group)
        self.layout.insertWidget(self.layout.indexOf(self.warn_label) + 1, btn_add_group)

        self.update_warning()


    def on_layer_change(self, index):
        self.layer = QgsProject.instance().mapLayer(self.layer_combo.currentData())
        self.reset_ui()


    def reset_ui(self):
        while self.groups:
            grp = self.groups.pop()
            grp["frame"].deleteLater()
        self.preview.clear()
        self.add_group()
        self.update_warning()


    def create_input_widget(self, is_date, field_name=None):
        if is_date:
            dt = QDateEdit(); dt.setCalendarPopup(True)
            dt.setDisplayFormat("yyyy-MM-dd"); dt.setDate(QDate.currentDate())
            return dt
        le = QLineEdit()
        if field_name:
            vals = {
                feat[field_name]
                for feat in self.layer.getFeatures(QgsFeatureRequest())
                if feat[field_name] not in (None, '')
            }
            comp = QCompleter(sorted(str(v) for v in vals), self)
            comp.setCaseSensitivity(Qt.CaseInsensitive)
            le.setCompleter(comp)
        return le


    def is_date_field(self, field_name):
        for f in self.layer.fields():
            if f.name() == field_name:
                return "date" in f.typeName().lower()
        return False


    def friendly_alias(self, f: QgsField):
        idx = self.layer.fields().indexOf(f.name())
        alias = self.layer.attributeAlias(idx)
        return alias or f.name().replace("_", " ").title()


    def add_group(self):
        grp = {}
        frame = QFrame(); frame.setFrameShape(QFrame.StyledPanel)
        grp["frame"] = frame
        vbox = QVBoxLayout(frame)
        self.groups_container.addWidget(frame)

        hl = QHBoxLayout()
        op = QComboBox(); op.addItems(["UND", "ODER"])
        if self.groups:
            op.setCurrentText("ODER")
        else:
            op.setCurrentText("UND"); op.setDisabled(True)
        btn_dup = QPushButton("🗐"); btn_del = QPushButton("🗑️")
        hl.addWidget(QLabel("Verknüpfung:")); hl.addWidget(op)
        hl.addStretch(); hl.addWidget(btn_dup); hl.addWidget(btn_del)
        vbox.addLayout(hl)
        op.currentTextChanged.connect(self.update_warning)

        cond_box = QVBoxLayout(); grp["conds"] = cond_box
        vbox.addLayout(cond_box)

        btn_add = QPushButton("  + Bedingung hinzufügen"); grp["add"] = btn_add
        vbox.addWidget(btn_add)

        grp.update({"op": op, "dup": btn_dup, "del": btn_del, "blocks": []})
        self.groups.append(grp)
        btn_add.clicked.connect(lambda _, g=grp: self.add_condition(g))
        btn_dup.clicked.connect(lambda _, g=grp: self.duplicate_group(g))
        btn_del.clicked.connect(lambda _, g=grp: self.remove_group(g))

        self.add_condition(grp)
        self.update_warning()


    def add_condition(self, group):
        blk = {}; hl = QHBoxLayout()

        fld = QComboBox()
        for f in self.layer.fields():
            fld.addItem(f"{self.friendly_alias(f)} ({f.name()})", f.name())

        op = QComboBox(); op.addItems([
            "=", "!=", ">", "<", ">=", "<=", "zwischen",
            "enthält", "ist leer", "ist nicht leer"
        ])

        inp1 = self.create_input_widget(False)
        inp2 = self.create_input_widget(False); inp2.hide()
        btn_del = QPushButton("❌"); btn_del.setToolTip("Diese Bedingung löschen")

        # Werte-Button
        btn_vals = QToolButton(); btn_vals.setText("▾")
        menu = QMenu(btn_vals)
        menu.addAction("Alle eindeutigen Werte")
        menu.addAction("10 Stichproben")
        menu.addAction("Nur verwendete Werte")
        btn_vals.setMenu(menu); btn_vals.setPopupMode(QToolButton.InstantPopup)
        hl.addWidget(btn_vals)
        # immer aktuelles inp1 referenzieren
        menu.triggered.connect(lambda action, b=blk:
            self.load_field_values(action.text(), b["fld"].currentData(), b["in1"])
        )

        for w in (fld, op, inp1, inp2, btn_del):
            hl.addWidget(w)

        container = QWidget(); container.setLayout(hl)
        group["conds"].addWidget(container)

        blk.update({
            "fld": fld, "op": op,
            "in1": inp1, "in2": inp2,
            "del_btn": btn_del, "container": container
        })
        group["blocks"].append(blk)

        def update_widgets():
            name = fld.currentData()
            date_field = self.is_date_field(name)
            oper = op.currentText()
            for w in (blk["in1"], blk["in2"]):
                hl.removeWidget(w); w.deleteLater()
            blk["in1"] = self.create_input_widget(date_field, name)
            blk["in2"] = self.create_input_widget(date_field, name)
            blk["in2"].setVisible(oper == "zwischen")
            hl.insertWidget(2, blk["in1"]); hl.insertWidget(3, blk["in2"])

        fld.currentIndexChanged.connect(update_widgets)
        op.currentTextChanged.connect(update_widgets)
        update_widgets()

        btn_del.clicked.connect(lambda: (
            group["conds"].removeWidget(container),
            container.deleteLater(),
            group["blocks"].remove(blk)
        ))


    def duplicate_group(self, group):
        self.add_group()
        new = self.groups[-1]; old = group["blocks"]
        w = new["conds"].takeAt(0).widget(); w.deleteLater()
        new["blocks"].clear()

        for ob in old:
            self.add_condition(new)
            nb = new["blocks"][-1]
            nb["fld"].setCurrentIndex(ob["fld"].currentIndex())
            nb["op"].setCurrentIndex(ob["op"].currentIndex())
            t1 = ob["in1"].date().toString("yyyy-MM-dd") if hasattr(ob["in1"], "date") else ob["in1"].text()
            t2 = ob["in2"].date().toString("yyyy-MM-dd") if hasattr(ob["in2"], "date") else ob["in2"].text()
            if hasattr(nb["in1"], "setDate"):
                nb["in1"].setDate(QDate.fromString(t1, "yyyy-MM-dd"))
            else:
                nb["in1"].setText(t1)
            if hasattr(nb["in2"], "setDate"):
                nb["in2"].setDate(QDate.fromString(t2, "yyyy-MM-dd"))
            else:
                nb["in2"].setText(t2)

        self.update_warning()


    def remove_group(self, group):
        if len(self.groups) <= 1:
            return
        idx = self.groups.index(group)
        group["frame"].deleteLater()
        self.groups.pop(idx)
        if idx == 0:
            self.groups[0]["op"].setDisabled(True)
        self.update_warning()


    def get_val(self, w):
        if hasattr(w, "date"):
            return w.date().toString("yyyy-MM-dd")
        return w.text().strip()


    def generate_expression(self):
        parts = []
        for i, grp in enumerate(self.groups):
            conds = []
            for blk in grp["blocks"]:
                f = blk["fld"].currentData()
                op_text = blk["op"].currentText()
                v1 = self.get_val(blk["in1"]); v2 = self.get_val(blk["in2"])
                if op_text == "ist leer":
                    conds.append(f"(\"{f}\" IS NULL OR \"{f}\" = '{{}}')")
                elif op_text == "ist nicht leer":
                    conds.append(f"(\"{f}\" IS NOT NULL AND \"{f}\" != '{{}}')")
                elif op_text == "enthält":
                    conds.append(f"\"{f}\" ILIKE '%{v1}%'")
                elif op_text == "zwischen":
                    conds.append(f"\"{f}\" >= '{v1}' AND \"{f}\" <= '{v2}'")
                elif v1:
                    if v1.replace(".", "", 1).isdigit():
                        conds.append(f"\"{f}\" {op_text} {v1}")
                    else:
                        conds.append(f"\"{f}\" {op_text} '{v1}'")
            expr = "(" + " AND ".join(conds) + ")"
            if i == 0:
                parts.append(expr)
            else:
                conj = " AND " if grp["op"].currentText() == "UND" else " OR "
                parts.append(conj + expr)
        self.preview.setText("".join(parts))


    def apply_filter(self):
        expr = self.preview.toPlainText()
        if expr:
            self.layer.removeSelection()
            self.layer.selectByExpression(expr, QgsVectorLayer.SetSelection)


    def copy_expression(self):
        expr = self.preview.toPlainText()
        if expr:
            QGuiApplication.clipboard().setText(expr)


    def save_filter(self):
        path, _ = QFileDialog.getSaveFileName(self, "Filter speichern", "", "JSON Files (*.json*)")
        if not path:
            return
        data = {"version": "v0.2.8", "groups": []}
        for grp in self.groups:
            grp_data = {"op": grp["op"].currentText(), "blocks": []}
            for blk in grp["blocks"]:
                bd = {
                    "field": blk["fld"].currentData(),
                    "operator": blk["op"].currentText(),
                    "value1": self.get_val(blk["in1"]),
                    "value2": self.get_val(blk["in2"])
                }
                grp_data["blocks"].append(bd)
            data["groups"].append(grp_data)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Speichern fehlgeschlagen:\n{e}")


    def load_filter(self):
        path, _ = QFileDialog.getOpenFileName(self, "Filter laden", "", "JSON Files (*.json*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Laden fehlgeschlagen:\n{e}")
            return

        for grp in list(self.groups)[1:]:
            self.remove_group(grp)
        first = self.groups[0]
        for blk in list(first["blocks"]):
            widget = blk["container"]
            first["conds"].removeWidget(widget)
            widget.deleteLater()
            first["blocks"].remove(blk)

        for i, grp_data in enumerate(data.get("groups", [])):
            if i > 0:
                self.add_group()
            grp = self.groups[i]
            grp["op"].setCurrentText(grp_data.get("op", "UND"))
            for blk_data in grp_data.get("blocks", []):
                self.add_condition(grp)
                blk = grp["blocks"][-1]
                blk["fld"].setCurrentIndex(blk["fld"].findData(blk_data.get("field","")))
                blk["op"].setCurrentText(blk_data.get("operator","="))
                if hasattr(blk["in1"], "setDate"):
                    try:
                        d = QDate.fromString(blk_data.get("value1",""), "yyyy-MM-dd")
                        blk["in1"].setDate(d)
                    except:
                        blk["in1"].setDate(QDate.currentDate())
                    try:
                        d2 = QDate.fromString(blk_data.get("value2",""), "yyyy-MM-dd")
                        blk["in2"].setDate(d2)
                    except:
                        blk["in2"].setDate(QDate.currentDate())
                else:
                    blk["in1"].setText(blk_data.get("value1",""))
                    blk["in2"].setText(blk_data.get("value2",""))

        self.generate_expression()
        self.update_warning()


    def update_warning(self):
        if len(self.groups) > 1 and all(grp["op"].currentText() == "UND" for grp in self.groups[1:]):
            self.warn_label.show()
        else:
            self.warn_label.hide()


    def load_field_values(self, mode: str, field_name: str, lineedit: QLineEdit):
        """
        Füllt den Completer und zeigt ihn sofort an:
          - Alle eindeutigen Werte
          - 10 Stichproben
          - Nur verwendete Werte (aktuelle Features)
        """
        req = QgsFeatureRequest()
        distinct = {
            feat[field_name]
            for feat in self.layer.getFeatures(req)
            if feat[field_name] not in (None, '')
        }

        if mode == "Alle eindeutigen Werte":
            vals = distinct
        elif mode == "10 Stichproben":
            vals = set(random.sample(list(distinct), min(10, len(distinct))))
        else:
            vals = distinct

        comp = QCompleter(sorted(str(v) for v in vals), self)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        lineedit.setCompleter(comp)
        comp.complete()
