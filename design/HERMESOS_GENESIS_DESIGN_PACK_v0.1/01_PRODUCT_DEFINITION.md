# 01_PRODUCT_DEFINITION.md
> Product: HermesOS Genesis Bootstrap
> Generated: 2026-07-11T23:30:00Z

## Product Identity
| Field | Value |
|---|---|
| Name | HermesOS Genesis Bootstrap |
| Version | v0.1 |
| Type | Reproducible bootstrap package |
| Target | Clean official Hermes Agent installation |

## Product Purpose
Позволить чистому официальному Hermes Agent (v0.18.x) получить утверждённый
bootstrap package, создать отдельного агента HermesOS, загрузить его identity
и HKP governance, привести совместимый shared runtime к утверждённому
HKP enforcement baseline и доказать готовность через validation.

## Target User
Serghei (owner) — or any authorised operator following published instructions.

## Target Environment
- Hermes Agent v0.18.x installed via pip
- Windows 10/11 or Linux
- Python 3.11+
- Git available for patch application
- Network access to github.com and LLM providers

## Supported Use Case
1. Fresh Hermes Agent installation on a new machine
2. Recovery/migration of HermesOS identity and governance to new environment

## Non-Goals (v0.1)
- Full HermesOS runtime environment with all project-specific integrations
- MMC Auto Center or other domain-specific configurations
- Operating Cycle implementation
- Knowledge DNA implementation
- Full 12-stage Bootstrap from Foundation v1.0
- Multi-agent bootstrap (only HermesOS, not MMC team)

## Trust Assumptions
1. Owner controls the trusted GitHub repository
2. Package is delivered from pinned commit/release
3. Package integrity verified via SHA-256 before execution
4. Secrets are injected by owner, never shipped in package
5. Hermes Agent upstream is authentic (pip install)

## Success Criteria
1. Clean Hermes Agent + Genesis Bootstrap -> HermesOS profile created
2. HermesOS starts with identity loaded
3. HKP governance authority block injects into system prompt
4. Runtime enforcement (deny-by-default) is active
5. All execution contexts behave as specified
6. Validation suite passes
7. Evidence package produced

## v0.1 Scope
INHERIT: Foundation architecture hierarchy, 7 Genesis principles, Constitution identity
FORMALIZE: 6 Operational Decision Gates, ExecutionContext model
EXTEND: Security Model (deny-by-default, credential broker)
DEFER: Operating Cycle, Knowledge DNA, Full Registry instantiation, 12-stage Bootstrap

## PRODUCT vs CURRENT LOCAL INSTALLATION
The product is NOT a backup of C:\Users\molds\...
The product is NOT a copy of current working HermesOS.
The product is a REPRODUCIBLE package that can recreate HermesOS on any compatible host.
