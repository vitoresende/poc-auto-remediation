# Architecture & Work Breakdown Structure (WBS)
## PoC Auto-Remediation Agent (Sentry -> GitHub)

---

## 1. Overview & Context
This Proof of Concept (PoC) implements an end-to-end automated pipeline for triaging, deterministically sanitizing, and autonomously remediating production errors captured by **Sentry**, integrating directly with **GitHub** to open Pull Requests with suggested fixes and unit tests.

The primary goal is to drastically reduce the Mean Time to Resolution (MTTR) of production incidents **without exposing Personally Identifiable Information (PII) or sensitive secrets to external Large Language Models (LLMs)**.

---

## 2. Solution Architecture

### 2.1. Logical Execution Flow
1. **Sentry Alert / Webhook:** Sentry captures an unhandled or logged exception from `dummy-app` and dispatches a webhook (`issue.created` / `error.created`).
2. **Ingestion & Deterministic PII Sanitizer (No-LLM):** A local, deterministic filter strips all PII (CPF, SSN, credit card numbers, emails, passwords, API keys, Bearer tokens) and truncates noisy breadcrumbs before any external AI call.
3. **Orchestrator Agent & LLM Engine:** Receives only the sanitized stack trace and metadata, retrieves surrounding source code from GitHub, and formulates a structured Root Cause Analysis (RCA), code patch, and unit test.
4. **Repo Context Retrieval (GitHub REST API):** Fetches a targeted 50–100 line window around the failing file and line number from the target branch.
5. **GitHub Delivery Engine:** Validates Python AST syntax of the generated patch, creates a standardized branch (`fix/sentry-issue-<id>`), commits the changes, and opens a Pull Request on GitHub triggering GitHub Actions CI.

### 2.2. Core Components

| Component | Primary Responsibility | Technologies / Methods |
| :--- | :--- | :--- |
| **Ingress & Event Handler** | Receive Sentry webhook events (`issue.created`, `error.created`) and extract essential technical context (stack trace, breadcrumbs, tags, exception details). | Python, FastAPI, Webhook Receivers |
| **PII Sanitizer Layer** | Isolated, strictly deterministic module that redacts sensitive data prior to LLM invocation and truncates redundant breadcrumbs. | Compiled Regex, Microsoft Presidio (Local) |
| **Orchestrator Agent & Context Retrieval** | Analyze sanitized logs, query GitHub repository context (adjacent lines and function signatures), and generate RCA, patch, and unit tests. | LangChain / LlamaIndex, LLM API (Structured Outputs) |
| **GitHub Delivery Engine** | Validate syntax (`ast.parse`) of the generated patch, create a dynamic branch, commit fixes, and open a traceable Pull Request with Human-in-the-Loop review markers. | GitHub REST API / PyGithub, Git CLI, GitHub Actions |

---

## 3. Work Breakdown Structure (WBS)

### Package 1: Environment, Infrastructure & Mocks *(Completed)*
| ID | Activity | Description |
| :--- | :--- | :--- |
| **1.1** | **Sentry Sandbox Setup** | Create a free Sentry sandbox organization/project and configure outbound webhooks pointing to the ingestion endpoint. |
| **1.2** | **Target Repository (Dummy App)** | Configure the Python/FastAPI project on GitHub with a GitHub Actions CI pipeline (`.github/workflows/ci.yml`) and 4 intentional bug scenarios with injected PII. |
| **1.3** | **Sentry Payload Fixtures** | Export canonical JSON fixtures of real Sentry events (`fixtures/sentry_*.json`) to enable offline development and deterministic unit testing. |

### Package 2: Deterministic Data Sanitization Module (PII Filter)
| ID | Activity | Description |
| :--- | :--- | :--- |
| **2.1** | **PII Pattern Mapping** | Map all sensitive patterns across Sentry event payloads (`exception`, `frame.vars`, `breadcrumbs`, `request`, `user`, `tags`): credit cards, CPF/SSN, Bearer tokens, passwords, API keys, emails, and phones. |
| **2.2** | **Sanitization Engine** | Build the local sanitization library (zero LLM calls) replacing sensitive values with standardized placeholders (`[MASKED_CPF]`, `[MASKED_CARD]`, `[MASKED_EMAIL]`, `[MASKED_TOKEN]`, `[MASKED_SECRET]`) and truncating noisy breadcrumbs. |
| **2.3** | **Redaction Test Suite** | Create automated tests running against `fixtures/sentry_*.json` to guarantee 0% PII leakage while preserving stack trace structure and line numbers. |

### Package 3: GitHub Integration & Git Operations
| ID | Activity | Description |
| :--- | :--- | :--- |
| **3.1** | **Credentials & Permissions** | Configure a Fine-Grained GitHub Personal Access Token (PAT) scoped strictly to the target repository (`Contents: Read & Write`, `Pull Requests: Read & Write`). |
| **3.2** | **GitHub API Client** | Implement the client module to read source files at specific refs, validate Python syntax via `ast.parse`, create dynamic branches (`fix/sentry-issue-<id>`), commit changes, and open Pull Requests. |

### Package 4: Resolution Agent & Prompt Engineering
| ID | Activity | Description |
| :--- | :--- | :--- |
| **4.1** | **RCA & Patch Prompt** | Design structured-output prompts (Pydantic JSON Schema) returning Root Cause Analysis (RCA), updated file content/patch, and unit tests. |
| **4.2** | **Context Retrieval (Repo Search)** | Implement code window extraction (50 to 100 lines around the failing frame across the call stack) to optimize token consumption. |
| **4.3** | **Remediation Evaluation** | Calibrate fix accuracy by running the agent against the 4 programmed error scenarios in `dummy_app`. |

### Package 5: End-to-End Orchestration & Integration
| ID | Activity | Description |
| :--- | :--- | :--- |
| **5.1** | **Ingestor & Orchestrator Service** | Build the main webhook receiver connecting Ingestion $\rightarrow$ PII Sanitizer $\rightarrow$ Context Retrieval $\rightarrow$ LLM Agent $\rightarrow$ GitHub PR Creation. |
| **5.2** | **Integrated Dry Run** | Execute end-to-end validation in the sandbox environment, verifying processing latency, zero PII leakage, and GitHub Actions CI status on the generated Pull Request. |
| **5.3** | **Documentation & Metrics** | Consolidate technical runbooks, response time metrics, sanitization efficacy rate, and token cost estimates. |
