# -*- coding: utf-8 -*-
import json
import random
import re
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTextEdit, QLineEdit, QWidget, QDateEdit, QFrame, QFileDialog,
    QMessageBox, QCompleter, QScrollArea, QToolButton, QMenu
)
from qgis.PyQt.QtCore import Qt, QDate
from qgis.PyQt.QtGui import QGuiApplication
from qgis.core import (
    QgsProject, QgsField, QgsVectorLayer, QgsFeatureRequest,
    QgsEditorWidgetSetup
)


class QueryBuilderDialog(QDialog):
    def __init__(self, layer):
        super().__init__()

        # 80 % der Bildschirmgröße, Min/Max-Buttons erlauben
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(int(screen.width() * 0.8), int(screen.height() * 0.8))
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
        )
        self.setWindowTitle("QueryBuilder – v0.4.3")
        self.layout = QVBoxLayout(self)

        # Layer-Auswahl (nur Vektorlayer)
        hl = QHBoxLayout()
        hl.addWidget(QLabel("Layer:"))
        self.layer_combo = QComboBox()
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer):
                self.layer_combo.addItem(lyr.name(), lyr.id())
        idx = self.layer_combo.findData(layer.id())
        if idx != -1:
            self.layer_combo.setCurrentIndex(idx)
        hl.addWidget(self.layer_combo)
        self.layout.addLayout(hl)
        self.layer_combo.currentIndexChanged.connect(self.on_layer_change)
        self.layer = layer

        # Buttons Save/Load
        hl2 = QHBoxLayout()
        btn_save = QPushButton("💾 Filter speichern")
        btn_load = QPushButton("📂 Filter laden")
        hl2.addWidget(btn_save); hl2.addWidget(btn_load); hl2.addStretch()
        self.layout.addLayout(hl2)
        btn_save.clicked.connect(self.save_filter)
        btn_load.clicked.connect(self.load_filter)

        # ScrollArea für Gruppen
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.groups_container = QVBoxLayout(content)
        content.setLayout(self.groups_container)
        scroll.setWidget(content)
        self.layout.addWidget(scroll)

        # Warnung, wenn alle Gruppen UND sind
        self.warn = QLabel(
            "⚠️ Achtung: Alle Gruppen sind mit UND verknüpft –\n"
            "nur Datensätze, die alle Bedingungen erfüllen, bleiben übrig."
        )
        self.warn.setStyleSheet("color: #e0a800;")
        self.warn.setWordWrap(True)
        self.warn.hide()
        self.layout.addWidget(self.warn)

        # Ausdrucksvorschau
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.layout.addWidget(QLabel("Erzeugter Ausdruck:"))
        self.layout.addWidget(self.preview)

        # Aktion-Buttons
        hl3 = QHBoxLayout()
        btn_gen   = QPushButton("Ausdruck erzeugen")
        btn_copy  = QPushButton("📋 Kopieren")
        btn_apply = QPushButton("Filter anwenden (Objekte markieren)")
        hl3.addWidget(btn_gen); hl3.addWidget(btn_copy); hl3.addWidget(btn_apply)
        self.layout.addLayout(hl3)
        btn_gen.clicked.connect(self.generate_expression)
        btn_copy.clicked.connect(self.copy_expression)
        btn_apply.clicked.connect(self.apply_filter)

        # Fußhinweis
        foot = QLabel("Hinweis: Bitte überprüfe den erzeugten Ausdruck auf Richtigkeit.")
        foot.setStyleSheet("color: #888888; font-size: 10pt;")
        foot.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(foot)

        # erste Gruppe + Button zum Hinzufügen weiterer Gruppen
        self.groups = []
        self.add_group()
        btn_grp = QPushButton("+ Gruppe hinzufügen")
        btn_grp.clicked.connect(self.add_group)
        self.layout.insertWidget(self.layout.indexOf(self.warn) + 1, btn_grp)

        self.update_warning()


    def on_layer_change(self, idx):
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
        """
        Erzeugt QDateEdit oder QLineEdit mit Auto-Completer für
        ValueMap / ValueRelation / Fallback auf Layer-Werte.
        """
        if is_date:
            dt = QDateEdit(); dt.setCalendarPopup(True)
            dt.setDisplayFormat("yyyy-MM-dd")
            dt.setDate(QDate.currentDate())
            return dt

        le = QLineEdit()
        if field_name:
            idx = self.layer.fields().indexOf(field_name)
            setup = self.layer.editorWidgetSetup(idx)
            wtype = setup.type()  # String: "ValueMap", "ValueRelation", ...

            # ValueMap
            if wtype == "ValueMap":
                cfg = setup.config()
                disp_map = cfg.get("map", {})
                choices = [f"{disp} ({key})" for key, disp in disp_map.items()]
                comp = QCompleter(sorted(choices), self)
                comp.setCaseSensitivity(Qt.CaseInsensitive)
                comp.setCompletionMode(QCompleter.PopupCompletion)
                comp.activated[str].connect(lambda txt, le=le: le.setText(txt))
                le.setCompleter(comp)
                le._value_map = disp_map
                return le

            # ValueRelation
            if wtype == "ValueRelation":
                cfg = setup.config()
                rel_layer = QgsProject.instance().mapLayer(cfg.get("Layer"))
                keycol, valcol = cfg.get("Key"), cfg.get("Value")
                disp_map = {}
                if isinstance(rel_layer, QgsVectorLayer):
                    for f in rel_layer.getFeatures():
                        disp_map[f[keycol]] = f[valcol]
                choices = [f"{v} ({k})" for k, v in disp_map.items()]
                comp = QCompleter(sorted(choices), self)
                comp.setCaseSensitivity(Qt.CaseInsensitive)
                comp.setCompletionMode(QCompleter.PopupCompletion)
                comp.activated[str].connect(lambda txt, le=le: le.setText(txt))
                le.setCompleter(comp)
                le._value_map = disp_map
                return le

            # Fallback: eindeutige Layer-Werte
            vals = {
                feat[field_name]
                for feat in self.layer.getFeatures(QgsFeatureRequest())
                if feat[field_name] not in (None, '')
            }
            comp = QCompleter(sorted(str(v) for v in vals), self)
            comp.setCaseSensitivity(Qt.CaseInsensitive)
            comp.setCompletionMode(QCompleter.PopupCompletion)
            comp.activated[str].connect(lambda txt, le=le: le.setText(txt))
            le.setCompleter(comp)

        return le


    def is_date_field(self, fname):
        for f in self.layer.fields():
            if f.name() == fname:
                return "date" in f.typeName().lower()
        return False


    def friendly_alias(self, f: QgsField):
        idx = self.layer.fields().indexOf(f.name())
        alias = self.layer.attributeAlias(idx)
        return alias or f.name().replace("_"," ").title()


    def add_group(self):
        grp = {}
        frame = QFrame(); frame.setFrameShape(QFrame.StyledPanel)
        grp["frame"] = frame
        vbox = QVBoxLayout(frame)
        self.groups_container.addWidget(frame)

        # Kopfzeile
        hl = QHBoxLayout()
        op = QComboBox(); op.addItems(["UND","ODER"])
        if self.groups:
            op.setCurrentText("ODER")
        else:
            op.setCurrentText("UND"); op.setDisabled(True)
        btn_dup = QPushButton("🗐"); btn_del = QPushButton("🗑️")
        hl.addWidget(QLabel("Verknüpfung:")); hl.addWidget(op)
        hl.addStretch(); hl.addWidget(btn_dup); hl.addWidget(btn_del)
        vbox.addLayout(hl)
        op.currentTextChanged.connect(self.update_warning)

        # Conditions-Box
        cond_box = QVBoxLayout(); grp["conds"] = cond_box
        vbox.addLayout(cond_box)
        btn_add = QPushButton("  + Bedingung hinzufügen")
        vbox.addWidget(btn_add)

        grp.update({"op":op,"dup":btn_dup,"del":btn_del,"blocks":[]})
        self.groups.append(grp)
        btn_add.clicked.connect(lambda _,g=grp: self.add_condition(g))
        btn_dup.clicked.connect(lambda _,g=grp: self.duplicate_group(g))
        btn_del.clicked.connect(lambda _,g=grp: self.remove_group(g))

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

        inp1 = self.create_input_widget(False, fld.currentData())
        inp2 = self.create_input_widget(False, fld.currentData()); inp2.hide()
        btn_del = QPushButton("❌"); btn_del.setToolTip("Bedingung löschen")

        # Werte-Popup
        btn_vals = QToolButton(); btn_vals.setText("▾"); menu = QMenu(btn_vals)
        for m in ("Alle eindeutigen Werte","10 Stichproben","Nur verwendete Werte"):
            menu.addAction(m)
        btn_vals.setMenu(menu); btn_vals.setPopupMode(QToolButton.InstantPopup)
        hl.addWidget(btn_vals)
        menu.triggered.connect(lambda action, b=blk:
            self.load_field_values(action.text(), b["fld"].currentData(), b["in1"])
        )

        for w in (fld,op,inp1,inp2,btn_del):
            hl.addWidget(w)
        container = QWidget(); container.setLayout(hl)
        group["conds"].addWidget(container)

        blk.update({"fld":fld,"op":op,"in1":inp1,"in2":inp2,
                    "del_btn":btn_del,"container":container})
        group["blocks"].append(blk)

        def rebuild():
            name = fld.currentData(); datef = self.is_date_field(name)
            oper = op.currentText()
            for w in (blk["in1"],blk["in2"]):
                hl.removeWidget(w); w.deleteLater()
            blk["in1"] = self.create_input_widget(datef,name)
            blk["in2"] = self.create_input_widget(datef,name)
            blk["in2"].setVisible(oper=="zwischen")
            hl.insertWidget(2,blk["in1"]); hl.insertWidget(3,blk["in2"])
            menu.triggered.disconnect()
            menu.triggered.connect(lambda action, b=blk:
                self.load_field_values(action.text(), b["fld"].currentData(), b["in1"])
            )

        fld.currentIndexChanged.connect(rebuild)
        op.currentTextChanged.connect(rebuild)
        rebuild()

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
            nb["op"].setCurrentText(ob["op"].currentText())
            for inp in ("in1","in2"):
                raw = (ob[inp].date().toString("yyyy-MM-dd")
                       if hasattr(ob[inp],"date") else ob[inp].text())
                widget = nb[inp]
                if hasattr(widget,"_value_map"):
                    widget.setText(raw + f" ({raw})")
                elif hasattr(widget,"setDate"):
                    widget.setDate(QDate.fromString(raw,"yyyy-MM-dd"))
                else:
                    widget.setText(raw)
        self.update_warning()


    def remove_group(self, group):
        if len(self.groups)<=1: return
        idx = self.groups.index(group)
        group["frame"].deleteLater()
        self.groups.pop(idx)
        if idx==0:
            self.groups[0]["op"].setDisabled(True)
        self.update_warning()


    def get_val(self, w):
        return w.date().toString("yyyy-MM-dd") if hasattr(w,"date") else w.text().strip()


    def _resolve_value_map(self, widget, raw):
        if raw.startswith("{") and raw.endswith("}"):
            items = re.findall(r'"([^"]+)"', raw)
            rev = {v:k for k,v in getattr(widget,"_value_map",{}).items()}
            keys = [rev.get(d,d) for d in items]
            return '{' + ','.join(keys) + '}'
        m = re.match(r'^(.*)\s*\((.*)\)$', raw)
        if m:
            return m.group(2)
        rev = {v:k for k,v in getattr(widget,"_value_map",{}).items()}
        return rev.get(raw, raw)


    def generate_expression(self):
        parts=[]
        for i,grp in enumerate(self.groups):
            conds=[]
            for blk in grp["blocks"]:
                f=blk["fld"].currentData(); op=blk["op"].currentText()
                d1=self.get_val(blk["in1"]); v1=self._resolve_value_map(blk["in1"],d1)
                d2=self.get_val(blk["in2"]); v2=self._resolve_value_map(blk["in2"],d2)
                if op=="ist leer":
                    conds.append(f'("{f}" IS NULL OR "{f}" = \'{{}}\')')
                elif op=="ist nicht leer":
                    conds.append(f'("{f}" IS NOT NULL AND "{f}" != \'{{}}\')')
                elif op=="enthält":
                    conds.append(f'"{f}" ILIKE \'%{v1}%\'')
                elif op=="zwischen":
                    conds.append(f'"{f}" >= \'{v1}\' AND "{f}" <= \'{v2}\'')
                elif v1:
                    if v1.replace(".","",1).isdigit():
                        conds.append(f'"{f}" {op} {v1}')
                    else:
                        conds.append(f'"{f}" {op} \'{v1}\'')
            expr="(" + " AND ".join(conds) + ")"
            if i==0:
                parts.append(expr)
            else:
                conj=" AND " if grp["op"].currentText()=="UND" else " OR "
                parts.append(conj+expr)
        self.preview.setText("".join(parts))


    def apply_filter(self):
        expr=self.preview.toPlainText()
        if expr:
            self.layer.removeSelection()
            self.layer.selectByExpression(expr, QgsVectorLayer.SetSelection)


    def copy_expression(self):
        txt=self.preview.toPlainText()
        if txt:
            QGuiApplication.clipboard().setText(txt)


    def save_filter(self):
        path,_ = QFileDialog.getSaveFileName(self,"Filter speichern","","JSON Files (*.json*)")
        if not path:
            return
        data = {"version":"v0.4.3","groups":[]}
        for grp in self.groups:
            gd = {"op":grp["op"].currentText(),"blocks":[]}
            for blk in grp["blocks"]:
                bd = {
                    "field":blk["fld"].currentData(),
                    "operator":blk["op"].currentText(),
                    "value1":self.get_val(blk["in1"]),
                    "value2":self.get_val(blk["in2"])
                }
                gd["blocks"].append(bd)
            data["groups"].append(gd)
        try:
            with open(path,"w",encoding="utf-8") as f:
                json.dump(data,f,ensure_ascii=False,indent=2)
        except Exception as e:
            QMessageBox.critical(self,"Fehler",f"Speichern fehlgeschlagen:\n{e}")


    def load_filter(self):
        path,_ = QFileDialog.getOpenFileName(self,"Filter laden","","JSON Files (*.json*)")
        if not path:
            return
        try:
            data = json.load(open(path,"r",encoding="utf-8"))
        except Exception as e:
            QMessageBox.critical(self,"Fehler",f"Laden fehlgeschlagen:\n{e}")
            return

        # Alle Gruppen außer der ersten entfernen
        for grp in list(self.groups)[1:]:
            self.remove_group(grp)
        # Erste Gruppe zurücksetzen
        first = self.groups[0]
        for blk in list(first["blocks"]):
            w = blk["container"]
            first["conds"].removeWidget(w)
            w.deleteLater()
            first["blocks"].remove(blk)

        # Neu laden
        for i,gd in enumerate(data.get("groups",[])):
            if i > 0:
                self.add_group()
            grp = self.groups[i]
            grp["op"].setCurrentText(gd.get("op","UND"))
            for bd in gd.get("blocks",[]):
                self.add_condition(grp)
                blk = grp["blocks"][-1]
                blk["fld"].setCurrentIndex(blk["fld"].findData(bd.get("field","")))
                blk["op"].setCurrentText(bd.get("operator","="))
                if hasattr(blk["in1"], "setDate"):
                    try:
                        d = QDate.fromString(bd.get("value1",""), "yyyy-MM-dd")
                        blk["in1"].setDate(d)
                    except:
                        blk["in1"].setDate(QDate.currentDate())
                    try:
                        d2 = QDate.fromString(bd.get("value2",""), "yyyy-MM-dd")
                        blk["in2"].setDate(d2)
                    except:
                        blk["in2"].setDate(QDate.currentDate())
                else:
                    blk["in1"].setText(bd.get("value1",""))
                    blk["in2"].setText(bd.get("value2",""))

        self.generate_expression()
        self.update_warning()


    def update_warning(self):
        show = len(self.groups) > 1 and all(
            g["op"].currentText() == "UND" for g in self.groups[1:]
        )
        self.warn.setVisible(show)


    def load_field_values(self, mode, field_name, le):
        """
        Popup mit allen / 10 Stichproben / nur verwendeten Werten.
        Berücksichtigt jetzt auch QGIS-Mehrfachwert-Strings "{a,b}".
        """
        vm = getattr(le, "_value_map", None)
        if vm is not None:
            keys = list(vm.keys())

            if mode == "10 Stichproben":
                keys = random.sample(keys, min(10, len(keys)))

            elif mode == "Nur verwendete Werte":
                used = set()
                for feat in self.layer.getFeatures(QgsFeatureRequest()):
                    val = feat[field_name]
                    if not val:
                        continue
                    if isinstance(val, (list, tuple)):
                        for k in val:
                            used.add(k)
                    elif isinstance(val, str) and val.startswith("{") and val.endswith("}"):
                        inner = val[1:-1]
                        for part in inner.split(","):
                            used.add(part.strip().strip("'").strip('"'))
                    else:
                        used.add(val)
                keys = [k for k in keys if k in used]

            choices = [f"{vm[k]} ({k})" for k in keys]

        else:
            distinct = set()
            for feat in self.layer.getFeatures(QgsFeatureRequest()):
                val = feat[field_name]
                if not val:
                    continue
                if isinstance(val, (list, tuple)):
                    for v in val:
                        distinct.add(v)
                elif isinstance(val, str) and val.startswith("{") and val.endswith("}"):
                    inner = val[1:-1]
                    for part in inner.split(","):
                        distinct.add(part.strip().strip("'").strip('"'))
                else:
                    distinct.add(val)

            if mode == "10 Stichproben":
                distinct = set(random.sample(list(distinct), min(10, len(distinct))))
            choices = sorted(str(v) for v in distinct)

        comp = QCompleter(choices, self)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setCompletionMode(QCompleter.PopupCompletion)
        comp.activated[str].connect(lambda txt, le=le: le.setText(txt))
        le.setCompleter(comp)
        le.setFocus()
        comp.complete()
