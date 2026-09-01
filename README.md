# DialogueForge Studio

A lightweight desktop application for AI-assisted screenplay and dialogue writing.

DialogueForge Studio is built with **Python and PySide6** and allows writers to create projects, manage characters, write scenes, and use either **local Ollama models** or supported cloud AI providers to generate and improve dialogue.

## Features

### Project Management

Each project contains:

- Project title
- Genre
- Scene number
- Scene text
- Character information
- AI provider selection
- AI model selection

Projects are saved as standard JSON files.

### Character Management

Create, edit, and remove characters.

Each character can contain:

- Name
- Age
- Personality
- Notes

Character information is automatically included in the AI prompt when dialogue is generated.

### Scene Editor

Write your screenplay scene directly in the application.

The editor supports:

- Writing and editing scenes
- Selecting existing dialogue
- Sending scene context to the AI
- Inserting generated dialogue back into the scene

### AI Dialogue Tools

DialogueForge Studio provides several AI writing actions:

- **Generate Dialogue** – Generate screenplay dialogue for the current scene
- **Continue Scene** – Continue the existing scene
- **Rewrite Selected** – Rewrite selected dialogue
- **Make Natural** – Make dialogue sound more natural and conversational
- **Increase Tension** – Add dramatic tension and emotional conflict

The AI receives context including:

- Project title
- Genre
- Character information
- Character personalities
- Character notes
- Current scene
- Selected text
- Requested writing action

The application instructs the AI to return screenplay dialogue and necessary screenplay action without additional explanation.

## AI Providers

DialogueForge Studio currently supports the following providers:

### Ollama Local

Local Ollama models are accessed through:

```text
http://localhost:11434
