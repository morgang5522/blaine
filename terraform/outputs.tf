output "droplet_ip" {
  description = "Public IP address of the Blaine DigitalOcean Droplet"
  value       = digitalocean_droplet.blaine_server.ipv4_address
}

output "droplet_status" {
  description = "Status of the Blaine Droplet"
  value       = digitalocean_droplet.blaine_server.status
}

output "github_deploy_key" {
  description = "Public SSH key to paste into GitHub -> Settings -> Deploy keys"
  value       = tls_private_key.github_deploy_key.public_key_openssh
}

output "ssh_blaine_command" {
  description = "Command to SSH into the Blaine Droplet as non-root user 'blaine'"
  value       = "ssh -i id_ed25519 blaine@${digitalocean_droplet.blaine_server.ipv4_address}"
}

output "ssh_root_command" {
  description = "Command to SSH into the Blaine Droplet as root"
  value       = "ssh -i id_ed25519 root@${digitalocean_droplet.blaine_server.ipv4_address}"
}

output "redeploy_command" {
  description = "Command to trigger a 1-click update/rebuild as blaine user"
  value       = "ssh -i id_ed25519 blaine@${digitalocean_droplet.blaine_server.ipv4_address} '/opt/blaine/redeploy.sh'"
}
