from __future__ import annotations

import json
import shutil
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

APP_TITLE = "AIM Lab Admin"


class ArrayEditDialog(QDialog):
    def __init__(self, parent: QWidget | None, title: str, values: list[str]):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(520, 420)

        self.editor = QPlainTextEdit(self)
        self.editor.setPlainText("\n".join(values))

        hint = QLabel("한 줄에 하나씩 입력하세요. 빈 줄은 저장 시 제거됩니다.")
        hint.setWordWrap(True)

        btn_ok = QPushButton("적용")
        btn_cancel = QPushButton("취소")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)

        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(self.editor, 1)
        layout.addLayout(btn_row)

    def values(self) -> list[str]:
        return [line.strip() for line in self.editor.toPlainText().splitlines() if line.strip()]


class ReorderableListWidget(QListWidget):
    orderChanged = Signal()

    def dropEvent(self, event):
        super().dropEvent(event)
        self.orderChanged.emit()


class ImageFieldWidget(QWidget):
    fileDropped = Signal(str)

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._info: dict[str, Any] | None = None
        self.current_image_path: Path | None = None
        self.setAcceptDrops(True)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 700;")

        self.preview = QLabel("No image")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(140, 120)
        self.preview.setMaximumSize(220, 180)
        self.preview.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.preview.setAcceptDrops(False)
        self.preview.setStyleSheet(
            "border: 1px dashed #94a3b8; border-radius: 10px; "
            "background: #f8fafc; color: #64748b; padding: 6px;"
        )

        self.drop_hint = QLabel("이미지를 여기로 끌어다 놓을 수 있습니다.")
        self.drop_hint.setStyleSheet("color: #6b7280;")

        self.path_label = QLabel("")
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("color: #6b7280;")

        self.upload_btn = QPushButton("이미지 업로드 / 교체")
        self.refresh_btn = QPushButton("미리보기 새로고침")

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.upload_btn)
        btn_row.addWidget(self.refresh_btn)
        btn_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(title_label)
        layout.addWidget(self.preview, 0, Qt.AlignLeft)
        layout.addWidget(self.drop_hint)
        layout.addLayout(btn_row)
        layout.addWidget(self.path_label)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        mime = event.mimeData()
        if mime.hasUrls():
            urls = mime.urls()
            if urls:
                local = urls[0].toLocalFile()
                ext = Path(local).suffix.lower()
                if ext in {".jpg", ".jpeg", ".png", ".gif"}:
                    event.acceptProposedAction()
                    self.preview.setStyleSheet(
                        "border: 2px dashed #2563eb; border-radius: 10px; "
                        "background: #eff6ff; color: #1d4ed8; padding: 6px;"
                    )
                    return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self.preview.setStyleSheet(
            "border: 1px dashed #94a3b8; border-radius: 10px; "
            "background: #f8fafc; color: #64748b; padding: 6px;"
        )
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self.preview.setStyleSheet(
            "border: 1px dashed #94a3b8; border-radius: 10px; "
            "background: #f8fafc; color: #64748b; padding: 6px;"
        )
        mime = event.mimeData()
        if mime.hasUrls():
            urls = mime.urls()
            if urls:
                local = urls[0].toLocalFile()
                if local:
                    self.fileDropped.emit(local)
                    event.acceptProposedAction()
                    return
        event.ignore()

    def set_people_aspect(self, enabled: bool) -> None:
        if enabled:
            self.preview.setMinimumSize(130, 170)
            self.preview.setMaximumSize(180, 240)
            self.preview.resize(180, 240)
        else:
            self.preview.setMinimumSize(140, 120)
            self.preview.setMaximumSize(220, 180)
            self.preview.resize(220, 180)

    def set_info(self, info: dict[str, Any] | None) -> None:
        self._info = info
        self.current_image_path = None
        if not info or not str(info.get("base_name", "")).strip():
            self.preview.setPixmap(QPixmap())
            self.preview.setText("파일명 생성에 필요한 값을 먼저 입력하세요")
            self.path_label.setText("")
            return

        expected = " / ".join(info.get("candidates", []))
        self.path_label.setText(f"Expected file names: {expected}")

    def set_preview_from_path(self, path: Path | None) -> None:
        self.current_image_path = path
        if path and path.exists():
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                target_size = self.preview.maximumSize()
                scaled = pixmap.scaled(
                    target_size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.preview.setPixmap(scaled)
                self.preview.setText("")
                return

        self.preview.setPixmap(QPixmap())
        self.preview.setText("No image found")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.current_image_path and self.current_image_path.exists():
            self.set_preview_from_path(self.current_image_path)


class DatasetConfig:
    def __init__(self, label: str, filename: str):
        self.label = label
        self.filename = filename

    def create_empty(self) -> dict[str, Any]:
        raise NotImplementedError

    def get_label(self, item: dict[str, Any]) -> str:
        raise NotImplementedError

    def get_sub_label(self, item: dict[str, Any]) -> str:
        return ""

    def build_editor(self, app: "AimLabAdmin", item: dict[str, Any]) -> QWidget:
        raise NotImplementedError

    def image_info(self, item: dict[str, Any], root_dir: Path) -> dict[str, Any] | None:
        return None


class PublicationsConfig(DatasetConfig):
    def __init__(self):
        super().__init__("Publications", "publications.json")

    def create_empty(self) -> dict[str, Any]:
        from datetime import datetime

        return {
            "title": "",
            "authors": [],
            "journal": "",
            "year": datetime.now().year,
            "volume": "",
            "issue": "",
            "pages": "",
            "featured": False,
            "doi": "",
            "lab_member": [],
            "first_author": [],
            "corresponding_author": [],
        }

    def get_label(self, item: dict[str, Any]) -> str:
        return item.get("title") or "(Untitled publication)"

    def get_sub_label(self, item: dict[str, Any]) -> str:
        parts = [item.get("journal"), str(item.get("year") or "").strip()]
        return " · ".join([p for p in parts if p])

    def build_editor(self, app: "AimLabAdmin", item: dict[str, Any]) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        fields: dict[str, Any] = {}
        fields["title"] = QLineEdit(item.get("title", ""))
        fields["authors_csv"] = QLineEdit(", ".join(item.get("authors", [])))
        fields["journal"] = QLineEdit(item.get("journal", ""))
        fields["year"] = QLineEdit(str(item.get("year", "")))
        fields["volume"] = QLineEdit(item.get("volume", ""))
        fields["issue"] = QLineEdit(item.get("issue", ""))
        fields["pages"] = QLineEdit(item.get("pages", ""))
        fields["doi"] = QLineEdit(item.get("doi", ""))
        fields["featured"] = QCheckBox("featured")
        fields["featured"].setChecked(bool(item.get("featured", False)))

        fields["author_roles"] = {
            "lab_member": list(item.get("lab_member", [])),
            "first_author": list(item.get("first_author", [])),
            "corresponding_author": list(item.get("corresponding_author", [])),
        }

        fields["author_roles_widget"] = app.make_publication_author_roles_widget(fields)

        authors_hint = QLabel("저자 이름을 comma로 구분해서 입력하세요. 아래 체크박스에서 역할을 지정할 수 있습니다.")
        authors_hint.setWordWrap(True)
        authors_hint.setStyleSheet("color: #6b7280;")

        layout.addRow("Title", fields["title"])
        layout.addRow("Authors", fields["authors_csv"])
        layout.addRow("", authors_hint)
        layout.addRow("Author Roles", fields["author_roles_widget"])
        layout.addRow("Journal", fields["journal"])
        layout.addRow("Year", fields["year"])
        layout.addRow("Volume", fields["volume"])
        layout.addRow("Issue", fields["issue"])
        layout.addRow("Pages", fields["pages"])
        layout.addRow("DOI URL", fields["doi"])
        layout.addRow("Featured", fields["featured"])

        app.bind_form(fields)
        app.refresh_publication_author_roles(fields)
        return w


class PeopleConfig(DatasetConfig):
    def __init__(self):
        super().__init__("People", "people.json")

    def create_empty(self) -> dict[str, Any]:
        return {
            "given_name": "",
            "family_name": "",
            "name_kr": "",
            "birth": "",
            "category": "current",
            "role": "",
            "role_kr": "",
            "degree": "",
            "degree_kr": "",
            "program": "",
            "program_kr": "",
            "current_position": "",
            "current_position_kr": "",
            "email": "",
            "phone": "",
            "website": "",
            "scholar": "",
            "educational_background": [],
            "educational_background_kr": [],
            "professional_experience": [],
            "professional_experience_kr": [],
            "awards": [],
            "awards_kr": [],
            "research_interests": [],
            "research_interests_kr": [],
        }

    def get_label(self, item: dict[str, Any]) -> str:
        name = " ".join([p for p in [item.get("given_name", ""), item.get("family_name", "")] if p])
        return name or "(Unnamed person)"

    def get_sub_label(self, item: dict[str, Any]) -> str:
        return " · ".join([p for p in [item.get("category", ""), item.get("role", "")] if p])

    def image_info(self, item: dict[str, Any], root_dir: Path) -> dict[str, Any] | None:
        base_name = f"{item.get('given_name', '')}_{item.get('family_name', '')}_{item.get('birth', '')}".strip()
        folder = root_dir / "photo"
        return {
            "folder": folder,
            "base_name": base_name,
            "candidates": [f"photo/{base_name}.jpg", f"photo/{base_name}.png"],
            "extensions": ["jpg", "png"],
            "aspect": "people",
        }

    def build_editor(self, app: "AimLabAdmin", item: dict[str, Any]) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        fields: dict[str, Any] = {}
        simple_keys = [
            ("Given Name", "given_name"),
            ("Family Name", "family_name"),
            ("Korean Name", "name_kr"),
            ("Birth (YYYYMMDD)", "birth"),
            ("Role (EN)", "role"),
            ("Role (KR)", "role_kr"),
            ("Degree (EN)", "degree"),
            ("Degree (KR)", "degree_kr"),
            ("Program (EN)", "program"),
            ("Program (KR)", "program_kr"),
            ("Current Position (EN)", "current_position"),
            ("Current Position (KR)", "current_position_kr"),
            ("Email", "email"),
            ("Phone", "phone"),
            ("Website", "website"),
            ("Scholar", "scholar"),
        ]
        for label, key in simple_keys:
            fields[key] = QLineEdit(item.get(key, ""))
            layout.addRow(label, fields[key])

        fields["category"] = QComboBox()
        fields["category"].addItems(["pi", "current", "alumni"])
        idx = fields["category"].findText(item.get("category", "current"))
        if idx >= 0:
            fields["category"].setCurrentIndex(idx)
        layout.insertRow(4, "Category", fields["category"])

        layout.addRow(
            "Educational Background (EN)",
            app.make_array_button("educational_background", item.get("educational_background", []), fields),
        )
        layout.addRow(
            "Educational Background (KR)",
            app.make_array_button("educational_background_kr", item.get("educational_background_kr", []), fields),
        )
        layout.addRow(
            "Professional Experience (EN)",
            app.make_array_button("professional_experience", item.get("professional_experience", []), fields),
        )
        layout.addRow(
            "Professional Experience (KR)",
            app.make_array_button("professional_experience_kr", item.get("professional_experience_kr", []), fields),
        )
        layout.addRow("Awards (EN)", app.make_array_button("awards", item.get("awards", []), fields))
        layout.addRow("Awards (KR)", app.make_array_button("awards_kr", item.get("awards_kr", []), fields))
        layout.addRow(
            "Research Interests (EN)",
            app.make_array_button("research_interests", item.get("research_interests", []), fields),
        )
        layout.addRow(
            "Research Interests (KR)",
            app.make_array_button("research_interests_kr", item.get("research_interests_kr", []), fields),
        )

        image_widget = app.make_image_widget(item)
        layout.addRow(image_widget)

        app.bind_form(fields)
        return w


class ResearchConfig(DatasetConfig):
    def __init__(self):
        super().__init__("Research", "research.json")

    def create_empty(self) -> dict[str, Any]:
        return {
            "theme": "",
            "theme_kr": "",
            "subtitle": "",
            "subtitle_kr": "",
            "description": "",
            "description_kr": "",
            "keywords": [],
            "keywords_kr": [],
            "methods": [],
            "methods_kr": [],
            "topics": [],
            "topics_kr": [],
        }

    def get_label(self, item: dict[str, Any]) -> str:
        return item.get("theme") or "(Untitled theme)"

    def get_sub_label(self, item: dict[str, Any]) -> str:
        return item.get("subtitle") or ""

    def image_info(self, item: dict[str, Any], root_dir: Path) -> dict[str, Any] | None:
        base_name = str(item.get("theme", ""))
        folder = root_dir / "research_image"
        return {
            "folder": folder,
            "base_name": base_name,
            "candidates": [
                f"research_image/{base_name}.jpg",
                f"research_image/{base_name}.png",
                f"research_image/{base_name}.gif",
            ],
            "extensions": ["jpg", "png", "gif"],
            "aspect": "wide",
        }

    def build_editor(self, app: "AimLabAdmin", item: dict[str, Any]) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        fields: dict[str, Any] = {}
        fields["theme"] = QLineEdit(item.get("theme", ""))
        fields["theme_kr"] = QLineEdit(item.get("theme_kr", ""))
        fields["subtitle"] = QLineEdit(item.get("subtitle", ""))
        fields["subtitle_kr"] = QLineEdit(item.get("subtitle_kr", ""))
        fields["description"] = QTextEdit(item.get("description", ""))
        fields["description"].setMinimumHeight(100)
        fields["description_kr"] = QTextEdit(item.get("description_kr", ""))
        fields["description_kr"].setMinimumHeight(100)

        layout.addRow("Theme (EN)", fields["theme"])
        layout.addRow("Theme (KR)", fields["theme_kr"])
        layout.addRow("Subtitle (EN)", fields["subtitle"])
        layout.addRow("Subtitle (KR)", fields["subtitle_kr"])
        layout.addRow("Description (EN)", fields["description"])
        layout.addRow("Description (KR)", fields["description_kr"])
        layout.addRow("Keywords (EN)", app.make_array_button("keywords", item.get("keywords", []), fields))
        layout.addRow("Keywords (KR)", app.make_array_button("keywords_kr", item.get("keywords_kr", []), fields))
        layout.addRow("Methods (EN)", app.make_array_button("methods", item.get("methods", []), fields))
        layout.addRow("Methods (KR)", app.make_array_button("methods_kr", item.get("methods_kr", []), fields))
        layout.addRow("Topics (EN)", app.make_array_button("topics", item.get("topics", []), fields))
        layout.addRow("Topics (KR)", app.make_array_button("topics_kr", item.get("topics_kr", []), fields))
        layout.addRow(app.make_image_widget(item))

        app.bind_form(fields)
        return w


class NewsConfig(DatasetConfig):
    def __init__(self):
        super().__init__("News", "news.json")

    def create_empty(self) -> dict[str, Any]:
        return {
            "date": "",
            "title": "",
            "summary": "",
            "link": "",
        }

    def get_label(self, item: dict[str, Any]) -> str:
        return item.get("title") or "(Untitled news)"

    def get_sub_label(self, item: dict[str, Any]) -> str:
        return item.get("date") or ""

    def image_info(self, item: dict[str, Any], root_dir: Path) -> dict[str, Any] | None:
        base_name = str(item.get("title", ""))
        folder = root_dir / "news_image"
        return {
            "folder": folder,
            "base_name": base_name,
            "candidates": [f"news_image/{base_name}.jpg", f"news_image/{base_name}.png"],
            "extensions": ["jpg", "png"],
            "aspect": "wide",
        }

    def build_editor(self, app: "AimLabAdmin", item: dict[str, Any]) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        fields: dict[str, Any] = {}
        fields["date"] = QLineEdit(item.get("date", ""))
        fields["title"] = QLineEdit(item.get("title", ""))
        fields["summary"] = QTextEdit(item.get("summary", ""))
        fields["summary"].setMinimumHeight(100)
        fields["link"] = QLineEdit(item.get("link", ""))

        layout.addRow("Date (YYYY-MM-DD)", fields["date"])
        layout.addRow("Title", fields["title"])
        layout.addRow("Summary", fields["summary"])
        layout.addRow("External Link", fields["link"])
        layout.addRow(app.make_image_widget(item))

        app.bind_form(fields)
        return w


class AimLabAdmin(QMainWindow):
    def __init__(self, root_dir: Path):
        super().__init__()
        self.root_dir = root_dir.resolve()
        self.data_dir = self.root_dir / "data"
        self.dataset_configs: dict[str, DatasetConfig] = {
            "publications": PublicationsConfig(),
            "people": PeopleConfig(),
            "research": ResearchConfig(),
            "news": NewsConfig(),
        }
        self.dataset_data: dict[str, list[dict[str, Any]]] = {k: [] for k in self.dataset_configs}
        self.current_key = "publications"
        self.selected_index: int | None = None
        self.dirty = False
        self.form_fields: dict[str, Any] = {}
        self.image_widget: ImageFieldWidget | None = None

        self.setWindowTitle(APP_TITLE)
        self.resize(1380, 900)
        self._build_ui()
        self._load_all()
        self._render_all()

    def _build_ui(self) -> None:
        self.statusBar().showMessage("Ready")

        save_action = QAction("Save JSON", self)
        save_action.triggered.connect(self.save_current_dataset)
        self.menuBar().addAction(save_action)

        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)

        header = QGroupBox(APP_TITLE)
        header_layout = QVBoxLayout(header)
        desc = QLabel(
            "앱이 위치한 디렉토리를 사이트 루트로 간주합니다. "
            "data/, photo/, research_image/, news_image/를 자동으로 사용합니다."
        )
        desc.setWordWrap(True)
        header_layout.addWidget(desc)
        root_layout.addWidget(header)

        toolbar = QHBoxLayout()
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.tabBarClicked.connect(self._on_tab_changed)
        for _, cfg in self.dataset_configs.items():
            self.tabs.addTab(QWidget(), cfg.label)
        toolbar.addWidget(self.tabs, 1)

        self.reload_btn = QPushButton("Reload file")
        self.add_btn = QPushButton("Add item")
        self.move_up_btn = QPushButton("Move up")
        self.move_down_btn = QPushButton("Move down")
        self.apply_btn = QPushButton("Apply changes")
        self.delete_btn = QPushButton("Delete item")
        self.save_btn = QPushButton("Save JSON to disk")

        self.reload_btn.clicked.connect(self.reload_current_dataset)
        self.add_btn.clicked.connect(self.add_item)
        self.move_up_btn.clicked.connect(lambda: self.move_selected_item(-1))
        self.move_down_btn.clicked.connect(lambda: self.move_selected_item(1))
        self.apply_btn.clicked.connect(self.apply_changes)
        self.delete_btn.clicked.connect(self.delete_item)
        self.save_btn.clicked.connect(self.save_current_dataset)

        for btn in [
            self.reload_btn,
            self.add_btn,
            self.move_up_btn,
            self.move_down_btn,
            self.apply_btn,
            self.delete_btn,
            self.save_btn,
        ]:
            toolbar.addWidget(btn)

        root_layout.addLayout(toolbar)

        splitter = QSplitter()
        root_layout.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Items"))

        self.item_list = ReorderableListWidget()
        self.item_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.item_list.setDefaultDropAction(Qt.MoveAction)
        self.item_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.item_list.currentRowChanged.connect(self._on_item_selected)
        self.item_list.orderChanged.connect(self.sync_order_from_list_widget)
        left_layout.addWidget(self.item_list, 1)

        right = QWidget()
        right_layout = QVBoxLayout(right)

        editor_label = QLabel("Editor")
        editor_label.setStyleSheet("font-weight: 700; font-size: 16px;")
        right_layout.addWidget(editor_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.form_host = QWidget()
        self.form_layout = QVBoxLayout(self.form_host)
        self.form_layout.setContentsMargins(8, 8, 8, 8)
        self.scroll.setWidget(self.form_host)
        right_layout.addWidget(self.scroll, 3)

        right_layout.addWidget(QLabel("JSON Preview"))
        self.json_preview = QPlainTextEdit()
        self.json_preview.setReadOnly(True)
        self.json_preview.setMinimumHeight(260)
        self.json_preview.setStyleSheet(
            "background: #0f172a; color: #e2e8f0; border-radius: 10px; "
            "font-family: Consolas, monospace;"
        )
        right_layout.addWidget(self.json_preview, 2)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([360, 980])

    def current_config(self) -> DatasetConfig:
        return self.dataset_configs[self.current_key]

    def current_data(self) -> list[dict[str, Any]]:
        return self.dataset_data[self.current_key]

    def _dataset_file(self, key: str) -> Path:
        return self.data_dir / self.dataset_configs[key].filename

    def _ensure_structure(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.root_dir / "photo").mkdir(exist_ok=True)
        (self.root_dir / "research_image").mkdir(exist_ok=True)
        (self.root_dir / "news_image").mkdir(exist_ok=True)

        for key in self.dataset_configs:
            path = self._dataset_file(key)
            if not path.exists():
                path.write_text("[]\n", encoding="utf-8")

    def _load_all(self) -> None:
        self._ensure_structure()
        for key in self.dataset_configs:
            path = self._dataset_file(key)
            try:
                content = json.loads(path.read_text(encoding="utf-8"))
                self.dataset_data[key] = content if isinstance(content, list) else []
            except Exception as exc:
                self.dataset_data[key] = []
                self._warn(f"{path.name} 로드 실패: {exc}")
        self.selected_index = 0 if self.current_data() else None

    def _render_all(self) -> None:
        self._render_item_list()
        self._render_form()
        self._update_preview()
        self._update_status()

    def _update_status(self) -> None:
        file_name = self.current_config().filename
        dirty_mark = " *수정됨" if self.dirty else ""
        self.statusBar().showMessage(f"{self.root_dir}  |  {file_name}{dirty_mark}")

    def _render_item_list(self) -> None:
        self.item_list.blockSignals(True)
        self.item_list.clear()
        cfg = self.current_config()
        for item in self.current_data():
            text = cfg.get_label(item)
            sub = cfg.get_sub_label(item)
            label = text if not sub else f"{text}\n{sub}"
            self.item_list.addItem(QListWidgetItem(label))
        if self.current_data() and self.selected_index is not None:
            self.selected_index = max(0, min(self.selected_index, len(self.current_data()) - 1))
            self.item_list.setCurrentRow(self.selected_index)
        self.item_list.blockSignals(False)

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            child = layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()

    def _render_form(self) -> None:
        self._clear_layout(self.form_layout)
        self.form_fields = {}
        self.image_widget = None

        if self.selected_index is None or self.selected_index >= len(self.current_data()):
            self.form_layout.addWidget(QLabel("Select an item or add a new one."))
            self.form_layout.addStretch(1)
            return

        item = deepcopy(self.current_data()[self.selected_index])
        widget = self.current_config().build_editor(self, item)
        self.form_layout.addWidget(widget)
        self.form_layout.addStretch(1)
        self.refresh_image_preview()

    def _update_preview(self) -> None:
        preview_data = deepcopy(self.current_data())
        if self.selected_index is not None and self.form_fields and self.selected_index < len(preview_data):
            try:
                preview_data[self.selected_index] = self.collect_form_values()
            except Exception:
                pass
        self.json_preview.setPlainText(json.dumps(preview_data, ensure_ascii=False, indent=2))

    def _on_tab_changed(self, index: int) -> None:
        keys = list(self.dataset_configs.keys())
        new_key = keys[index]
        if new_key == self.current_key:
            return
        self.current_key = new_key
        self.selected_index = 0 if self.current_data() else None
        self._render_all()

    def _on_item_selected(self, row: int) -> None:
        self.selected_index = row if row >= 0 else None
        self._render_form()
        self._update_preview()

    def bind_form(self, fields: dict[str, Any]) -> None:
        self.form_fields = fields
        for key, widget in fields.items():
            if key in {"author_roles", "author_roles_widget"}:
                continue
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(self._on_form_changed)
            elif isinstance(widget, QTextEdit):
                widget.textChanged.connect(self._on_form_changed)
            elif isinstance(widget, QCheckBox):
                widget.checkStateChanged.connect(self._on_form_changed)
            elif isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self._on_form_changed)

        if "authors_csv" in fields and "author_roles_widget" in fields:
            fields["authors_csv"].textChanged.connect(lambda: self.refresh_publication_author_roles(fields))

    def make_publication_author_roles_widget(self, fields: dict[str, Any]) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        return wrapper

    def refresh_publication_author_roles(self, fields: dict[str, Any]) -> None:
        wrapper = fields.get("author_roles_widget")
        if wrapper is None:
            return

        layout = wrapper.layout()
        if layout is None:
            layout = QVBoxLayout(wrapper)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(6)

        while layout.count():
            child = layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()

        csv_widget = fields.get("authors_csv")
        author_roles = fields.get("author_roles", {})
        if not isinstance(csv_widget, QLineEdit) or not isinstance(author_roles, dict):
            return

        authors = [name.strip() for name in csv_widget.text().split(",") if name.strip()]
        fields["authors_list"] = authors

        for role_key in ["lab_member", "first_author", "corresponding_author"]:
            existing = author_roles.get(role_key, [])
            author_roles[role_key] = [name for name in existing if name in authors]

        if not authors:
            empty_label = QLabel("저자를 입력하면 여기에서 lab member / first author / corresponding author를 체크할 수 있습니다.")
            empty_label.setWordWrap(True)
            empty_label.setStyleSheet("color: #6b7280;")
            layout.addWidget(empty_label)
            return

        for author in authors:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)

            name_label = QLabel(author)
            name_label.setMinimumWidth(180)
            row_layout.addWidget(name_label)

            for role_key, role_label in [
                ("lab_member", "Lab Member"),
                ("first_author", "First Author"),
                ("corresponding_author", "Corresponding Author"),
            ]:
                checkbox = QCheckBox(role_label)
                checkbox.setChecked(author in author_roles.get(role_key, []))

                def on_state_changed(state: int, *, rk: str = role_key, name: str = author) -> None:
                    selected = set(author_roles.get(rk, []))
                    if state:
                        selected.add(name)
                    else:
                        selected.discard(name)
                    author_roles[rk] = [a for a in authors if a in selected]
                    self._on_form_changed()

                checkbox.checkStateChanged.connect(on_state_changed)
                row_layout.addWidget(checkbox)

            row_layout.addStretch(1)
            layout.addWidget(row_widget)

        layout.addStretch(1)

    def make_array_button(self, key: str, values: list[str], fields: dict[str, Any]) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)

        summary = QLabel(self._array_summary(values))
        summary.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        summary.setWordWrap(True)
        btn = QPushButton("Edit")

        fields[key] = list(values)

        def edit_array() -> None:
            dialog = ArrayEditDialog(self, key, fields.get(key, []))
            if dialog.exec():
                fields[key] = dialog.values()
                summary.setText(self._array_summary(fields[key]))
                self._on_form_changed()

        btn.clicked.connect(edit_array)
        row.addWidget(summary, 1)
        row.addWidget(btn)
        return w

    def _array_summary(self, values: list[str]) -> str:
        if not values:
            return "(empty)"
        if len(values) <= 3:
            return ", ".join(values)
        return ", ".join(values[:3]) + f" ... (+{len(values) - 3})"

    def make_image_widget(self, item: dict[str, Any]) -> QWidget:
        self.image_widget = ImageFieldWidget("Image")
        info = self.current_config().image_info(item, self.root_dir)
        self.image_widget.set_people_aspect(info is not None and info.get("aspect") == "people")
        self.image_widget.set_info(info)
        self.image_widget.upload_btn.clicked.connect(self.upload_current_image)
        self.image_widget.refresh_btn.clicked.connect(self.refresh_image_preview)
        self.image_widget.fileDropped.connect(self.upload_current_image_from_path)
        return self.image_widget

    def _on_form_changed(self) -> None:
        self._update_preview()
        if self.image_widget:
            self.refresh_image_preview()

    def collect_form_values(self) -> dict[str, Any]:
        if self.selected_index is None:
            return {}

        current_item = deepcopy(self.current_data()[self.selected_index])
        for key, widget in self.form_fields.items():
            if key in {"author_roles", "author_roles_widget", "authors_list"}:
                continue
            if isinstance(widget, QLineEdit):
                value = widget.text().strip()
                if key == "year":
                    current_item[key] = int(value) if value else ""
                elif key == "authors_csv":
                    current_item["authors"] = [name.strip() for name in value.split(",") if name.strip()]
                else:
                    current_item[key] = value
            elif isinstance(widget, QTextEdit):
                current_item[key] = widget.toPlainText().strip()
            elif isinstance(widget, QCheckBox):
                current_item[key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                current_item[key] = widget.currentText()
            elif isinstance(widget, list):
                current_item[key] = [v.strip() for v in widget if str(v).strip()]

        author_roles = self.form_fields.get("author_roles")
        authors = current_item.get("authors", [])
        if isinstance(author_roles, dict):
            for role_key in ["lab_member", "first_author", "corresponding_author"]:
                current_item[role_key] = [name for name in author_roles.get(role_key, []) if name in authors]
        return current_item

    def apply_changes(self) -> None:
        if self.selected_index is None:
            return
        self.current_data()[self.selected_index] = self.collect_form_values()
        self.dirty = True
        self._render_all()
        self.statusBar().showMessage("변경사항이 메모리에 반영되었습니다. Save JSON to disk를 누르면 파일에 저장됩니다.")

    def add_item(self) -> None:
        self.current_data().append(self.current_config().create_empty())
        self.selected_index = len(self.current_data()) - 1
        self.dirty = True
        self._render_all()

    def move_selected_item(self, direction: int) -> None:
        if self.selected_index is None:
            return
        data = self.current_data()
        new_index = self.selected_index + direction
        if new_index < 0 or new_index >= len(data):
            return
        data[self.selected_index], data[new_index] = data[new_index], data[self.selected_index]
        self.selected_index = new_index
        self.dirty = True
        self._render_all()

    def sync_order_from_list_widget(self) -> None:
        if self.item_list.count() != len(self.current_data()):
            return

        old_data = deepcopy(self.current_data())
        cfg = self.current_config()
        available: list[tuple[int, dict[str, Any]]] = list(enumerate(old_data))
        reordered: list[dict[str, Any]] = []

        for row in range(self.item_list.count()):
            item_text = self.item_list.item(row).text()
            first_line = item_text.split("\n", 1)[0]

            match_index = None
            for idx, item in available:
                if cfg.get_label(item) == first_line:
                    match_index = idx
                    reordered.append(item)
                    break

            if match_index is not None:
                available = [(idx, item) for idx, item in available if idx != match_index]

        if len(reordered) == len(old_data):
            self.dataset_data[self.current_key] = reordered
            self.selected_index = self.item_list.currentRow()
            self.dirty = True
            self._update_preview()
            self._update_status()

    def delete_item(self) -> None:
        if self.selected_index is None:
            return
        reply = QMessageBox.question(self, APP_TITLE, "이 항목을 삭제할까요?")
        if reply != QMessageBox.Yes:
            return
        del self.current_data()[self.selected_index]
        if not self.current_data():
            self.selected_index = None
        else:
            self.selected_index = max(0, self.selected_index - 1)
        self.dirty = True
        self._render_all()

    def reload_current_dataset(self) -> None:
        path = self._dataset_file(self.current_key)
        try:
            self.dataset_data[self.current_key] = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(self.dataset_data[self.current_key], list):
                self.dataset_data[self.current_key] = []
            self.selected_index = 0 if self.current_data() else None
            self.dirty = False
            self._render_all()
        except Exception as exc:
            self._warn(f"{path.name} reload 실패: {exc}")

    def save_current_dataset(self) -> None:
        path = self._dataset_file(self.current_key)
        data = deepcopy(self.current_data())
        if self.selected_index is not None and self.form_fields and self.selected_index < len(data):
            data[self.selected_index] = self.collect_form_values()
            self.dataset_data[self.current_key] = data

        try:
            backup = path.with_suffix(path.suffix + ".bak")
            if path.exists():
                shutil.copy2(path, backup)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.dirty = False
            self._render_all()
            self.statusBar().showMessage(f"저장 완료: {path.name} (backup: {backup.name})")
        except Exception as exc:
            self._warn(f"저장 실패: {exc}")

    def sanitize_filename(self, raw: str) -> str:
        cleaned = "".join("_" if c in '<>:"/\\|?*' else c for c in raw.strip())
        cleaned = " ".join(cleaned.split())
        return cleaned

    def current_image_info(self) -> dict[str, Any] | None:
        if self.selected_index is None:
            return None
        item = self.collect_form_values()
        info = self.current_config().image_info(item, self.root_dir)
        if not info:
            return None
        info = dict(info)
        info["base_name"] = self.sanitize_filename(str(info.get("base_name", "")))
        info["candidates"] = [
            f"{Path(c).parent.as_posix()}/{self.sanitize_filename(Path(c).stem)}{Path(c).suffix}"
            for c in info.get("candidates", [])
        ]
        return info

    def refresh_image_preview(self) -> None:
        if not self.image_widget:
            return
        info = self.current_image_info()
        self.image_widget.set_people_aspect(info is not None and info.get("aspect") == "people")
        self.image_widget.set_info(info)
        if not info or not str(info.get("base_name", "")).strip():
            self.image_widget.set_preview_from_path(None)
            return

        folder: Path = info["folder"]
        base_name = info["base_name"]
        for ext in info.get("extensions", []):
            candidate = folder / f"{base_name}.{ext}"
            if candidate.exists():
                self.image_widget.set_preview_from_path(candidate)
                return
        self.image_widget.set_preview_from_path(None)

    def upload_current_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "이미지 선택",
            str(self.root_dir),
            "Images (*.jpg *.jpeg *.png *.gif)",
        )
        if not file_path:
            return
        self.upload_current_image_from_path(file_path)

    def upload_current_image_from_path(self, file_path: str) -> None:
        info = self.current_image_info()
        if not info or not str(info.get("base_name", "")).strip():
            self._warn("이미지 파일명 생성에 필요한 값을 먼저 입력하세요.")
            return

        src = Path(file_path)
        ext = src.suffix.lower().lstrip(".")
        if ext == "jpeg":
            ext = "jpg"
        if ext not in info.get("extensions", []):
            allowed = ", ".join(info.get("extensions", []))
            self._warn(f"지원하지 않는 형식입니다. 허용 형식: {allowed}")
            return

        target_folder: Path = info["folder"]
        target_folder.mkdir(parents=True, exist_ok=True)
        target = target_folder / f"{info['base_name']}.{ext}"

        try:
            shutil.copy2(src, target)
            self.refresh_image_preview()
            self.statusBar().showMessage(f"이미지 저장: {target.relative_to(self.root_dir)}")
        except Exception as exc:
            self._warn(f"이미지 저장 실패: {exc}")

    def _warn(self, message: str) -> None:
        QMessageBox.warning(self, APP_TITLE, message)


def resolve_root_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    window = AimLabAdmin(resolve_root_dir())
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()