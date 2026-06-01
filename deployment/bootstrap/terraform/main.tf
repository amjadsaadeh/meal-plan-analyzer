terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket   = "mealplananalyzer-dev-tfstate"
    key      = "bootstrap/terraform.tfstate"
    region   = "us-east-1" # required by S3 backend, ignored by Backblaze
    endpoint = "https://s3.eu-central-003.backblazeb2.com"

    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    use_path_style              = true

    # Credentials via env vars: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
  }

  encryption {
    key_provider "pbkdf2" "passphrase" {
      passphrase = var.state_encryption_passphrase

      key_length    = 32
      iterations    = 600000
      salt_length   = 32
      hash_function = "sha256"
    }

    method "aes_gcm" "default" {
      keys = key_provider.pbkdf2.passphrase
    }

    state {
      method = method.aes_gcm.default
    }

    plan {
      method = method.aes_gcm.default
    }
  }
}

variable "state_encryption_passphrase" {
  description = "Passphrase for state file encryption (set via TF_VAR_state_encryption_passphrase)"
  type        = string
  sensitive   = true
}

# ---------------------------------------------------------------------------
# Cloudflare DNS
# ---------------------------------------------------------------------------

variable "cloudflare_api_token" {
  type      = string
  sensitive = true
}

variable "cloudflare_zone_id" {
  type = string
}

variable "ipv4" {
  type = string
}

variable "ipv6" {
  type = string
}

# Credentials via env vars: TF_VAR_cloudflare_api_token
provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

resource "cloudflare_dns_record" "mealplananalyzer_dev_a" {
  zone_id = var.cloudflare_zone_id
  name    = "mealplananalyzer-dev"
  type    = "A"
  content = var.ipv4
  ttl     = 1
  proxied = false
}

resource "cloudflare_dns_record" "mealplananalyzer_dev_aaaa" {
  zone_id = var.cloudflare_zone_id
  name    = "mealplananalyzer-dev"
  type    = "AAAA"
  content = var.ipv6
  ttl     = 1
  proxied = false
}
