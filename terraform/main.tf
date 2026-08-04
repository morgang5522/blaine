# 1. Dedicated SSH Key Pair for Server Access (Root & Blaine user)
resource "tls_private_key" "server_ssh_key" {
  algorithm = "ED25519"
}

# Save server private SSH key locally so you can SSH using `ssh -i id_ed25519 blaine@<ip>` or `root@<ip>`
resource "local_sensitive_file" "server_private_key_file" {
  content         = tls_private_key.server_ssh_key.private_key_openssh
  filename        = "${path.module}/id_ed25519"
  file_permission = "0600"
}

# Register server public SSH key with DigitalOcean (authorizes root user access)
resource "digitalocean_ssh_key" "server_ssh_key" {
  name       = var.ssh_key_name
  public_key = tls_private_key.server_ssh_key.public_key_openssh
}

# 2. Dedicated Deploy Key Pair for GitHub Repository Access
resource "tls_private_key" "github_deploy_key" {
  algorithm = "ED25519"
}

# Optional: Register user's personal public SSH key with DigitalOcean
resource "digitalocean_ssh_key" "user_ssh_key" {
  count      = var.user_public_ssh_key != "" ? 1 : 0
  name       = "blaine-user-personal-key"
  public_key = var.user_public_ssh_key
}

# DigitalOcean Droplet Resource
resource "digitalocean_droplet" "blaine_server" {
  image      = "ubuntu-24-04-x64"
  name       = var.droplet_name
  region     = var.region
  size       = var.droplet_size
  ssh_keys   = compact([
    digitalocean_ssh_key.server_ssh_key.id,
    try(digitalocean_ssh_key.user_ssh_key[0].id, "")
  ])
  monitoring = true

  user_data = templatefile("${path.module}/templates/user_data.sh.tftpl", {
    server_public_key         = tls_private_key.server_ssh_key.public_key_openssh
    github_deploy_private_key = tls_private_key.github_deploy_key.private_key_openssh
    github_deploy_public_key  = tls_private_key.github_deploy_key.public_key_openssh
    git_repo_url              = var.git_repo_url
    telegram_bot_token        = var.telegram_bot_token
    gemini_api_key            = var.gemini_api_key
    rclone_config_base64      = var.rclone_config_base64
  })

  tags = ["blaine", "ai-assistant"]
}

# DigitalOcean Firewall Resource
resource "digitalocean_firewall" "blaine_firewall" {
  name = "blaine-firewall"

  droplet_ids = [digitalocean_droplet.blaine_server.id]

  # Allow inbound SSH
  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Allow all outbound traffic (for yt-dlp, Gemini API, Rclone, Telegram)
  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}
