variable "do_token" {
  description = "DigitalOcean API Token"
  type        = string
  sensitive   = true
}

variable "user_public_ssh_key" {
  description = "Optional personal public SSH key (e.g. cat ~/.ssh/id_ed25519.pub) to allow direct passwordless SSH access"
  type        = string
  default     = ""
}

variable "git_repo_url" {
  description = "Git clone HTTPS or SSH URL (e.g. https://github.com/your_username/blaine.git)"
  type        = string
  default     = "https://github.com/your_username/blaine.git"
}

variable "enable_github_deploy_key" {
  description = "Set to true to generate a dedicated SSH deploy key pair for private GitHub repository access"
  type        = bool
  default     = false
}

variable "telegram_bot_token" {
  description = "Telegram Bot Token"
  type        = string
  sensitive   = true
}

variable "gemini_api_key" {
  description = "Google Gemini API Key"
  type        = string
  sensitive   = true
}

variable "brave_api_key" {
  description = "Brave Search API Key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "rclone_config_base64" {
  description = "Base64 encoded rclone.conf file content (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "region" {
  description = "DigitalOcean datacenter region (e.g. lon1, nyc3, ams3)"
  type        = string
  default     = "lon1"
}

variable "droplet_size" {
  description = "Droplet instance slug size ($18/mo = s-2vcpu-2gb)"
  type        = string
  default     = "s-2vcpu-2gb"
}

variable "ssh_key_name" {
  description = "Name of the SSH key registered in DigitalOcean"
  type        = string
  default     = "blaine-deploy-key"
}

variable "droplet_name" {
  description = "Hostname for the Blaine server"
  type        = string
  default     = "blaine-ai-host"
}
