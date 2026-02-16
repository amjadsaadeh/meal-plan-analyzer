# Meal Plan Analyzer

This small application that provide a basic meal planning and analyzing capibility, based on the Bundes Lebensmittel Schlüssel.
It is somehow my toy project to get more practice in using AI coding tools.

## Setup

```bash
uv sync
```


## Deploy

Prepare your k8s config.

```bash
cd ansible
uv run ansible-playbook --vault-id saadeh.devk3s@vault-key-client deploy.yml
```

