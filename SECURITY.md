# Security Policy

This repository contains portfolio labs and synthetic examples. It must not contain production credentials, customer data, private keys, cloud state files or employer-confidential material.

## Reporting a security issue

Do **not** paste credentials, tokens or sensitive logs into a public issue.

If GitHub private vulnerability reporting is available for this repository, use it. Otherwise, open a minimal public issue that contains no sensitive data and asks the repository owner to establish a private contact channel.

## Supported code

The `main` branch is the maintained portfolio version. Security-related fixes should include a regression test where practical.

## Repository hygiene

- Keep Terraform state, tfvars containing sensitive values and saved plans out of Git.
- Use short-lived cloud credentials for any separately authorized lab execution.
- Keep automated remediation disabled unless a future design adds explicit, auditable human approval.
- Sanitize screenshots and command output before publishing them as portfolio evidence.
