# 🤖 Blaine AI: Personal Assistant & Media Archiver

> A self-hosted, personal AI assistant for Telegram with persistent memory, automated media archiving, cloud storage sync, and dynamic web tools.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE.md)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg)](docker-compose.yml)
[![Terraform](https://img.shields.io/badge/Terraform-1.0+-7B42BC.svg)](terraform/)
[![Google Gemini API](https://img.shields.io/badge/AI%20Engine-Google%20Gemini-4285F4.svg)](src/ai_engine.py)

Blaine is an open-source, conversational AI assistant operating via **Telegram**. She goes beyond simple chat by combining natural language understanding powered by **Google Gemini** with an asynchronous background task execution pipeline, persistent SQLite long-term memory, and 1-click cloud infrastructure deployment via **Terraform**.

---

## ✨ Key Features

- 🧠 **Persistent Long-Term Memory**: Remembers user facts, personal preferences, and context across chat sessions in a local SQLite database.
- 🎥 **Media Archiving & Cloud Sync**: Send YouTube, TikTok, Vimeo, or podcast URLs directly in Telegram. Blaine downloads them in your preferred format (`yt-dlp` + `ffmpeg`) and automatically syncs them to **Google Drive** or **MEGA S3** (`rclone`).
- ⏰ **Smart Reminders**: Schedule, list, or cancel reminders using natural language (e.g., _"Remind me to check the oven in 25 minutes"_ or _"Remind me about the team sync on Friday at 3pm"_).
- 📝 **Dynamic Custom Lists**: Create and manage to-do lists, shopping lists, or reading lists conversationally.
- 🔍 **Real-Time Web Search**: Integrates with the **Brave Search API** for up-to-date answers and web research.
- 💬 **Interactive Telegram UX**: Includes inline quality selector buttons (e.g., `[🎬 1080p Video]`, `[🎧 MP3 Audio]`) and interactive control flows.
- ☁️ **1-Click Terraform Deployment**: Spin up a fully configured, hardened Ubuntu server on **DigitalOcean** running Docker Compose in under a minute.

---

## 🏗️ Architecture Overview

```
 ┌─────────────────────────────────────────────────────────────┐
 │                      Telegram User                          │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                        (Telegram Bot API)
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                  Blaine Bot (src/bot.py)                    │
 └──────────────┬───────────────────────────────┬──────────────┘
                │                               │
       (Function Calling)                (Async Tasks)
                │                               │
                ▼                               ▼
 ┌──────────────────────────────┐ ┌───────────────────────────┐
 │     Gemini AI Engine         │ │        Redis Queue        │
 │    (src/ai_engine.py)        │ └─────────────┬─────────────┘
 └──────────────┬───────────────┘               │
                │                               ▼
        (Tool Registry)           ┌───────────────────────────┐
   ┌────────────┴────────────┐    │      Worker Service       │
   ▼                         ▼    │     (src/worker.py)       │
 ┌───────────┐         ┌────────┐ └─────────────┬─────────────┘
 │ SQLite DB │         │ Web    │               │
 │ (Memory)  │         │ Search │       (yt-dlp / Rclone)
 └───────────┘         └────────┘               │
                                                ▼
                                  ┌───────────────────────────┐
                                  │   MEGA S3 / Google Drive  │
                                  └───────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Local Development

Ensure you have **Python 3.11+**, `ffmpeg`, and `rclone` installed on your system.

```bash
# Clone the repository
git clone https://github.com/morgang5522/blaine.git
cd blaine

# Install Python dependencies
pip install -r requirements.txt

# Create environment configuration
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN and GEMINI_API_KEY

# Run Blaine locally
python3 src/main.py bot
```

### 2. 1-Click DigitalOcean Cloud Deployment

Blaine includes full **Terraform** Infrastructure-as-Code to provision a hardened DigitalOcean Droplet running Docker Compose automatically:

```bash
cd terraform/
cp terraform.tfvars.example terraform.tfvars
# Fill in do_token, git_repo_url, telegram_bot_token, and gemini_api_key

terraform init
terraform apply
```

For step-by-step instructions, environment variable details, and cloud remote setup, see the **[Complete Setup & Deployment Guide (SETUP.md)](SETUP.md)**.

---

## 📂 Repository Layout

```
blaine/
├── SETUP.md                        # Complete setup & deployment guide
├── README.md                       # Main project documentation
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Production container image definition
├── docker-compose.yml              # Multi-container stack (Bot, Worker, Redis)
│
├── terraform/                      # Infrastructure as Code (DigitalOcean)
│   ├── main.tf                    # Droplet, Firewall, SSH key resources
│   ├── provider.tf                # DigitalOcean provider config
│   ├── variables.tf               # Terraform input variables
│   ├── outputs.tf                 # Server IP, SSH & redeployment outputs
│   └── templates/
│       └── user_data.sh.tftpl     # Automated cloud-init bootstrap script
│
└── src/                            # Core Application Source Code
    ├── bot.py                     # Telegram Bot interface & message handlers
    ├── ai_engine.py               # Gemini AI Engine & function calling logic
    ├── memory.py                  # SQLite memory database (facts & conversation)
    ├── worker.py                  # Background Redis task consumer
    ├── main.py                    # Application entrypoint CLI
    ├── config.py                  # Centralized application settings
    │
    ├── tools/                     # Extensible Tool Plugin Registry
    │   ├── base.py                # Abstract BaseTool interface
    │   ├── lists.py               # Custom user lists (to-do, shopping, etc.)
    │   ├── media.py               # Media archiving & cloud sync tools
    │   ├── memory.py              # User facts storage tool
    │   ├── registry.py            # Dynamic tool registry builder
    │   ├── reminders.py           # Natural language reminder tools
    │   └── web_search.py          # Brave Search API integration
    │
    └── pipeline/                  # Media Pipeline Core
        ├── archiver.py            # yt-dlp & ffmpeg downloader engine
        ├── organizer.py           # Dynamic directory hierarchy sorter
        └── cloud_sync.py          # Rclone MEGA S3 & Google Drive sync
```

---

## 🧩 Adding Custom Tools

Blaine features an extensible **Tool Registry**. You can create custom tools by extending `BaseTool`:

```python
from src.tools.base import BaseTool

class CustomTool(BaseTool):
    name = "custom_tool"
    description = "Description of what your tool does for Gemini AI."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"}
        },
        "required": ["query"]
    }

    def execute(self, **kwargs) -> str:
        # Tool execution logic here
        return "Tool execution result"
```

Register your tool in `src/tools/registry.py` and Blaine's Gemini AI engine will automatically incorporate it into function calling!

---

## 📜 License

This project is open-source software licensed under the **[MIT License](LICENSE.md)**.

---

## 🤝 Contributing

Contributions, issue reports, and feature suggestions are welcome! Feel free to open an issue or submit a Pull Request.
