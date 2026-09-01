import json
import os
import sys
from dataclasses import dataclass

import requests

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QListWidget,
    QListWidgetItem,
)


APP_NAME = "DialogueForge Studio"


@dataclass
class AISettings:
    provider: str = "Ollama Local"
    model: str = "jimscard/new-adult-writer"
    api_key: str = ""
    base_url: str = ""


class AIWorker(QThread):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, settings, prompt):
        super().__init__()
        self.settings = settings
        self.prompt = prompt

    def run(self):
        try:
            if self.settings.provider == "Ollama Local":
                result = self.generate_ollama()

            elif self.settings.provider == "OpenRouter":
                result = self.generate_openai_compatible(
                    "https://openrouter.ai/api/v1/chat/completions"
                )

            elif self.settings.provider == "Groq":
                result = self.generate_openai_compatible(
                    "https://api.groq.com/openai/v1/chat/completions"
                )

            elif self.settings.provider == "Custom API":
                result = self.generate_openai_compatible(
                    self.settings.base_url
                )

            else:
                raise RuntimeError(
                    f"Provider not implemented: {self.settings.provider}"
                )

            self.finished.emit(result)

        except Exception as error:
            self.failed.emit(str(error))

    def generate_ollama(self):
        url = "http://localhost:11434/api/generate"

        response = requests.post(
            url,
            json={
                "model": self.settings.model,
                "prompt": self.prompt,
                "stream": False,
            },
            timeout=300,
        )

        response.raise_for_status()

        data = response.json()

        return data.get("response", "")

    def generate_openai_compatible(self, url):
        if not url:
            raise RuntimeError("API URL is not configured.")

        if not self.settings.api_key:
            raise RuntimeError("API key is required.")

        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            url,
            headers=headers,
            json={
                "model": self.settings.model,
                "messages": [
                    {
                        "role": "user",
                        "content": self.prompt,
                    }
                ],
                "temperature": 0.8,
            },
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()

        return data["choices"][0]["message"]["content"]


class CharacterDialog(QDialog):

    def __init__(self, parent=None, data=None):
        super().__init__(parent)

        self.setWindowTitle("Character")

        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.age_edit = QLineEdit()
        self.personality_edit = QPlainTextEdit()
        self.notes_edit = QPlainTextEdit()

        layout.addRow("Name:", self.name_edit)
        layout.addRow("Age:", self.age_edit)
        layout.addRow("Personality:", self.personality_edit)
        layout.addRow("Notes:", self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addRow(buttons)

        if data:
            self.name_edit.setText(data.get("name", ""))
            self.age_edit.setText(data.get("age", ""))
            self.personality_edit.setPlainText(
                data.get("personality", "")
            )
            self.notes_edit.setPlainText(
                data.get("notes", "")
            )

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "age": self.age_edit.text().strip(),
            "personality": self.personality_edit.toPlainText().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
        }


