# Blaine AI Assistant: Complete Setup & Deployment Guide

This guide walks you through setting up and running **Blaine** both locally for development/testing and in production on a **DigitalOcean Droplet** using a 1-click automated **Terraform** deployment.

---

## 📋 Prerequisites & API Keys

Before starting, gather the following credentials:

1. **Telegram Bot Token**:
   - Open Telegram and search for `@BotFather`.
   - Send `/newbot`, name your bot (e.g. `BlaineAssistantBot`), and copy the API Token provided.

2. **Google Gemini API Key**:
   - Visit [Google AI Studio](https://aistudio.google.com/).
   - Click **Get API key** and copy your API key.

3. **DigitalOcean API Token** (for Terraform cloud deployment):
   - Log into your DigitalOcean dashboard.
   - Go to **API** $\rightarrow$ **Tokens/Keys** $\rightarrow$ **Generate New Token** (Read & Write).

4. **GitHub Repository URL**:
   - HTTPS URL for your repository (e.g., `https://github.com/your_username/blaine.git`).

---

## 💻 Option A: Running Locally for Development

### 1. Install System Dependencies
Ensure you have `ffmpeg` and `rclone` installed on your computer:

```bash
# On macOS (Homebrew)
brew install ffmpeg rclone

# On Ubuntu / Debian
sudo apt update && sudo apt install -y ffmpeg rclone
```

### 2. Install Python Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:
```ini
TELEGRAM_BOT_TOKEN="your_telegram_bot_token_here"
GEMINI_API_KEY="your_gemini_api_key_here"
```

### 4. Run Blaine Telegram Bot
```bash
python3 src/main.py bot
```
Open Telegram, search for your bot username, and type `/start`!

---

## ☁️ Option B: 1-Click Automated Terraform Deployment (DigitalOcean)

Terraform fully provisions the 2 vCPU / 4GB RAM Droplet, generates a secure SSH key pair, sets up a non-root system user (`blaine`), clones your repository over HTTPS, configures `.env`, builds Docker containers, and launches the entire stack automatically on boot.

### Step 1: Configure Terraform Variables

Navigate to the `terraform/` directory and create `terraform.tfvars`:

```bash
cd terraform/
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
do_token           = "dop_v1_your_digitalocean_token_here"
git_repo_url       = "https://github.com/your_username/blaine.git"
telegram_bot_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
gemini_api_key     = "AIzaSyYourGeminiApiKeyHere"

# Optional: Set to true if cloning a private fork over SSH (git@github.com:username/blaine.git)
# enable_github_deploy_key = true

# Optional: Add your personal public SSH key (cat ~/.ssh/id_ed25519.pub) for direct access
# user_public_ssh_key = "ssh-ed25519 AAAAC3N..."

# Optional: Base64 encoded rclone.conf (cat ~/.config/rclone/rclone.conf | base64)
# rclone_config_base64 = "..."

region       = "lon1"       # Datacenter region (e.g. lon1, nyc3, ams3)
droplet_size = "s-2vcpu-4gb" # 2 vCPU, 4GB RAM suitable for yt-dlp & ffmpeg
```

### Step 2: Initialize & Apply Infrastructure

```bash
terraform init
terraform plan --out plan.tfplan
terraform apply plan.tfplan
```

When `terraform apply` completes, Terraform outputs your server details and automatically saves the private SSH key locally at `terraform/id_ed25519` (mode `0600`):

```
Outputs:
droplet_ip        = "206.189.XX.XX"
ssh_command       = "ssh -i id_ed25519 blaine@206.189.XX.XX"
redeploy_command  = "ssh -i id_ed25519 blaine@206.189.XX.XX '/opt/blaine/redeploy.sh'"
```

Within ~45–60 seconds of Droplet boot, the background setup script completes cloning, building, and starting Docker Compose automatically!

---

## 🚀 Managing & Updating Your Live Server

### Connecting via SSH
Connect as the hardened non-root `blaine` system user:
```bash
ssh -i id_ed25519 blaine@<YOUR_DROPLET_IP>
```
*(Or as root for system administration: `ssh -i id_ed25519 root@<YOUR_DROPLET_IP>`)*

### Checking Setup & Container Status
```bash
# Check cloud-init setup logs
tail -f /var/log/blaine-setup.log

# Check running Docker containers
docker compose -f /opt/blaine/docker-compose.yml ps
docker compose -f /opt/blaine/docker-compose.yml logs -f
```

### 1-Click Code Updates (Redeployment)
Whenever you push code changes to `main`, update your live server in seconds without destroying the Droplet:

```bash
ssh -i id_ed25519 blaine@<YOUR_DROPLET_IP> '/opt/blaine/redeploy.sh'
```

---

## ☁️ Setting Up Cloud Remotes (MEGA S3 / Google Drive)

### Option A: Via Terraform (Recommended)
Base64 encode your local `rclone.conf` and set `rclone_config_base64` in `terraform.tfvars`:
```bash
cat ~/.config/rclone/rclone.conf | base64
```
Terraform will automatically inject your rclone credentials onto the server.

### Option B: Manually on the Server
SSH into the server and run `rclone config` as user `blaine`:
```bash
ssh -i id_ed25519 blaine@<YOUR_DROPLET_IP>
rclone config
```

---

## 💬 How to Interact with Blaine

1. **Start Conversation**:
   Send `/start` or a greeting like *"Hello Blaine!"*

2. **Archive & Sync Media**:
   Send any YouTube, Vimeo, TikTok, or podcast URL:
   > *"Blaine, can you save this video into my Tech Podcasts folder?"*  
   > `https://www.youtube.com/watch?v=EXAMPLE`

3. **Format Quality Selection**:
   Blaine replies in her warm conversational tone and offers inline quality buttons:
   `[🎬 1080p Video] [🎧 MP3 Audio]`

4. **Persistent Memory & Preferences**:
   Tell Blaine your preferences directly:
   > *"Blaine, remember that I prefer 1080p for tech videos."*  
   She will save this into her SQLite memory database and recall it in future chats!

5. **Reset Conversation Memory**:
   Send `/forget` to clear short-term chat history.
