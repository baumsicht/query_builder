# QueryBuilder

> **Version:** 0.1.0  
> **QGIS:** ≥ 3.22  
> **Author:** Treesta  
> **License:** GNU General Public License v3.0 (GPL-3.0)  

---

## 🇩🇪 Deutsch

### 📖 Beschreibung
**QueryBuilder** ist ein QGIS-Plugin, das es Anwender:innen ermöglicht, komplexe Layer-Filter grafisch zu erstellen. Anstatt SQL-Ausdrücke von Hand zu schreiben, wählen Sie einfach:

- **Felder** anhand ihres Alias oder Namens  
- **Operatoren** (z. B. „=“, „zwischen“, „enthält“, „ist leer“)  
- **Werte** über Textfelder, Datumspicker oder Autocomplete  
- **Gruppen** mit UND/ODER-Verknüpfung  

Und bauen so in wenigen Klicks beliebig verschachtelte Filter-Statements.

### 🌟 Hauptfunktionen
- **Layer-Auswahl**: Dropdown aller Vektor-Layer im Projekt, Standard = aktiver Layer  
- **Bedingungen**: Je Feld eine Zeile mit Feld-Alias, Operator und Eingabe  
- **Datumsfelder**: Automatische Erkennung & Kalender-Widget  
- **Mehrfachwerte**: „zwischen“ zeigt zwei Eingaben, „ist leer/nicht leer“ ohne Wert  
- **Autocomplete**: Ermittlung aller vorhandenen Attribut-Werte für Textfelder  
- **Gruppen**: +Gruppe hinzufügen, Duplizieren 🗐, Löschen 🗑️, Verknüpfung UND/ODER  
- **Zeile löschen**: ❌-Button auf jeder Bedingung  
- **Ausdruck erzeugen**: Generiert gültigen QGIS-SQL-Ausdruck  
- **Kopieren**: 📋 Kopiert den fertigen Ausdruck in die Zwischenablage  
- **Filter anwenden**: Setzt das SubsetString des Layers  
- **Speichern/Laden**: Filter-Definition als JSON exportieren/importieren  

### 🔧 Installation
1. ZIP-Archiv in **Plugins > Plugin verwalten und installieren > Installieren von ZIP** hochladen  
2. QGIS neu starten  
3. **Plugins > QueryBuilder** öffnen  

### 📝 Nutzung
1. **Layer** wählen (oben)  
2. Mit **+ Bedingung hinzufügen** Felder, Operator und Wert definieren  
3. Bei Bedarf **+ Gruppe hinzufügen** und Verknüpfung festlegen  
4. **Ausdruck erzeugen** klicken  
5. Ausdruck per **📋 Kopieren** in Zwischenablage übernehmen  
6. Mit **Filter anwenden** auf den Layer übertragen  
7. Optional: Filter mit **💾 Filter speichern** sichern oder mit **📂 Filter laden** wiederherstellen  

---

## EN English

### 📖 Description  
**QueryBuilder** is a QGIS plugin that lets users build complex layer filters visually instead of writing SQL by hand. Simply choose:

- **Fields** by alias or name  
- **Operators** (e.g. “=”, “between”, “contains”, “is null”)  
- **Values** via text input, date pickers or autocomplete  
- **Groups** with AND/OR logical connectors  

in a flexible, nested way.

### 🌟 Key Features  
- **Layer selection**: Dropdown of all vector layers in the project (defaults to active layer)  
- **Conditions**: One row per condition with field, operator, and value widget  
- **Date support**: Automatic detection of date fields & calendar popup  
- **Range & null tests**: “between” shows two inputs; “is empty”/“is not empty” need no value  
- **Autocomplete**: Collects existing attribute values for text entry  
- **Groups**: Add group, duplicate 🗐, delete 🗑️, choose AND/OR connector  
- **Delete row**: ❌ button on each condition  
- **Generate expression**: Builds a valid QGIS SQL filter string  
- **Copy**: 📋 copies the filter to clipboard  
- **Apply filter**: Sets the layer’s subsetString  
- **Save/Load**: Export/import filter definitions as JSON  

### 🔧 Installation  
1. In QGIS, go to **Plugins > Manage and Install Plugins > Install from ZIP**  
2. Select the ZIP archive and install  
3. Restart QGIS  
4. Open **Plugins > QueryBuilder**

### 📝 Usage  
1. Select your **Layer** at top  
2. Click **+ Add condition** to define field, operator & value  
3. (Optional) Click **+ Add group** and set logical connector  
4. Click **Generate expression**  
5. Click **📋 Copy** to copy filter text  
6. Click **Apply filter** to activate the subset on the layer  
7. Optionally **Save filter** as JSON or **Load filter** back  

---

## 📜 License  
This plugin is released under the **GNU General Public License v3.0** (GPL-3.0). See `LICENSE` file for details.  