class DialogueForge(QMainWindow):

    def __init__(self):
        super().__init__()

        self.settings = AISettings()
        self.characters = []
        self.current_file = None
        self.worker = None

        self.setWindowTitle(APP_NAME)
        self.resize(1400, 850)

        self.build_ui()
        self.refresh_ollama_models()

    def build_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)

        header = QHBoxLayout()

        title = QLabel(APP_NAME)
        title.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        self.status_label = QLabel("● Ready")

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status_label)

        main_layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        splitter.addWidget(self.create_sidebar())
        splitter.addWidget(self.create_editor_area())

        splitter.setSizes([350, 1000])

        main_layout.addWidget(splitter)

    def create_sidebar(self):

        panel = QWidget()
        layout = QVBoxLayout(panel)

        project_label = QLabel("PROJECT")
        project_label.setStyleSheet("font-weight: bold;")

        layout.addWidget(project_label)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Project title")

        self.genre_edit = QLineEdit()
        self.genre_edit.setPlaceholderText("Genre")

        self.scene_number_edit = QLineEdit()
        self.scene_number_edit.setPlaceholderText("Scene number")

        layout.addWidget(self.title_edit)
        layout.addWidget(self.genre_edit)
        layout.addWidget(self.scene_number_edit)

        characters_label = QLabel("CHARACTERS")
        characters_label.setStyleSheet("font-weight: bold;")

        layout.addSpacing(10)
        layout.addWidget(characters_label)

        self.character_list = QListWidget()

        layout.addWidget(self.character_list)

        character_buttons = QHBoxLayout()

        add_character = QPushButton("+ Add")
        edit_character = QPushButton("Edit")
        remove_character = QPushButton("Remove")

        add_character.clicked.connect(self.add_character)
        edit_character.clicked.connect(self.edit_character)
        remove_character.clicked.connect(self.remove_character)

        character_buttons.addWidget(add_character)
        character_buttons.addWidget(edit_character)
        character_buttons.addWidget(remove_character)

        layout.addLayout(character_buttons)

        ai_label = QLabel("AI SETTINGS")
        ai_label.setStyleSheet("font-weight: bold;")

        layout.addSpacing(10)
        layout.addWidget(ai_label)

        self.provider_combo = QComboBox()

        self.provider_combo.addItems([
            "Ollama Local",
            "OpenRouter",
            "Groq",
            "Custom API",
        ])

        self.provider_combo.currentTextChanged.connect(
            self.provider_changed
        )

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)

        layout.addWidget(QLabel("Provider"))
        layout.addWidget(self.provider_combo)

        layout.addWidget(QLabel("Model"))
        layout.addWidget(self.model_combo)

        settings_button = QPushButton("Provider Settings")
        settings_button.clicked.connect(
            self.configure_provider
        )

        test_button = QPushButton("Test Connection")
        test_button.clicked.connect(
            self.test_connection
        )

        layout.addWidget(settings_button)
        layout.addWidget(test_button)

        layout.addStretch()

        save_button = QPushButton("Save Project")
        save_button.clicked.connect(self.save_project)

        open_button = QPushButton("Open Project")
        open_button.clicked.connect(self.open_project)

        layout.addWidget(save_button)
        layout.addWidget(open_button)

        return panel

    def create_editor_area(self):

        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel("SCENE"))

        self.scene_editor = QPlainTextEdit()

        self.scene_editor.setPlaceholderText(
            "Write your scene here...\n\n"
            "Example:\n\n"
            "INT. COFFEE SHOP – NIGHT\n\n"
            "Maya enters and sees Raj sitting alone."
        )

        layout.addWidget(
            self.scene_editor,
            stretch=3
        )

        tools = QHBoxLayout()

        generate = QPushButton("Generate Dialogue")
        continue_scene = QPushButton("Continue Scene")
        rewrite = QPushButton("Rewrite Selected")
        natural = QPushButton("More Natural")
        tension = QPushButton("Increase Tension")

        generate.clicked.connect(
            lambda: self.generate_dialogue("generate")
        )

        continue_scene.clicked.connect(
            lambda: self.generate_dialogue("continue")
        )

        rewrite.clicked.connect(
            lambda: self.generate_dialogue("rewrite")
        )

        natural.clicked.connect(
            lambda: self.generate_dialogue("natural")
        )

        tension.clicked.connect(
            lambda: self.generate_dialogue("tension")
        )

        tools.addWidget(generate)
        tools.addWidget(continue_scene)
        tools.addWidget(rewrite)
        tools.addWidget(natural)
        tools.addWidget(tension)

        layout.addLayout(tools)

        layout.addWidget(QLabel("AI DIALOGUE"))

        self.output_editor = QPlainTextEdit()

        self.output_editor.setPlaceholderText(
            "Generated dialogue will appear here..."
        )

        layout.addWidget(
            self.output_editor,
            stretch=2
        )

        output_tools = QHBoxLayout()

        insert_button = QPushButton(
            "Insert into Scene"
        )

        copy_button = QPushButton("Copy")

        clear_button = QPushButton("Clear")

        insert_button.clicked.connect(
            self.insert_output
        )

        copy_button.clicked.connect(
            self.copy_output
        )

        clear_button.clicked.connect(
            self.output_editor.clear
        )

        output_tools.addWidget(insert_button)
        output_tools.addWidget(copy_button)
        output_tools.addWidget(clear_button)

        layout.addLayout(output_tools)

        return panel

    def refresh_ollama_models(self):

        try:
            response = requests.get(
                "http://localhost:11434/api/tags",
                timeout=5,
            )

            response.raise_for_status()

            data = response.json()

            models = [
                item["name"]
                for item in data.get("models", [])
            ]

            self.model_combo.clear()

            self.model_combo.addItems(models)

            preferred = "jimscard/new-adult-writer"

            index = self.model_combo.findText(
                preferred
            )

            if index >= 0:
                self.model_combo.setCurrentIndex(
                    index
                )

        except Exception:
            self.model_combo.clear()
            self.model_combo.addItem(
                "jimscard/new-adult-writer"
            )

    def provider_changed(self, provider):

        self.settings.provider = provider

        if provider == "Ollama Local":
            self.refresh_ollama_models()

        else:
            self.model_combo.clear()
            self.model_combo.setEditable(True)

    def configure_provider(self):

        provider = self.provider_combo.currentText()

        if provider == "Ollama Local":

            QMessageBox.information(
                self,
                APP_NAME,
                "Ollama Local uses:\n\n"
                "http://localhost:11434"
            )

            return

        api_key, ok = QInputDialog.getText(
            self,
            "API Key",
            f"Enter API key for {provider}:",
            QLineEdit.EchoMode.Password,
            self.settings.api_key,
        )

        if not ok:
            return

        self.settings.api_key = api_key

        if provider == "Custom API":

            base_url, ok = QInputDialog.getText(
                self,
                "Custom API URL",
                "Chat completions endpoint:",
                text=self.settings.base_url,
            )

            if ok:
                self.settings.base_url = base_url.strip()

        QMessageBox.information(
            self,
            APP_NAME,
            "Provider settings saved for this session."
        )

    def test_connection(self):

        provider = self.provider_combo.currentText()

        try:

            if provider == "Ollama Local":

                response = requests.get(
                    "http://localhost:11434/api/tags",
                    timeout=5,
                )

                response.raise_for_status()

                QMessageBox.information(
                    self,
                    APP_NAME,
                    "Ollama is connected successfully."
                )

            else:

                QMessageBox.information(
                    self,
                    APP_NAME,
                    "Cloud provider configuration saved.\n\n"
                    "The connection will be tested when "
                    "you generate dialogue."
                )

        except Exception as error:

            QMessageBox.warning(
                self,
                "Connection Error",
                str(error)
            )

    def add_character(self):

        dialog = CharacterDialog(self)

        if dialog.exec():

            data = dialog.get_data()

            if not data["name"]:
                return

            self.characters.append(data)

            self.refresh_characters()

    def edit_character(self):

        row = self.character_list.currentRow()

        if row < 0:
            return

        dialog = CharacterDialog(
            self,
            self.characters[row],
        )

        if dialog.exec():

            self.characters[row] = dialog.get_data()

            self.refresh_characters()

    def remove_character(self):

        row = self.character_list.currentRow()

        if row < 0:
            return

        del self.characters[row]

        self.refresh_characters()

    def refresh_characters(self):

        self.character_list.clear()

        for character in self.characters:

            item = QListWidgetItem(
                character["name"]
            )

            self.character_list.addItem(item)

    def build_character_context(self):

        if not self.characters:
            return "No characters have been defined."

        parts = []

        for character in self.characters:

            parts.append(
                f"Name: {character['name']}\n"
                f"Age: {character['age']}\n"
                f"Personality: "
                f"{character['personality']}\n"
                f"Notes: {character['notes']}"
            )

        return "\n\n".join(parts)

    def generate_dialogue(self, mode):

        scene = self.scene_editor.toPlainText().strip()

        if not scene:
            QMessageBox.warning(
                self,
                APP_NAME,
                "Please write a scene first."
            )

            return

        selected_text = (
            self.scene_editor.textCursor()
            .selectedText()
        )

        instructions = {
            "generate":
                "Generate realistic screenplay dialogue "
                "for this scene.",

            "continue":
                "Continue the scene with screenplay dialogue.",

            "rewrite":
                "Rewrite the selected dialogue to make it "
                "stronger and more natural.",

            "natural":
                "Rewrite the dialogue to sound more natural, "
                "human, and conversational.",

            "tension":
                "Rewrite or continue the dialogue with more "
                "dramatic tension and emotional conflict.",
        }

        instruction = instructions[mode]

        context = (
            f"PROJECT TITLE:\n"
            f"{self.title_edit.text()}\n\n"

            f"GENRE:\n"
            f"{self.genre_edit.text()}\n\n"

            f"CHARACTERS:\n"
            f"{self.build_character_context()}\n\n"

            f"SCENE:\n"
            f"{scene}\n\n"

            f"SELECTED TEXT:\n"
            f"{selected_text}\n\n"

            f"INSTRUCTION:\n"
            f"{instruction}\n\n"

            "Return only the screenplay dialogue and "
            "necessary screenplay action. "
            "Do not explain your answer."
        )

        self.settings.provider = (
            self.provider_combo.currentText()
        )

        self.settings.model = (
            self.model_combo.currentText().strip()
        )

        if not self.settings.model:
            QMessageBox.warning(
                self,
                APP_NAME,
                "Please select or enter a model name."
            )

            return

        self.status_label.setText(
            "● Generating..."
        )

        self.output_editor.clear()

        self.worker = AIWorker(
            self.settings,
            context,
        )

        self.worker.finished.connect(
            self.generation_finished
        )

        self.worker.failed.connect(
            self.generation_failed
        )

        self.worker.start()

    def generation_finished(self, result):

        self.output_editor.setPlainText(
            result
        )

        self.status_label.setText(
            "● Ready"
        )

    def generation_failed(self, error):

        self.status_label.setText(
            "● Error"
        )

        QMessageBox.warning(
            self,
            "Generation Error",
            error
        )

    def insert_output(self):

        text = (
            self.output_editor.toPlainText()
        )

        if not text:
            return

        cursor = (
            self.scene_editor.textCursor()
        )

        cursor.insertText(
            "\n\n" + text
        )

    def copy_output(self):

        QApplication.clipboard().setText(
            self.output_editor.toPlainText()
        )

        self.status_label.setText(
            "● Copied"
        )

    def save_project(self):

        data = {
            "title": self.title_edit.text(),
            "genre": self.genre_edit.text(),
            "scene_number":
                self.scene_number_edit.text(),
            "scene":
                self.scene_editor.toPlainText(),
            "characters":
                self.characters,
            "ai_settings": {
                "provider":
                    self.provider_combo.currentText(),
                "model":
                    self.model_combo.currentText(),
            },
        }

        filename = self.current_file

        if not filename:

            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save DialogueForge Project",
                "",
                "DialogueForge Project (*.json)",
            )

        if not filename:
            return

        if not filename.endswith(".json"):
            filename += ".json"

        with open(
            filename,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False,
            )

        self.current_file = filename

        self.status_label.setText(
            "● Project Saved"
        )

    def open_project(self):

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open DialogueForge Project",
            "",
            "DialogueForge Project (*.json)",
        )

        if not filename:
            return

        try:

            with open(
                filename,
                "r",
                encoding="utf-8",
            ) as file:

                data = json.load(file)

            self.title_edit.setText(
                data.get("title", "")
            )

            self.genre_edit.setText(
                data.get("genre", "")
            )

            self.scene_number_edit.setText(
                data.get("scene_number", "")
            )

            self.scene_editor.setPlainText(
                data.get("scene", "")
            )

            self.characters = data.get(
                "characters",
                [],
            )

            self.refresh_characters()

            ai = data.get(
                "ai_settings",
                {},
            )

            provider = ai.get(
                "provider",
                "Ollama Local",
            )

            index = self.provider_combo.findText(
                provider
            )

            if index >= 0:
                self.provider_combo.setCurrentIndex(
                    index
                )

            model = ai.get("model", "")

            if model:
                self.model_combo.setCurrentText(
                    model
                )

            self.current_file = filename

            self.status_label.setText(
                "● Project Loaded"
            )

        except Exception as error:

            QMessageBox.warning(
                self,
                "Open Error",
                str(error),
            )


def main():

    app = QApplication(sys.argv)

    app.setApplicationName(
        APP_NAME
    )

    window = DialogueForge()

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
