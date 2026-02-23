#! /bin/bash

uv run ansible-vault edit --vault-id ${ANSIBLE_VAULT_ID}@vault-key-client vault.yml
