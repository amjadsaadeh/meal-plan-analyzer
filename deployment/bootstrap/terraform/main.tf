terraform {
  required_providers {
    netcup-ccp = {
      source  = "rincedd/netcup-ccp"
      version = "0.0.1"
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
# Netcup DNS
# ---------------------------------------------------------------------------

variable "netcup_customer_number" {
  type      = string
  sensitive = true
}

variable "netcup_api_key" {
  type      = string
  sensitive = true
}

variable "netcup_api_password" {
  type      = string
  sensitive = true
}

variable "domain" {
  type    = string
  default = "saadeh.dev"
}

variable "ipv4" {
  type = string
}

variable "ipv6" {
  type = string
}

# Credentials via env vars: TF_VAR_netcup_customer_number, TF_VAR_netcup_api_key, TF_VAR_netcup_api_password
provider "netcup-ccp" {
  customer_number  = var.netcup_customer_number
  ccp_api_key      = var.netcup_api_key
  ccp_api_password = var.netcup_api_password
}

resource "netcup-ccp_dns_record" "mealplananalyzer_dev_a" {
  domain_name = var.domain
  name        = "mealplananalyzer-dev"
  type        = "A"
  value       = var.ipv4
  priority    = "0"
}

resource "netcup-ccp_dns_record" "mealplananalyzer_dev_aaaa" {
  domain_name = var.domain
  name        = "mealplananalyzer-dev"
  type        = "AAAA"
  value       = var.ipv6
  priority    = "0"
}
