# Security Policy

RivalScope treats system security and data isolation as foundational priorities. This policy outlines our vulnerability reporting process, tenant isolation guarantees, and security controls.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within RivalScope, please report it via email to `security@rivalscope.org` instead of opening a public GitHub issue.

Please include:
1. Vulnerability description and potential impact.
2. Reproduction steps or proof of concept.
3. Affected components (Backend, MCP Gateway, Auth, API, Frontend).

We acknowledge all reports within 48 hours and coordinate responsible disclosure timelines.

## Core Security Controls

- **Multi-Tenant Scoping**: All database operations and cache lookups are strictly partitioned by `tenant_id`.
- **SSRF Defense**: The MCP Gateway strictly disallows connections to loopback (`127.0.0.1`), link-local (`169.254.169.254`), and private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) unless explicitly allowed in local development.
- **Envelope Encryption**: Secrets, third-party API credentials, and notification channel webhook URLs are encrypted at rest using AES-256-GCM.
- **Prompt Injection Defense**: External web and RSS inputs are untrusted data strings, wrapped in isolated delimiter boundaries, and validated against rigid Pydantic output schemas.
- **Authentication**: JWT with configurable RS256/HS256 algorithms and Role-Based Access Control (`admin`, `analyst`, `viewer`).
