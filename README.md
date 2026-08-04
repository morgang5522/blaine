# Blaine: Autonomous AI Media Archiving & Sync Assistant

Blaine is a warm, intelligent AI assistant operating via Telegram. She archives media (`yt-dlp` & `ffmpeg`), organizes files into structured folder hierarchies, and syncs media to cloud storage (MEGA S3 & Google Drive). She is built with **Google Gemini API**, an **SQLite memory engine**, and an **extensible tool registry**.

All cloud infrastructure is provisioned on **DigitalOcean** via **Terraform** using a 1-click automated setup.

---

## 📖 Quick Links & Documentation

- 📘 **[Complete Setup & Deployment Guide](SETUP.md)** - Step-by-step local testing & DigitalOcean Terraform setup.

---

## 📂 Repository Structure

```
blaine/
├── SETUP.md                        # Complete installation & deployment guide
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Production container image definition
├── docker-compose.yml              # Services composition (Bot, Worker, Redis)
├── README.md                       # Repository overview
│
├── terraform/                      # Infrastructure as Code (DigitalOcean)
│   ├── provider.tf                # DigitalOcean & TLS providers
│   ├── main.tf                    # Droplet, Firewall, SSH key resources
│   ├── variables.tf               # Infrastructure & app environment variables
│   ├── outputs.tf                 # Server IP, SSH, and redeployment outputs
│   └── templates/
│       └── user_data.sh.tftpl     # Automated cloud-init bootstrap template
│
└── src/                            # Blaine Core Application
    ├── bot.py                     # Telegram Bot interface & handler
    ├── ai_engine.py               # Gemini AI engine, system prompt & turn parser
    ├── memory.py                  # SQLite memory database (Short-term & Facts)
    ├── worker.py                  # Redis async queue task consumer
    ├── main.py                    # Application entrypoint (bot/worker)
    ├── config.py                  # Environment & fallback settings
    │
    ├── tools/                     # Plugin Tool Registry & Capabilities
    │   ├── base.py                # Abstract BaseTool interface
    │   ├── lists.py               # Custom user list management (to-do, shopping, etc.)
    │   ├── media.py               # Media archiving & cloud storage sync tools
    │   ├── memory.py              # Dynamic long-term user fact storage tool
    │   ├── registry.py            # Tool registry & Gemini function calling builder
    │   ├── reminders.py           # Reminder tools (schedule, cancel, list, amend)
    │   └── web_search.py          # Real-time web search tool
    │
    └── pipeline/                  # Core processing pipeline
        ├── archiver.py            # yt-dlp & ffmpeg downloader
        ├── organizer.py           # Structured media path sorter
        └── cloud_sync.py          # MEGA S3 & Google Drive sync engine
```

---

## ⚡ Quick Start

### Option A: Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment (.env)
cp .env.example .env

# 3. Launch Blaine Telegram Bot
python3 src/main.py bot
```

### Option B: 1-Click DigitalOcean Cloud Deployment

```bash
cd terraform/
cp terraform.tfvars.example terraform.tfvars
# Fill in do_token, git_repo_url, telegram_bot_token, gemini_api_key in terraform.tfvars

terraform init
terraform apply
```

For detailed deployment and update steps, refer to **[SETUP.md](SETUP.md)**.
