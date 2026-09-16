# Security Policy

## Supported Versions

Only the current major version (V2) is actively supported for security updates.

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| 1.0.x   | :x:                |

## Reporting a Vulnerability

Please do not report security vulnerabilities through public GitHub issues.

Instead, please send an email to security@fintechguru.local. We will acknowledge receipt of your vulnerability report within 48 hours and strive to send you regular updates about our progress.

## Architecture Security Guarantees
- **Hard Safety Boundary**: The deterministic engine strictly guards the core numerical decisions. Prompt injections into the LLM layer cannot alter safe limits or minimum balance thresholds.
- **Evidence Extraction**: Large Language Models are completely stripped of final mathematical authority and isolated merely as interpretation engines.
- **Storage**: User records, evidence logic, and histories are logically isolated in the persistent SQLite layer.

## Known Limitations
- Not currently compliant with PCI-DSS or SOC2 without further infrastructure hardening.
- End-to-end encryption of evidence blobs (receipts/invoices) relies on host OS protections.
