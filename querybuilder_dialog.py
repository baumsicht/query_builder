from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTextEdit, QLineEdit, QWidget, QDateEdit, QFrame
)
from qgis.PyQt.QtCore import Qt, QDate, QVariant
from qgis.core import QgsField


class QueryBuilderDialog(QDialog):
    def __init__(self, layer):
        super().__init__()
        self.layer = layer
        self.setWindowTitle("QueryBuilder  –  v1.4.2")
        self.setMinimumWidth(600)

        # Main Layout
        self.layout = QVBoxLayout(self)
        self.groups_container = QVBoxLayout()
        self.layout.addLayout(self.groups_container)

        # Button: Gruppe hinzufügen
        btn_add_group = QPushButton("+ Gruppe hinzufügen")
        btn_add_group.clicked.connect(self.add_group)
        self.layout.addWidget(btn_add_group)

        # Ausdrucksvorschau
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.layout.addWidget(QLabel("Erzeugter Ausdruck:"))
        self.layout.addWidget(self.preview)

        # Generate / Apply Buttons
        btns = QHBoxLayout()
        btn_generate = QPushButton("Ausdruck erzeugen")
        btn_generate.clicked.connect(self.generate_expression)
        btn_apply = QPushButton("Filter anwenden")
        btn_apply.clicked.connect(self.apply_filter)
        btns.addWidget(btn_generate)
        btns.addWidget(btn_apply)
        self.layout.addLayout(btns)

        # Groups storage
        self.groups = []
        self.add_group()

    def create_input_widget(self, is_date):
        """Return QDateEdit if date, else QLineEdit."""
        if is_date:
            dt = QDateEdit()
            dt.setCalendarPopup(True)
            dt.setDisplayFormat("yyyy-MM-dd")
            dt.setDate(QDate.currentDate())
            return dt
        return QLineEdit()

    def is_date_field(self, field_name):
        """Detect date/datetime fields via typeName."""
        for f in self.layer.fields():
            if f.name() == field_name:
                t = f.typeName().lower()
                return "date" in t
        return False

    def friendly_alias(self, f: QgsField):
        """Use layer.alias if set, otherwise prettify field.name."""
        idx = self.layer.fields().indexOf(f.name())
        alias = self.layer.attributeAlias(idx)
        if alias:
            return alias
        # fallback: replace underscores, title-case
        return f.name().replace("_", " ").title()

    def add_group(self):
        grp = {}
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        vbox = QVBoxLayout(frame)
        self.groups_container.addWidget(frame)

        # Header: UND/ODER, Duplizieren, Löschen
        hl_top = QHBoxLayout()
        op = QComboBox()
        op.addItems(["UND", "ODER"])
        if not self.groups:
            op.setCurrentText("UND")
            op.setDisabled(True)
        btn_dup = QPushButton("🗐")
        btn_del = QPushButton("🗑️")
        hl_top.addWidget(QLabel("Verknüpfung:"))
        hl_top.addWidget(op)
        hl_top.addStretch()
        hl_top.addWidget(btn_dup)
        hl_top.addWidget(btn_del)
        vbox.addLayout(hl_top)

        # Conditions container
        cond_box = QVBoxLayout()
        vbox.addLayout(cond_box)

        # Button: add condition
        btn_add = QPushButton("  + Bedingung hinzufügen")
        vbox.addWidget(btn_add)

        grp.update({
            "frame": frame,
            "op": op,
            "conds": cond_box,
            "dup": btn_dup,
            "del": btn_del,
            "add": btn_add,
            "blocks": []
        })
        self.groups.append(grp)

        btn_add.clicked.connect(lambda _, g=grp: self.add_condition(g))
        btn_dup.clicked.connect(lambda _, g=grp: self.duplicate_group(g))
        btn_del.clicked.connect(lambda _, g=grp: self.remove_group(g))

        # first condition
        self.add_condition(grp)

    def add_condition(self, group):
        blk = {}
        hl = QHBoxLayout()

        # Field combo with friendly alias
        fld = QComboBox()
        for f in self.layer.fields():
            label = f"{self.friendly_alias(f)} ({f.name()})"
            fld.addItem(label, f.name())

        # Operator combo
        op = QComboBox()
        op.addItems(["=", "!=", ">", "<", ">=", "<=", "zwischen", "enthält", "ist leer", "ist nicht leer"])

        # Inputs (placeholders)
        inp1 = self.create_input_widget(False)
        inp2 = self.create_input_widget(False)
        inp2.hide()

        # assemble
        for w in (fld, op, inp1, inp2):
            hl.addWidget(w)
        container = QWidget()
        container.setLayout(hl)
        group["conds"].addWidget(container)

        blk.update({
            "fld": fld,
            "op": op,
            "in1": inp1,
            "in2": inp2,
            "layout": hl
        })
        group["blocks"].append(blk)

        def update():
            name = fld.currentData()
            is_date = self.is_date_field(name)
            operator = op.currentText()

            # remove old widgets
            for w in (blk["in1"], blk["in2"]):
                hl.removeWidget(w)
                w.deleteLater()

            # create new
            blk["in1"] = self.create_input_widget(is_date)
            blk["in2"] = self.create_input_widget(is_date)
            blk["in2"].setVisible(operator == "zwischen")

            # insert at correct pos
            hl.insertWidget(2, blk["in1"])
            hl.insertWidget(3, blk["in2"])

        fld.currentIndexChanged.connect(update)
        op.currentTextChanged.connect(update)
        update()

    def duplicate_group(self, group):
        # add new group and copy conditions
        self.add_group()
        new = self.groups[-1]
        old = group["blocks"]
        # remove initial
        w = new["conds"].takeAt(0).widget(); w.deleteLater()
        new["blocks"].clear()
        for ob in old:
            self.add_condition(new)
            nb = new["blocks"][-1]
            nb["fld"].setCurrentIndex(ob["fld"].currentIndex())
            nb["op"].setCurrentIndex(ob["op"].currentIndex())
            # transfer values
            v1 = ob["in1"].date().toString("yyyy-MM-dd") if hasattr(ob["in1"], "date") else ob["in1"].text()
            v2 = ob["in2"].date().toString("yyyy-MM-dd") if hasattr(ob["in2"], "date") else ob["in2"].text()
            nb["in1"].setText(v1)
            nb["in2"].setText(v2)

    def remove_group(self, group):
        if len(self.groups) <= 1:
            return
        idx = self.groups.index(group)
        group["frame"].deleteLater()
        self.groups.pop(idx)
        if idx == 0:
            self.groups[0]["op"].setDisabled(True)

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
                op = blk["op"].currentText()
                v1 = self.get_val(blk["in1"])
                v2 = self.get_val(blk["in2"])
                if op == "ist leer":
                    conds.append(f'("{f}" IS NULL OR "{f}" = \'{{}}\')')
                elif op == "ist nicht leer":
                    conds.append(f'("{f}" IS NOT NULL AND "{f}" != \'{{}}\')')
                elif op == "enthält":
                    conds.append(f'"{f}" ILIKE \'%{v1}%\'')
                elif op == "zwischen":
                    conds.append(f'"{f}" >= \'{v1}\' AND "{f}" <= \'{v2}\'')
                elif v1:
                    if v1.replace(".", "", 1).isdigit():
                        conds.append(f'"{f}" {op} {v1}')
                    else:
                        conds.append(f'"{f}" {op} \'{v1}\'')
            grp_expr = "(" + " AND ".join(conds) + ")"
            if i == 0:
                parts.append(grp_expr)
            else:
                conj = " AND " if grp["op"].currentText()=="UND" else " OR "
                parts.append(conj + grp_expr)
        self.preview.setText("".join(parts))

    def apply_filter(self):
        expr = self.preview.toPlainText()
        if expr:
            self.layer.setSubsetString(expr)
