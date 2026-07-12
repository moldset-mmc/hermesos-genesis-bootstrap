# 10_SECRETS_AND_TRUST_MODEL.md
> Secrets and Trust Model for Bootstrap Package
> Generated: 2026-07-11T23:30:00Z

## Core Principles
1. The genesis package contains ZERO secrets
2. Secrets are injected by the owner AFTER package delivery
3. Package trust is established via SHA-256 + pinned commit + release tags
4. Every bootstrap execution is independently verifiable

## Trust Chain
OWNER (Serghei)
  -> TRUSTED GITHUB REPOSITORY (pinned commit or release tag)
    -> VERIFIED PACKAGE (SHA-256 matches manifest)
      -> BOOTSTRAP EXECUTION (package integrity re-verified)
        -> AGENT CREATED (secrets injected by owner)
          -> VALIDATED AGENT (tests pass independently)

## Package Integrity Requirements
- Every release has a checksum manifest (SHA-256 of all files)
- Release tags are annotated
- Package distributed as immutable ZIP with sibling .sha256
- Bootstrap re-verifies all checksums before any write

## Secret Categories

### Bootstrap-required (before Phase 7)
1. OPENROUTER_API_KEY — LLM inference
2. TELEGRAM_BOT_TOKEN_ASSISTANT — Telegram connectivity
3. HKP_AUTHORITY_ROOT path

### Bootstrap-optional (after Phase 14)
- DEEPSEEK_API_KEY, GITHUB_TOKEN, TWILIO_*, etc.

## Secret Injection Mechanism
1. Package provides .env.template with key names and placeholders
2. Owner copies to .env and fills real values
3. Secrets NEVER logged, echoed, or stored in evidence

## Scanning Requirements
- GitHub secret scanning enabled on repository
- Pre-release grep for patterns: 'sk-', 'api_key', 'token', 'password'
- Build-time check: fail if pattern detected in package files
