# CAPITAL INDEX 2026 — Production-Grade Architecture

**Версия:** 2.2  
**Формат:** единый production-grade архитектурный документ  
**Дата:** 2026-05-25  
**Владелец:** Александр Тюрин  
**Организация:** fixer.guru / integrayachtsuae.com  
**Цель:** central intelligence layer поверх Google Workspace, GCP/Firebase проектов, Obsidian Vault и AI-контекстов.

---

## 1. Назначение системы

CAPITAL INDEX 2026 — это центральный intelligence layer над всеми бизнесами, файлами, CRM, Google Drive, Gmail, Sheets, Docs, Vault и AI-контекстами.

Система автоматически:

1. Отслеживает изменения во всех ключевых источниках.
2. Классифицирует данные по бизнесам, проектам, людям, рискам, деньгам и уровню доступа.
3. Извлекает сущности, связи, дедлайны, финансовые сигналы и операционные факты.
4. Строит cross-project knowledge graph.
5. Находит дубликаты, версии, evidence copies и связанные документы.
6. Обновляет Obsidian Vault как читаемую проекцию.
7. Генерирует универсальные AI-контексты для одного или нескольких подключённых AI-исполнителей одновременно.
8. Поддерживает audit trail, security policy, review queue и cost control.
9. Работает поверх всех существующих GCP/Firebase-проектов как мета-уровень.

CAPITAL INDEX не является одним Apps Script, одной таблицей, одним Vault или одним AI context file. Это production-grade control plane + event bus + AI processing fabric + knowledge graph + projection system.

---

## 2. Текущая реальная конфигурация

### 2.1 Google Workspace

- Домен: `integrayachtsuae.com`
- План: Google Workspace Business Plus
- Доступно:
  - Google Drive 5 TB
  - Google Docs / Sheets / Gmail
  - Drive Labels
  - Google Vault
  - Apps Script
  - Workspace API / Workspace Events API
  - Gemini for Workspace в админке

### 2.2 Google Cloud / Firebase

Существующие GCP/Firebase проекты остаются отдельными бизнес- или продукт-инфраструктурами. CAPITAL INDEX создаётся как отдельный мета-проект.

Существующие проекты:

| Project ID | Назначение |
|---|---|
| `integra-motors-493118` | Integra Motors infrastructure |
| `kvartal-dev` | KVARTAL Dev |
| `gen-lang-client-0953531299` | Gemini / ContentMaster |
| `trust-dev-7bd6f` | 100trust-dev |
| `content-factory-492423` | Content Factory |
| `freshcuisine` | Fresh Cuisine |

Firebase-проекты подключаются через registry и не смешиваются с control plane.

### 2.3 Существующие компоненты

- Apps Script `CAPITAL INDEX Б2`
- `CAPITAL_INDEX_2026` Sheet
- `AI_Bridge_Log_Spreadsheet`
- `AI_TODAY_CONTEXT`
- `AI_WINDOW_CONTEXT`
- Obsidian Vault в Google Drive
- PARA-структура Vault
- Базовый Gemini-анализ файлов

---

## 3. Главные архитектурные решения

### 3.1 Новый GCP-проект

Создать отдельный GCP project:

```text
capital-index-2026
```

Роль проекта:

```text
Central control plane
Central event bus
Central audit layer
Central AI processing layer
Central knowledge graph
Central projection publisher
Central approval layer
Central observability layer
```

### 3.2 Source of truth

```text
Firestore = operational source of truth
BigQuery = audit, history, analytics
Google Drive = source files
Obsidian Vault = readable projection
Google Sheets = human dashboard
AI context files = compressed AI-facing projection
```

Не допускается:

```text
Vault как база данных
Sheets как база данных
Apps Script как backend очереди
AI как источник истины
```

---

## 4. Высокоуровневая архитектура

```text
┌────────────────────────────────────────────────────────────┐
│                    SOURCE LAYER                             │
│ Drive | Gmail | Sheets | Docs | Calendar | Firebase | GCP   │
└───────────────────────┬────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────────┐
│                    EVENT LAYER                              │
│ Workspace Events API | Drive API Watch | Gmail Push          │
│ Sheets Bridge | Scheduler | Pub/Sub                         │
└───────────────────────┬────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────────┐
│                    CONTROL PLANE                            │
│ Project Registry | Source Registry | Policy Engine          │
│ Identity Map | Job Orchestrator | State Machine             │
└───────────────────────┬────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────────┐
│                    AI PROCESSING FABRIC                     │
│ Classifier | Extractor | OCR | Chunker | Embedder           │
│ Entity Extractor | Relationship Extractor | Dedupe          │
│ Graph Builder | Validator | Scoring Engine                  │
└───────────────────────┬────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                            │
│ Firestore | BigQuery | Cloud Storage | Secret Manager        │
└───────────────────────┬────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────────┐
│                    PROJECTION LAYER                         │
│ Vault Writer | Context Publisher | Sheets Dashboard          │
│ Daily Briefing | Telegram / Email / Admin Approval           │
└───────────────────────┬────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────────┐
│                    CONSUMPTION LAYER                        │
│ AI Gateway | Claude | Gemini | ChatGPT | Agents | Dashboards   │
└────────────────────────────────────────────────────────────┘
```

---

## 5. Event ingestion

### 5.1 Drive ingestion

Primary:

```text
Workspace Events API Drive subscriptions → Cloud Pub/Sub
```

Fallback:

```text
Drive API changes.watch + changes.list
```

Historical / reconciliation:

```text
Drive Activity API
scheduled Drive inventory scan
```

Drive ingestion не строится на одном механизме. Workspace Events API используется как primary, но Phase 1 не начинается без POC.

### 5.2 Обязательный POC Drive events

```text
POC-DRIVE-EVENTS-001

Goal:
  подтвердить, что изменения в одной тестовой Drive-папке доходят до Pub/Sub.

Steps:
  1. Создать тестовую папку CAPITAL_INDEX_EVENT_TEST.
  2. Создать Workspace Events API subscription на эту папку.
  3. Настроить Pub/Sub topic capital.events.drive.test.
  4. Создать файл.
  5. Изменить файл.
  6. Переместить файл.
  7. Удалить файл.
  8. Проверить payload, latency, resource_id, event_type.
  9. Проверить expiration / renewal subscription.
  10. Задокументировать gaps.

Pass criteria:
  create/update/move/delete события получены
  или зафиксирован fallback через Drive changes API.

Fail behavior:
  Drive API changes.watch становится primary.
  Workspace Events API остаётся optional.
```

### 5.3 Gmail ingestion

```text
Gmail Push Notifications → Pub/Sub
```

Используется для:

```text
new message
label change
thread update
attachment detection
client communication signals
```

### 5.4 Sheets ingestion

Apps Script onChange не является единственным источником истины.

Tier 1 — critical sheets:

```text
CRM
Finance
Suppliers
Leads
Operations
```

Mechanism:

```text
Apps Script installable trigger
→ Pub/Sub bridge endpoint
→ sheet/tab/range hash
→ Firestore update
```

Tier 2 — normal sheets:

```text
Drive modifiedTime event
→ delayed fetch
→ sheet hash comparison
→ update only if content changed
```

Tier 3 — archive sheets:

```text
scheduled reconciliation only
```

Hash:

```text
sheet_hash = hash(
  spreadsheet_id
  + sheet_id
  + used_range_values
  + headers
  + row_count
  + column_count
)
```

### 5.5 Calendar ingestion

```text
Calendar push notifications if reliable for selected calendars
otherwise scheduled sync
```

---

## 6. Pub/Sub topology

### 6.1 Event topics

```text
capital.events.drive
capital.events.gmail
capital.events.sheets
capital.events.calendar
capital.events.firebase
capital.events.gcp
capital.events.manual
```

### 6.2 Job topics

```text
capital.jobs.classification
capital.jobs.extraction
capital.jobs.ocr
capital.jobs.chunking
capital.jobs.embedding
capital.jobs.entity_extraction
capital.jobs.relationship_extraction
capital.jobs.dedupe
capital.jobs.graph
capital.jobs.validation
capital.jobs.projection
capital.jobs.scoring
capital.jobs.review
```

### 6.3 Priority queues

```text
capital.jobs.priority.critical
capital.jobs.priority.normal
capital.jobs.priority.backfill
capital.jobs.priority.low
```

Priority order:

```text
1. security / policy jobs
2. active project changes
3. critical CRM / finance sheets
4. normal Drive events
5. backfill
6. archive processing
```

### 6.4 Dead-letter topics

```text
capital.dlq
capital.audit
capital.cost
```

DLQ policy:

```text
max_delivery_attempts = 5
dead_letter_topic = capital.dlq
```

---

## 7. Control Plane

Control Plane отвечает за правила, маршрутизацию и управление состояниями.

Компоненты:

```text
project-registry
source-registry
policy-engine
identity-resolver
job-orchestrator
state-machine
approval-router
cost-controller
audit-writer
```

Control Plane решает:

```text
что индексировать
что не индексировать
какой namespace использовать
какой sensitivity class применить
какой AI-модели разрешено читать файл
можно ли делать embedding
можно ли публиковать в Vault
можно ли включать в AI context
нужно ли manual approval
какой retry policy применить
```

---

## 8. Project Registry

Firestore collection:

```text
/project_registry/{project_id}
```

Пример:

```json
{
  "project_id": "integra_motors",
  "display_name": "Integra Motors",
  "type": "business",
  "status": "active",
  "gcp_project_id": "integra-motors-493118",
  "firebase_project_ids": ["integra-motors"],
  "drive_root_folder_ids": ["..."],
  "canonical_sheets": {
    "crm": "...",
    "suppliers": "...",
    "finance": "..."
  },
  "vault_path": "01-Projects/Integra-Motors/",
  "sensitivity_default": "BUSINESS_CONFIDENTIAL",
  "owner": "alexander",
  "priority": "high",
  "enabled": true
}
```

Назначение:

```text
единая карта всех бизнесов
единая карта всех GCP/Firebase связей
единая карта Drive/Sheets/Vault источников
единый namespace для knowledge graph
единая cost attribution
```

---

## 9. Source Registry

Firestore collection:

```text
/source_registry/{source_id}
```

Типы источников:

```text
google_drive_folder
google_drive_file
google_sheet
google_doc
gmail_label
calendar
firebase_project
gcp_project
vault_folder
manual_input
telegram_input
```

Пример:

```json
{
  "source_id": "im_crm_v5",
  "source_type": "google_sheet",
  "project_id": "integra_motors",
  "business_area": "integra_motors",
  "drive_file_id": "...",
  "canonical": true,
  "data_domain": "crm",
  "sensitivity_class": "BUSINESS_CONFIDENTIAL",
  "indexing_enabled": true,
  "embedding_allowed": true,
  "ai_summary_allowed": true,
  "vault_publish_allowed": true,
  "last_seen_at": "2026-05-25T00:00:00Z"
}
```

---

## 10. Data classification

### 10.1 Classes

```text
PUBLIC_INTERNAL
BUSINESS_CONFIDENTIAL
CLIENT_PRIVILEGED
LEGAL_PRIVILEGED
FINANCIAL_RESTRICTED
SECRET
DO_NOT_INDEX
UNCLASSIFIED_REVIEW_REQUIRED
```

### 10.2 Access matrix

| Class | Read metadata | Read content | AI summary | Embedding | Cross-project graph | Vault publish | AI context |
|---|---:|---:|---:|---:|---:|---:|---:|
| PUBLIC_INTERNAL | yes | yes | yes | yes | yes | yes | yes |
| BUSINESS_CONFIDENTIAL | yes | yes | Vertex-only | yes | yes | yes | yes |
| CLIENT_PRIVILEGED | yes | approval | summary only | no by default | no by default | summary only | limited |
| LEGAL_PRIVILEGED | yes | approval | approval | no | no | no | no |
| FINANCIAL_RESTRICTED | yes | approval | approval | no | restricted | no / summary only | limited |
| SECRET | yes | no | no | no | no | no | no |
| DO_NOT_INDEX | no | no | no | no | no | no | no |
| UNCLASSIFIED_REVIEW_REQUIRED | yes | no | no | no | no | no | no |

### 10.3 Definition of limited AI context

`limited` означает:

```text
только metadata:
  file name
  project
  date
  status
  source id
  sensitivity class

запрещено:
  content summary
  extracted entities
  extracted relationships
  money details
  legal facts
  client-private facts

AI_EXECUTIVE_CONTEXT:
  не включает restricted details

Доступ:
  только по конкретному запросу
  только с approval_id
  approval TTL = 30 минут
```

---

## 11. Classification strategy

Drive Labels не являются primary mechanism для всех файлов.

Priority order:

```text
1. Explicit manual override
2. Drive Label
3. Folder-based policy
4. Source Registry policy
5. Metadata-only AI classification
6. Content AI classification, only if allowed
7. Review queue
```

### 11.1 Folder-based policy

Primary classification layer.

Reason:

```text
20–50 folder policies покрывают большую часть данных быстрее,
чем ручная разметка 1554+ файлов.
```

Firestore:

```json
{
  "folder_id": "string",
  "policy_name": "Legal folders",
  "sensitivity_class": "LEGAL_PRIVILEGED",
  "inherit_to_children": true,
  "allowed_actions": ["read_metadata"],
  "denied_actions": ["read_content", "embed", "publish_to_context"],
  "approval_required_for": ["read_content", "summary"]
}
```

### 11.2 Drive Labels

Use case:

```text
exceptions and overrides
```

Example:

```text
public folder contains one financial file
→ Drive Label FINANCIAL_RESTRICTED overrides folder policy
```

---

## 12. Policy Engine

Policy Engine принимает решение до чтения содержимого.

Input:

```text
file metadata
folder policy
Drive Labels
source registry
project registry
user ownership
mime type
filename
path
manual overrides
existing classification
```

Output:

```json
{
  "decision": "allow|deny|review_required",
  "sensitivity_class": "BUSINESS_CONFIDENTIAL",
  "allowed_actions": [
    "extract_text",
    "summarize",
    "embed",
    "publish_to_vault",
    "include_in_ai_context"
  ],
  "denied_actions": [],
  "requires_approval": false,
  "reason": "folder_policy + drive_label"
}
```

Rule:

```text
AI content read is forbidden until policy engine grants read_content.
```

---

## 13. Worker topology

Production workers:

```text
event-ingestor
metadata-loader
policy-engine-worker
classifier-worker
content-extractor
document-ai-worker
chunker-worker
embedder-worker
entity-extractor
relationship-extractor
dedupe-clusterer
graph-builder
validator-worker
vault-writer
context-publisher
sheets-dashboard-writer
review-orchestrator
ai-gateway
scoring-engine
cost-controller
audit-writer
dlq-reprocessor
```

---

## 14. Worker responsibilities

### 14.1 `event-ingestor`

```text
получает Pub/Sub события
нормализует payload
создаёт event_log
создаёт job
проверяет idempotency
передаёт в metadata-loader
```

### 14.2 `metadata-loader`

```text
читает Drive/Gmail/Sheets metadata
определяет owner, path, mime type, revision
связывает ресурс с source_registry
обновляет /files
```

### 14.3 `policy-engine-worker`

```text
применяет Drive Labels
применяет folder policy
применяет source/project registry
решает allowed_actions
блокирует SECRET / DO_NOT_INDEX
отправляет спорное в review_queue
```

### 14.4 `classifier-worker`

```text
классифицирует тип документа
определяет project_id
определяет business_area
определяет sensitivity_class если нет label/policy
создаёт classification artifact
```

### 14.5 `content-extractor`

```text
извлекает текст из Google Docs
извлекает данные из Sheets
извлекает структуру из Slides
извлекает Gmail body/attachments
передаёт PDF/scans в document-ai-worker
```

### 14.6 `document-ai-worker`

```text
OCR
layout parsing
tables extraction
forms extraction
contract/invoice parsing
```

### 14.7 `chunker-worker`

```text
разбивает документ на chunks
проставляет semantic boundaries
сохраняет chunk order
сохраняет source offsets
```

### 14.8 `embedder-worker`

```text
создаёт embeddings
записывает vectors
проверяет embedding_allowed
не работает с legal/secret/financial без approval
```

### 14.9 `entity-extractor`

```text
люди
компании
клиенты
машины
суммы
валюты
счета
даты
дедлайны
риски
обязательства
поставщики
документы
```

### 14.10 `relationship-extractor`

```text
project ↔ project
person ↔ project
file ↔ project
company ↔ project
vehicle ↔ deal
invoice ↔ client
contract ↔ obligation
risk ↔ project
cashflow ↔ business
```

### 14.11 `dedupe-clusterer`

```text
exact duplicate
near duplicate
version family
template reuse
evidence copy
canonical assignment
archive suggestion
```

### 14.12 `graph-builder`

```text
обновляет entities
обновляет relationships
обновляет project graph
обновляет people graph
обновляет business graph
```

### 14.13 `validator-worker`

```text
валидирует JSON schema
проверяет confidence
проверяет policy violations
проверяет hallucination risk
проверяет source attribution
```

### 14.14 `vault-writer`

```text
обновляет master-index.md
обновляет project overview
обновляет project-links.md
пишет только protected blocks
не трогает manual notes
соблюдает manual_override
```

### 14.15 `context-publisher`

```text
генерирует AI_EXECUTIVE_CONTEXT.md
генерирует AI_PROJECT_INDEX.md
генерирует AI_RELATIONSHIP_GRAPH.md
генерирует AI_RECENT_CHANGES_7D.md
генерирует AI_REVIEW_QUEUE.md
```

### 14.16 `review-orchestrator`

```text
создаёт review tasks
получает approval/reject
пишет audit
разблокирует jobs
```

### 14.17 `scoring-engine`

```text
приоритизация проектов
cash impact
time to value
risk
execution cost
dependencies
strategic leverage
```

### 14.18 `cost-controller`

```text
считает AI calls
останавливает bulk jobs при лимитах
пишет cost_log
создаёт alerts
управляет circuit breaker
```

### 14.19 `audit-writer`

```text
пишет security_audit
пишет processing_audit
пишет ai_call_audit
пишет projection_audit
```

---

## 15. Job Orchestrator

Firestore collection:

```text
/jobs/{job_id}
```

States:

```text
received
metadata_loaded
policy_checked
classified
content_allowed
extracted
chunked
embedded
entities_extracted
relationships_extracted
dedupe_checked
graph_updated
validated
projected
completed
blocked
waiting_approval
failed
dead_lettered
```

Example:

```json
{
  "job_id": "job_...",
  "trace_id": "trace_...",
  "source_event_id": "event_...",
  "resource_id": "drive_file_id",
  "revision_id": "123",
  "project_id": "integra_motors",
  "current_stage": "entity_extraction",
  "status": "running",
  "attempts": {
    "classification": 1,
    "extraction": 1,
    "entity_extraction": 2
  },
  "last_successful_stage": "chunked",
  "locked_by": "entity-extractor-01",
  "lease_expires_at": "2026-05-25T10:00:00Z",
  "created_at": "2026-05-25T09:00:00Z",
  "updated_at": "2026-05-25T09:15:00Z"
}
```

---

## 16. Concurrency Control

### 16.1 File-level optimistic locking

Все записи в `/files/{file_id}` обновляются через Firestore transaction.

Transaction rule:

```text
read /files/{file_id}
compare latest_revision_id
compare processing_version
update only if expected values match
```

Если revision изменился во время обработки:

```text
current job → stale
new revision → new job
old artifacts → retained, marked superseded
```

### 16.2 Job leases

```json
{
  "locked_by": "worker_instance_id",
  "lease_started_at": "timestamp",
  "lease_expires_at": "timestamp",
  "lease_renewal_count": 0
}
```

Rules:

```text
lease_duration = 5 minutes
renew_every = 60 seconds
max_lease_duration = 60 minutes
expired lease → job can be claimed by another worker
AI long call → heartbeat required
```

### 16.3 Stage idempotency

```text
stage_idempotency_key =
  job_id + stage_name + file_id + revision_id + schema_version + prompt_version
```

Worker перед записью проверяет, есть ли уже successful artifact с таким ключом.

### 16.4 Vault writer concurrency

Перед записью в Vault:

```text
1. read current Drive file content
2. calculate current_content_hash
3. compare with last_seen_vault_hash
4. if changed by user → abort
5. create projection_conflict review item
6. save proposed projection in Firestore
```

---

## 17. Backpressure and rate limiting

### 17.1 Token bucket

Firestore:

```json
{
  "ai_calls_per_minute_limit": 100,
  "ai_calls_current_window": 0,
  "document_ai_pages_per_hour_limit": 500,
  "embedding_calls_per_minute_limit": 300,
  "backfill_concurrency": 5,
  "interactive_concurrency": 20,
  "circuit_state": "closed",
  "cooldown_until": null
}
```

### 17.2 Circuit breaker states

```text
closed:
  normal operation

half_open:
  limited traffic after cooldown

open:
  block expensive AI calls
  allow metadata-only processing
  allow security processing
  pause backfill
```

Triggers:

```text
429 from AI API repeated 3 times in 5 minutes
daily cost > 80%
DLQ count > threshold
Document AI quota exceeded
Firestore write error rate > threshold
```

---

## 18. Firestore schema

Core collections:

```text
/project_registry
/source_registry
/folder_policies
/files
/file_revisions
/sheet_snapshots
/artifacts
/chunks
/entities
/relationships
/projects
/people
/businesses
/jobs
/events
/review_queue
/approval_decisions
/security_policies
/dedupe_clusters
/projections
/ai_contexts
/decision_log
/cost_state
/system_config
/migration_runs
/migration_errors
/legacy_artifacts
```

### 18.1 `/files/{file_id}`

```json
{
  "file_id": "string",
  "source_type": "drive",
  "drive_file_id": "string",
  "name": "string",
  "mime_type": "string",
  "url": "string",
  "parents": ["string"],
  "owner": "email",
  "created_at": "timestamp",
  "modified_at": "timestamp",
  "last_seen_at": "timestamp",

  "project_id": "string|null",
  "business_area": "string|null",
  "source_id": "string|null",

  "sensitivity_class": "BUSINESS_CONFIDENTIAL",
  "classification_source": "drive_label|folder_policy|ai|manual",
  "classification_confidence": 0.0,

  "indexing_status": "active|blocked|archived|error",
  "latest_revision_id": "string",
  "sha256": "string|null",

  "cluster_id": "string|null",
  "is_canonical": true,

  "created_by_system": false,
  "manual_override": false,
  "processing_version": 1
}
```

### 18.2 `/file_revisions/{revision_key}`

```json
{
  "revision_key": "file_id:revision_id",
  "file_id": "string",
  "revision_id": "string",
  "modified_at": "timestamp",
  "hash": "string|null",
  "processed": true,
  "artifact_ids": ["string"],
  "job_ids": ["string"],
  "superseded": false
}
```

### 18.3 `/artifacts/{artifact_id}`

```json
{
  "artifact_id": "string",
  "file_id": "string",
  "revision_id": "string",
  "artifact_type": "summary|classification|ocr|entity_extraction|relationship_extraction",
  "model": "string",
  "model_version": "string",
  "schema_name": "entity_extraction",
  "schema_version": 4,
  "prompt_id": "entity_extractor",
  "prompt_version": 7,
  "confidence": 0.0,
  "payload": {},
  "source_offsets": [],
  "created_at": "timestamp",
  "policy_snapshot_id": "string",
  "staleness": "fresh|stale_schema|stale_prompt|stale_model"
}
```

### 18.4 `/chunks/{chunk_id}`

```json
{
  "chunk_id": "string",
  "file_id": "string",
  "revision_id": "string",
  "chunk_index": 0,
  "text": "string",
  "token_count": 0,
  "embedding_ref": "string|null",
  "sensitivity_class": "BUSINESS_CONFIDENTIAL",
  "source_offsets": {
    "start": 0,
    "end": 0
  },
  "language": "ru|en|ar|mixed"
}
```

### 18.5 `/entities/{entity_id}`

```json
{
  "entity_id": "string",
  "entity_type": "person|company|vehicle|contract|invoice|money|deadline|risk|asset|supplier|client",
  "canonical_name": "string",
  "aliases": ["string"],
  "properties": {},
  "linked_files": ["string"],
  "linked_projects": ["string"],
  "linked_businesses": ["string"],
  "confidence": 0.0,
  "last_seen_at": "timestamp"
}
```

### 18.6 `/relationships/{relationship_id}`

```json
{
  "relationship_id": "string",
  "from_type": "project",
  "from_id": "string",
  "to_type": "entity",
  "to_id": "string",
  "relationship_type": "depends_on|references|owns|owes|client_of|supplier_of|same_vehicle|same_cashflow|legal_link",
  "strength": 0.0,
  "confidence": 0.0,
  "evidence_file_ids": ["string"],
  "evidence_artifact_ids": ["string"],
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

### 18.7 `/dedupe_clusters/{cluster_id}`

```json
{
  "cluster_id": "string",
  "cluster_type": "exact_duplicate|near_duplicate|version_family|template_reuse|evidence_copy",
  "canonical_file_id": "string",
  "member_file_ids": ["string"],
  "confidence": 0.0,
  "action": "none|archive_suggested|review_required",
  "created_at": "timestamp"
}
```

### 18.8 `/review_queue/{review_id}`

```json
{
  "review_id": "string",
  "review_type": "classification|security|dedupe|projection_conflict|low_confidence|policy_violation",
  "resource_type": "file|project|relationship|projection",
  "resource_id": "string",
  "reason": "string",
  "proposed_action": "string",
  "risk_level": "low|medium|high|critical",
  "status": "open|approved|rejected|ignored",
  "created_at": "timestamp",
  "resolved_at": "timestamp|null",
  "resolved_by": "string|null"
}
```

---

## 19. BigQuery schema

Dataset:

```text
capital_index
```

Tables:

```text
event_log
job_history
file_revision_history
ai_call_log
security_audit
policy_decisions
entity_history
relationship_history
dedupe_history
projection_history
review_history
cost_log
error_log
daily_snapshots
project_activity
business_activity
processing_stats
```

Partitioning:

```text
partition by DATE(timestamp)
cluster by project_id, source_type, sensitivity_class
```

BigQuery используется для:

```text
расследований
аналитики
стоимости
истории изменений
audit trail
latency/error reports
project activity reports
stale data reports
vector analytics
```

---

## 20. Vector backend strategy

Firestore vector search используется для operational-dedupe и небольшого semantic search. BigQuery vector search используется для аналитики и больших исторических выборок. Vertex AI Vector Search подключается при росте.

Firestore:

```text
operational dedupe
active files
small-scale top-k similarity
```

BigQuery:

```text
historical similarity analysis
large analytical vector queries
batch graph enrichment
```

Vertex AI Vector Search:

```text
large-scale low-latency retrieval
Phase 7 or when needed
```

Firestore config:

```json
{
  "active_backend": "firestore",
  "allowed_backends": ["firestore", "bigquery", "vertex_vector_search"],
  "firestore": {
    "max_dimensions": 2048,
    "max_result_count": 1000,
    "usage": "operational_dedupe_and_small_scale_semantic_search"
  },
  "bigquery": {
    "usage": "analytics_vector_search_and_large_scale_history"
  },
  "vertex_vector_search": {
    "usage": "large_scale_low_latency_retrieval",
    "enabled": false
  }
}
```

Migration trigger:

```text
If vector_count > 100000
or avg_vector_query_latency > 1500ms
or Firestore query limitations block required filters
then enable BigQuery/Vertex backend migration plan.
```

---

## 21. Cloud Storage

Buckets:

```text
capital-index-raw-cache
capital-index-exports
capital-index-backups
capital-index-prompts
capital-index-migrations
```

### 21.1 `capital-index-raw-cache`

```text
временное хранение файлов для Document AI
TTL 7 дней
шифрование включено
доступ только document-ai-worker
```

### 21.2 `capital-index-exports`

```text
экспорт AI context snapshots
экспорт graph snapshots
экспорт dashboard data
```

### 21.3 `capital-index-backups`

```text
Firestore export
BigQuery scheduled export
Vault projection backup
pre-write Vault backups
```

### 21.4 `capital-index-prompts`

```text
versioned prompt templates
prompt changelog
prompt test fixtures
```

### 21.5 `capital-index-migrations`

```text
schema migration scripts
artifact migration scripts
data repair jobs
```

---

## 22. Secret Manager

Secrets:

```text
gemini-api-key
telegram-bot-token
workspace-oauth-client
external-api-keys
service-config
```

Forbidden:

```text
секреты в Apps Script
секреты в GitHub
секреты в Firestore
секреты в Vault
секреты в Google Sheets
```

---

## 23. AI Layer

### 23.1 Model routing

Model IDs не хардкодятся в worker code.

Firestore config:

```text
/system_config/model_routing
```

Example:

```json
{
  "fast_classifier": "configurable_model_id",
  "deep_extractor": "configurable_model_id",
  "embedding_model": "configurable_model_id",
  "long_context_model": "configurable_model_id"
}
```

Routing:

```text
fast_classification:
  Gemini Flash / Flash Lite

deep_extraction:
  Gemini Pro

long_context_synthesis:
  long-context Gemini model

embeddings:
  Gemini Embedding multimodal

ocr_layout:
  Document AI Enterprise OCR / Layout Parser

strategic reasoning:
  через AI Gateway: Claude / Gemini / ChatGPT / Vertex Model Garden / локальные или внешние agent runtimes, по policy и routing rules
```

### 23.2 Prompt contracts

Каждый AI worker имеет:

```text
input schema
output schema
policy constraints
allowed sensitivity classes
max token budget
confidence rules
fallback behavior
target_languages
preserve_original_names
```

Multilingual requirement:

```json
{
  "target_languages": ["ru", "en", "ar"],
  "preserve_original_names": true,
  "do_not_translate_legal_names": true,
  "extract_aliases": true
}
```

### 23.3 JSON validation

If JSON invalid:

```text
retry with repair prompt
if still invalid → review_queue
```

---

## 24. Schema and prompt versioning

### 24.1 `/system_config/schemas/{schema_name}`

```json
{
  "schema_name": "entity_extraction",
  "current_version": 4,
  "effective_from": "2026-05-25T00:00:00Z",
  "json_schema": {},
  "migration_required_from": [1, 2],
  "migration_script_uri": "gs://capital-index-migrations/entity_v3_to_v4.py"
}
```

### 24.2 `/system_config/prompts/{prompt_id}`

```json
{
  "prompt_id": "entity_extractor",
  "current_version": 7,
  "schema_name": "entity_extraction",
  "schema_version": 4,
  "template_uri": "gs://capital-index-prompts/entity_extractor_v7.txt",
  "changelog": "Added multilingual entity preservation and evidence offsets",
  "active": true
}
```

### 24.3 Artifact reprocessing

```text
if artifact.schema_version < current_schema_version:
  mark stale_schema
  schedule reprocessing by priority

if artifact.prompt_version < current_prompt_version:
  mark stale_prompt
  reprocess only if projection depends on it

old artifacts are retained, not deleted.
```

---

## 25. Knowledge Graph

Graph состоит из:

```text
businesses
projects
people
companies
clients
suppliers
vehicles
contracts
invoices
documents
cashflows
deadlines
risks
decisions
```

Relationships:

```text
project_has_file
project_has_person
project_has_client
project_has_supplier
project_has_vehicle
project_has_contract
project_has_invoice
project_has_risk
project_depends_on_project
person_controls_project
company_related_to_project
file_references_entity
invoice_belongs_to_client
contract_creates_obligation
cashflow_affects_business
```

Storage:

```text
Phase 1–6:
  Firestore operational graph
  BigQuery history / analytics

Phase 7:
  consider Neo4j / graph database only if query complexity requires it.
```

Graph DB is not required before the graph query workload proves the need.

---

## 26. Dedupe and canonical clustering

No automatic deletion.

Cluster types:

```text
exact_duplicate
near_duplicate
version_family
template_reuse
evidence_copy
```

Logic:

```text
1. Compare hash.
2. Compare filename similarity.
3. Compare modified date.
4. Compare embeddings if allowed.
5. Compare extracted entities.
6. Determine cluster_type.
7. Assign canonical file.
8. Mark others as non-canonical.
9. Send disputed cases to review_queue.
```

Allowed action:

```text
archive_suggested
```

Forbidden action:

```text
automatic deletion
```

---

## 27. Vault projection

Vault is projection only.

Generated files:

```text
AI_EXECUTIVE_CONTEXT.md
AI_PROJECT_INDEX.md
AI_RELATIONSHIP_GRAPH.md
AI_RECENT_CHANGES_7D.md
AI_REVIEW_QUEUE.md
AI_STALE_ZONES.md
AI_COST_AND_ERRORS.md

00-INDEX/master-index.md
00-INDEX/project-links.md
00-INDEX/people-index.md
00-INDEX/company-index.md
00-INDEX/risk-index.md

01-Projects/{project_name}/00-overview.md
01-Projects/{project_name}/recent-changes.md
01-Projects/{project_name}/linked-files.md
01-Projects/{project_name}/risks.md
```

### 27.1 Frontmatter standard

```yaml
---
generated_by: capital-index
projection_type: project_overview
projection_version: 3
project_id: integra_motors
source_hash: abc123
last_seen_vault_hash: def456
last_generated_at: 2026-05-25T10:00:00Z

manual_override: false
locked_sections: []
---
```

### 27.2 Protected blocks

```markdown
<!-- CAPITAL_INDEX:START:auto_summary:v3 -->
Generated content
<!-- CAPITAL_INDEX:END:auto_summary:v3 -->
```

### 27.3 Marker failure

If END marker missing:

```text
do not write
create projection_conflict
backup current file
store proposed version
request review
```

### 27.4 Backup before write

Before every Vault write:

```text
copy current file to capital-index-backups/vault/
include file_id, timestamp, source_hash
TTL = 30 days
```

Restore command:

```text
/restore <projection_id>
```

---

## 28. Manual override conflict resolution

Conflict scenarios:

```text
manual_override = true
source_hash changed unexpectedly
protected block missing
Vault file manually renamed
project folder moved
policy now denies publish
user edited generated block directly
```

Workflow:

```text
1. Create projection_conflict in review_queue.
2. Save current Vault version.
3. Save proposed generated version.
4. Notify through Telegram / Email / Dashboard.
5. User chooses:
   - Keep manual
   - Re-generate
   - Merge
   - Show diff
6. If Merge:
   - Gemini Pro creates 3-way merge.
   - User confirms merged version.
   - manual_override can be reset to false.
```

---

## 29. Universal AI consumption layer

CAPITAL INDEX не должен быть привязан к Claude, Gemini, ChatGPT или любому одному управляющему AI. Система публикует контекст в универсальном формате и подключает один или несколько AI-исполнителей через единый AI Gateway.

Цель слоя:

```text
1. Подключать одного AI-исполнителя.
2. Подключать несколько AI-исполнителей одновременно.
3. Давать разным AI разные роли.
4. Контролировать, какой AI видит какие данные.
5. Логировать все запросы, ответы, действия и использованные контексты.
6. Позволять менять AI-провайдера без изменения source of truth.
```

### 29.1 AI Gateway

AI Gateway — единая точка подключения управляющих и исполнительных AI.

Компонент:

```text
ai-gateway
```

Функции:

```text
model/provider routing
context packaging
tool permission control
policy enforcement
multi-agent session orchestration
response logging
cost tracking
audit trail
fallback routing
```

AI Gateway не является source of truth. Он читает только разрешённые projections, Firestore graph, review queue и context bundles.

### 29.2 Supported AI provider types

```text
anthropic_claude
google_gemini
openai_chatgpt
vertex_model_garden
custom_http_agent
local_agent_runtime
internal_gcp_agent
manual_human_operator
```

### 29.3 AI provider registry

Firestore collection:

```text
/ai_providers/{provider_id}
```

Example:

```json
{
  "provider_id": "claude_primary",
  "provider_type": "anthropic_claude",
  "display_name": "Claude Primary Reasoning Agent",
  "enabled": true,
  "roles": ["strategy", "audit", "context_reasoning"],
  "allowed_context_classes": [
    "PUBLIC_INTERNAL",
    "BUSINESS_CONFIDENTIAL"
  ],
  "denied_context_classes": [
    "SECRET",
    "DO_NOT_INDEX",
    "LEGAL_PRIVILEGED",
    "FINANCIAL_RESTRICTED"
  ],
  "max_context_tokens": 120000,
  "supports_files": true,
  "supports_tools": false,
  "supports_streaming": true,
  "cost_profile": "external_paid",
  "priority": 10
}
```

### 29.4 AI agent registry

Один provider может иметь несколько agents с разными ролями.

Firestore collection:

```text
/ai_agents/{agent_id}
```

Example:

```json
{
  "agent_id": "capital_orchestrator",
  "provider_id": "gemini_control",
  "agent_role": "orchestrator",
  "enabled": true,
  "allowed_actions": [
    "read_context",
    "summarize",
    "rank_projects",
    "create_review_recommendation"
  ],
  "denied_actions": [
    "delete_file",
    "publish_sensitive_context",
    "approve_own_action"
  ],
  "input_context_bundle": "executive_context",
  "output_schema": "orchestrator_decision_v1",
  "requires_human_approval_for": [
    "security_exception",
    "destructive_action",
    "restricted_data_access"
  ]
}
```

### 29.5 AI roles

```text
orchestrator:
  главный координатор reasoning-сессии, выбирает какие agents вызывать

auditor:
  проверяет архитектуру, риски, ошибки, policy violations

operator:
  выполняет разрешённые действия через tools

summarizer:
  сжимает документы, проекты, изменения

relationship_analyst:
  ищет связи между проектами, людьми, деньгами, документами

scoring_agent:
  оценивает приоритеты и $10M filter

legal_sensitive_reviewer:
  работает только с разрешёнными legal summaries, не с raw legal content

finance_sensitive_reviewer:
  работает только с разрешёнными financial summaries, не с raw bank data

human:
  ручной approval / override
```

### 29.6 Multi-agent execution modes

```text
single_agent:
  один AI получает context bundle и возвращает ответ

parallel_review:
  несколько AI независимо анализируют один context bundle

debate:
  два или больше AI дают разные позиции, orchestrator синтезирует итог

specialist_chain:
  orchestrator → specialist agents → validator → final response

fallback:
  если primary AI недоступен или упёрся в лимит, запрос уходит backup AI

human_in_the_loop:
  AI готовит решение, человек approve/reject
```

### 29.7 Context bundles

AI context files остаются, но становятся не привязанными к конкретному AI.

Context bundles:

```text
executive_context
project_index
relationship_graph
recent_changes_7d
review_queue
stale_zones
cost_and_errors
security_limited_context
agent_task_context
```

Каждый bundle имеет:

```json
{
  "bundle_id": "executive_context",
  "version": 12,
  "generated_at": "2026-05-25T10:00:00Z",
  "max_tokens": 7500,
  "max_size_kb": 30,
  "allowed_ai_roles": ["orchestrator", "auditor", "summarizer"],
  "allowed_sensitivity_classes": [
    "PUBLIC_INTERNAL",
    "BUSINESS_CONFIDENTIAL"
  ],
  "excluded_sensitivity_classes": [
    "SECRET",
    "DO_NOT_INDEX",
    "LEGAL_PRIVILEGED"
  ],
  "source_projection_files": [
    "AI_EXECUTIVE_CONTEXT.md"
  ]
}
```

### 29.8 Context files

Generated context files:

```text
AI_EXECUTIVE_CONTEXT.md
AI_PROJECT_INDEX.md
AI_RELATIONSHIP_GRAPH.md
AI_RECENT_CHANGES_7D.md
AI_REVIEW_QUEUE.md
AI_STALE_ZONES.md
AI_COST_AND_ERRORS.md
AI_SECURITY_LIMITED_CONTEXT.md
AI_AGENT_TASK_CONTEXT.md
```

These are provider-neutral. They are not “Claude files” or “Gemini files”.

### 29.9 Context delivery mechanisms

Supported mechanisms:

```text
manual_paste:
  пользователь вручную вставляет context bundle в AI

file_attachment:
  context file прикладывается к AI-сессии

api_injection:
  backend отправляет context через API provider

mcp_or_connector:
  AI читает context через MCP / connector / Drive integration

project_knowledge_snapshot:
  статичный snapshot для AI project knowledge

agent_runtime_fetch:
  custom agent сам запрашивает context у AI Gateway

dashboard_copy:
  dashboard показывает готовый context для копирования
```

Каждый provider указывает supported delivery mechanisms:

```json
{
  "provider_id": "openai_primary",
  "supported_delivery": [
    "api_injection",
    "file_attachment",
    "mcp_or_connector"
  ]
}
```

### 29.10 Simultaneous AI usage

CAPITAL INDEX может использовать несколько AI одновременно.

Example:

```text
Gemini:
  fast classification, extraction, Workspace-native operations

Claude:
  strategic reasoning, architecture audit, risk review

ChatGPT:
  code generation, tool orchestration, document generation

Vertex AI model:
  internal GCP processing

Human:
  approval authority
```

AI Gateway формирует task graph:

```text
task_id
required_role
allowed_providers
context_bundle
policy_constraints
output_schema
validation_rules
approval_required
```

### 29.11 AI session audit

Firestore:

```text
/ai_sessions/{session_id}
```

Example:

```json
{
  "session_id": "session_2026_05_25_001",
  "mode": "parallel_review",
  "initiated_by": "user|scheduler|system",
  "agents": [
    "claude_auditor",
    "gemini_orchestrator",
    "chatgpt_code_agent"
  ],
  "context_bundles": [
    "executive_context",
    "relationship_graph"
  ],
  "policy_snapshot_id": "policy_123",
  "started_at": "timestamp",
  "completed_at": "timestamp",
  "status": "completed",
  "cost_estimate": 1.42
}
```

BigQuery:

```text
ai_session_log
ai_agent_output_log
ai_context_delivery_log
ai_provider_cost_log
```

### 29.12 Authority model

AI не получает абсолютную власть.

```text
AI can recommend.
AI can draft.
AI can summarize.
AI can classify within policy.
AI can route tasks.
AI can prepare actions.

AI cannot:
  approve its own restricted access
  delete files automatically
  bypass sensitivity policy
  publish restricted context without approval
  modify security policies without human approval
```

Final authority:

```text
policy-engine
review-orchestrator
human approval
audit log
```

### 29.13 Context size budgets

Default limits:

```text
AI_EXECUTIVE_CONTEXT.md:
  max 30 KB
  target 7,500 tokens

AI_PROJECT_INDEX.md:
  max 50 KB
  target 12,000 tokens

AI_RELATIONSHIP_GRAPH.md:
  max 50 KB
  target 12,000 tokens

AI_RECENT_CHANGES_7D.md:
  max 30 KB
  target 7,500 tokens

AI_REVIEW_QUEUE.md:
  max 30 KB
  target 7,500 tokens
```

If limit exceeded:

```text
1. Keep top-N critical items.
2. Move full list to paginated appendix.
3. Generate AI_PROJECT_INDEX_PART_001.md, PART_002.md, etc.
4. Add retrieval pointers.
5. Do not silently truncate critical blockers or security items.
```

### 29.14 Consumption success criteria

```text
1. Any supported AI can consume the same context bundle.
2. Two or more AI agents can analyze the same context in parallel.
3. Different AI agents can receive different context scopes by policy.
4. AI Gateway logs what context was sent to whom.
5. Restricted data is not sent to unauthorized AI providers.
6. Provider can be replaced without changing Firestore, BigQuery, Vault or source registries.
7. Human approval remains mandatory for sensitive/destructive actions.
```

---

## 30. Sheets dashboard

`CAPITAL_INDEX_2026` remains a human dashboard.

Tabs:

```text
Overview
Files
Projects
People
Entities
Relationships
Review Queue
Dedupe
Errors
Costs
Security
Stale Data
Backfill
```

Source:

```text
Firestore / BigQuery
```

Not allowed:

```text
manual database updates
untracked edits
secret storage
```

---

## 31. Review and approval

Approval channels:

```text
Telegram
Email magic link
Google Sheet dashboard
Vault AI_REVIEW_QUEUE.md
Admin web UI
```

Approval types:

```text
approve_ai_read
approve_embedding
approve_vault_publish
approve_context_publish
approve_archive
approve_dedupe_canonical
approve_sensitive_summary
approve_merge
approve_restore
```

Telegram is not a single point of failure.

Any destructive action:

```text
manual approval required
```

File deletion:

```text
forbidden for automation
```

---

## 32. Telegram bot

Commands:

```text
/status
/today
/review
/approve <id>
/reject <id>
/project <name>
/cash
/errors
/cost
/stale
/restore <projection_id>
```

Telegram bot is interface only. It is not source of truth.

---

## 33. Scoring Engine

Scoring runs after graph-builder.

Inputs:

```text
project facts
cash signals
deadlines
risks
relationships
recent changes
staleness
manual priorities
```

Dimensions:

```text
cash_impact
time_to_value
margin
strategic_asset
reusability
risk
execution_time
dependency_count
confidence
opportunity_cost
```

Output:

```json
{
  "project_id": "integra_motors",
  "score": 0.82,
  "priority": "critical",
  "rationale": "string",
  "confidence": 0.74,
  "source_relationships": [],
  "source_artifacts": []
}
```

Writes to:

```text
/decision_log
BigQuery decision_history
AI_EXECUTIVE_CONTEXT.md
```

---

## 34. Cost control and cost modeling

### 34.1 Cost attribution

Track cost by:

```text
business
project_id
source_id
worker
model
backfill_run
document type
sensitivity class
```

### 34.2 Cost state

Firestore:

```json
{
  "date": "2026-05-25",
  "total_estimated_cost_eur": 12.4,
  "gemini_cost": 7.1,
  "document_ai_cost": 2.0,
  "cloud_run_cost": 1.2,
  "bigquery_cost": 0.5,
  "pubsub_cost": 0.1,
  "status": "normal|warning|throttled|blocked"
}
```

### 34.3 Burst scenarios

Scenario: 500 files imported at once.

Controls:

```text
metadata processing continues
AI processing throttled
backfill queue slowed
expensive models paused if daily budget warning
Document AI page limits enforced
circuit breaker opens on repeated 429
```

### 34.4 Budget rules

```text
daily warning threshold
monthly warning threshold
bulk backfill throttle
expensive model throttle
sensitive document manual approval
large document approval
```

---

## 35. Backfill architecture

Backfill is a managed flow.

Stages:

```text
1. Drive inventory
2. Metadata import
3. Folder policy classification
4. Drive Label sync
5. Safe content extraction
6. AI classification
7. Embedding allowed files
8. Entity extraction
9. Relationship extraction
10. Dedupe
11. Graph build
12. Projection publish
```

Firestore:

```text
/backfill_runs/{run_id}
```

Example:

```json
{
  "run_id": "backfill_2026_05_25",
  "scope": "all_drive",
  "status": "running",
  "total_files": 1554,
  "processed_files": 410,
  "blocked_files": 38,
  "failed_files": 12,
  "started_at": "timestamp",
  "cost_limit_eur": 50
}
```

---

## 36. Data Migration

Phase 0.5 — Migration and baseline import.

Steps:

```text
1. Export current CAPITAL_INDEX_2026 Sheet.
2. Map rows to /files, /source_registry, /projects.
3. Import AI_Bridge_Log_Spreadsheet into BigQuery event history.
4. Parse existing Vault 00-overview.md files.
5. Extract project summaries into /projects.
6. Detect manual sections in Vault.
7. Mark generated/manual boundaries.
8. Archive AI_TODAY_CONTEXT and AI_WINDOW_CONTEXT.
9. Preserve old context files as legacy snapshots.
10. Validate counts before/after.
```

Collections:

```text
/migration_runs/{run_id}
/migration_errors/{error_id}
/legacy_artifacts/{artifact_id}
```

Validation:

```text
before_count_drive_files
after_count_firestore_files
before_project_count
after_project_count
vault_files_parsed
vault_files_failed
legacy_context_archived
manual_sections_detected
```

---

## 37. Multi-project governance

Every business/GCP/Firebase project is registered in `project_registry`.

For each:

```text
namespace
source roots
canonical sheets
vault path
sensitivity defaults
allowed workers
allowed AI models
cost attribution
owner
```

Cost attribution:

```text
cost by business
cost by source
cost by worker
cost by model
cost by backfill run
```

Existing projects connect as spokes. They are not merged into the control plane.

---

## 38. IAM and security

### 38.1 Service accounts

```text
capital-event-ingestor@
capital-policy-engine@
capital-ai-worker@
capital-document-ai@
capital-graph-builder@
capital-projection-writer@
capital-review-bot@
capital-audit-writer@
capital-cost-controller@
```

Each gets least-privilege roles.

### 38.2 Domain-wide delegation

Only for services requiring Workspace access.

Scopes:

```text
drive.readonly
drive.file
gmail.readonly
spreadsheets.readonly
documents.readonly
calendar.readonly
```

Full `drive` scope only for `projection-writer` if required to write Vault files.

### 38.3 Forbidden

```text
secrets in code
secrets in Apps Script
secrets in GitHub
secrets in Firestore
secrets in Vault
secrets in Sheets
automatic deletion
AI reading SECRET / DO_NOT_INDEX
embedding restricted data without approval
```

---

## 39. Region and residency

Preferred:

```text
EU region for Firestore / BigQuery / Storage where possible
Cloud Run EU region
Document AI EU processor if available
Vertex AI region based on model availability
```

---

## 40. Disaster Recovery

### 40.1 Objectives

```text
Firestore RPO: 24h
Firestore RTO: 4h

BigQuery RPO: 24h
BigQuery RTO: 4h

Vault projection RPO: 1h
Vault projection RTO: 2h

Secrets recovery RTO: 1h

Workspace lockout fallback:
  documented secondary admin path
```

### 40.2 Backups

```text
Firestore:
  daily export → capital-index-backups/firestore/

BigQuery:
  scheduled snapshots / table copies

Vault:
  hourly snapshot for generated files
  backup before every projection write

Source registry:
  daily JSON export

Security policies:
  daily JSON export

Prompt/schema configs:
  versioned Cloud Storage export
```

### 40.3 Failure scenarios

Firestore corruption:

```text
restore latest export into clean database
replay BigQuery event_log after export timestamp
```

Service account compromise:

```text
disable service account
rotate credentials
audit last 30 days
reissue least-privilege account
```

Workspace access failure:

```text
freeze ingestion
preserve Pub/Sub backlog
run reconciliation after access restored
```

Cost runaway:

```text
circuit breaker open
backfill paused
expensive AI disabled
metadata-only mode active
```

Vault corruption:

```text
restore from backup
regenerate projections from Firestore
```

### 40.4 DR drill

```text
monthly:
  restore Firestore export into test project
  replay sample events
  regenerate one Vault projection
  validate AI context output
```

---

## 41. Observability

Use:

```text
Cloud Logging
Cloud Monitoring
Error Reporting
Trace
BigQuery processing_stats
custom dashboards
budget alerts
```

Metrics:

```text
events_received
jobs_completed
jobs_failed
jobs_blocked
avg_latency_by_stage
ai_calls_by_model
cost_by_project
cost_by_worker
policy_denials
review_queue_size
projection_success_rate
dlq_count
stale_projects_count
vector_query_latency
confidence_drift
```

Alerts:

```text
DLQ > 0
AI cost daily limit > 80%
policy violation
projection failed
review queue critical item
worker error rate > threshold
Firestore write failures
BigQuery audit write failure
confidence drops > 10% month-over-month
```

---

## 42. AI quality drift monitoring

Each artifact has:

```text
confidence
model_id
model_version
prompt_version
schema_version
created_at
```

Monitoring:

```text
average confidence by model over time
average confidence by document type
schema invalid rate
manual rejection rate
relationship false-positive rate
```

Alert:

```text
if average confidence drops > 10% month-over-month:
  create review item
  freeze model upgrade
  run evaluation set
```

Evaluation set:

```text
100 representative files
manual expected outputs
re-run after model/prompt change
compare output quality
```

---

## 43. Testing Strategy

### 43.1 Unit tests

```text
each worker isolated
mock Firestore
mock Pub/Sub
mock Drive API
mock AI output
```

### 43.2 Integration tests

```text
event → ingest → policy → classify → extract → graph → projection
```

### 43.3 Synthetic events

```text
daily fake files
fake Drive events
fake Sheet changes
fake restricted files
fake projection conflicts
```

### 43.4 Canary deployments

```text
deploy new worker to 5% traffic
monitor 24h
promote or rollback
```

### 43.5 Test fixtures

```text
/test_fixtures/ in Cloud Storage
50 files of different types/classes
10 cross-project relationship examples
5 projection conflict examples
5 restricted data examples
```

---

## 44. Production flow

```text
1. New file appears in Drive.
2. Workspace Events API or Drive Watch sends event.
3. Pub/Sub receives event.
4. event-ingestor creates event and job.
5. metadata-loader reads metadata.
6. policy-engine applies Drive Labels, folder policy, source registry.
7. classifier-worker determines document type, project, business, sensitivity.
8. content-extractor or document-ai-worker extracts content if allowed.
9. chunker-worker creates chunks.
10. embedder-worker creates embeddings if allowed.
11. entity-extractor extracts people, companies, vehicles, money, deadlines, risks.
12. relationship-extractor builds links.
13. dedupe-clusterer assigns canonical cluster.
14. graph-builder updates knowledge graph.
15. validator checks schema, confidence, policy.
16. vault-writer updates Vault protected blocks.
17. context-publisher updates AI context files.
18. sheets-dashboard-writer updates dashboard.
19. audit-writer writes to BigQuery.
20. cost-controller updates cost state.
21. review-orchestrator creates approval tasks for disputed cases.
```

---

## 45. Production phases

### Phase 0 — Foundation and governance

```text
create capital-index-2026
enable APIs
create service accounts
create IAM
create Secret Manager
create Firestore
create BigQuery
create buckets
create Pub/Sub topics
create DLQ
create project_registry
create source_registry
create security_policies
create Drive Labels
create folder_policies
mark strict folders
remove secrets from Apps Script
```

### Phase 0.1 — Drive events POC

```text
create test folder
subscribe through Workspace Events API
test create/update/move/delete
verify Pub/Sub payload
verify fallback through Drive changes API
document final Drive ingestion mode
```

### Phase 0.5 — Migration

```text
export current CAPITAL_INDEX_2026 Sheet
import current metadata
import AI_Bridge_Log_Spreadsheet
parse Vault project files
archive old AI_TODAY_CONTEXT / AI_WINDOW_CONTEXT
validate counts
```

### Phase 1 — Event fabric

```text
Workspace Events API
Drive event subscriptions
Drive changes fallback
Gmail push
Sheets bridge
Calendar watcher
Pub/Sub routing
event-ingestor
metadata-loader
nightly reconciler
event audit
```

### Phase 2 — Policy and classification

```text
policy-engine-worker
folder policies
Drive Label sync
metadata classification
AI classification
review queue
security audit
limited context rules
```

### Phase 3 — Extraction and AI processing

```text
content-extractor
document-ai-worker
chunker-worker
entity-extractor
relationship-extractor
validator-worker
AI output schemas
AI call audit
multilingual extraction
```

### Phase 4 — Embeddings, dedupe, graph

```text
embedder-worker
vector backend config
dedupe-clusterer
canonical clusters
graph-builder
project links
people links
entity graph
```

### Phase 5 — Projection

```text
vault-writer
protected markdown blocks
pre-write backup
context-publisher
AI_EXECUTIVE_CONTEXT
AI_PROJECT_INDEX
AI_RELATIONSHIP_GRAPH
AI_RECENT_CHANGES_7D
AI_REVIEW_QUEUE
sheets-dashboard-writer
```

### Phase 6 — Review, scoring, consumption

```text
review-orchestrator
Telegram bot
email approval
scoring-engine
daily briefing
cost dashboard
error dashboard
stale zones dashboard
```

### Phase 7 — Multi-project expansion and optimization

```text
connect existing GCP projects
connect Firebase projects
cost attribution per business
source registry expansion
advanced graph analytics
optional Neo4j if graph workload requires it
optional Vertex AI Vector Search
optional Gemini Enterprise
external connectors optional
```

---

## 46. What is not allowed

```text
secrets in code
automatic file deletion
AI reading SECRET / DO_NOT_INDEX
embedding legal/financial/client files without approval
Vault as source of truth
Sheets as database
manual edits to generated blocks without conflict handling
unaudited AI calls
unaudited policy decisions
single-channel approval only
unbounded backfill
workers without idempotency
workers without lease
```

---

## 47. Production readiness criteria

```text
1. Drive events POC completed.
2. Fallback Drive changes API documented.
3. All Drive/Gmail/Sheets events enter event_log.
4. All files have source_id, project_id or review status.
5. All files have sensitivity_class.
6. SECRET / DO_NOT_INDEX are not read by AI.
7. All AI calls are audited.
8. All workers are idempotent.
9. All workers use leases for concurrency control.
10. Backpressure and circuit breaker are active.
11. DLQ works.
12. Review queue works across Telegram + backup channel.
13. Vault updates only through protected blocks.
14. Vault backup before write works.
15. AI context files generate automatically.
16. Dedupe works through canonical clusters.
17. Knowledge graph contains project/entity/person/file relationships.
18. Cost attribution works by project and model.
19. Manual approval is required for sensitive/destructive actions.
20. Existing GCP/Firebase projects are connected through registry.
21. Migration from current Sheet/Vault/context files is validated.
22. DR drill has passed at least once.
23. Testing fixtures and synthetic events exist.
24. AI quality drift monitoring is active.
```

---

## 48. External technical reference points

These references define assumptions that must be validated again before implementation:

1. Google Workspace Events API Drive events:
   - Google Workspace Events API supports subscriptions to Drive events delivered through Pub/Sub.
2. Google Drive API push notifications:
   - Drive API supports push notifications for resource changes and remains the fallback path.
3. Gmail Push Notifications:
   - Gmail API supports Pub/Sub push notifications for mailbox changes.
4. Firestore Vector Search:
   - Current limitations include 2048 dimensions, Standard edition 1000 result limit, no real-time snapshot listeners for vector search.
5. BigQuery Vector Search:
   - BigQuery supports `VECTOR_SEARCH` and vector indexes for scalable vector analytics.

Implementation must treat these as external dependencies, not permanent guarantees.

---

## 49. Final formula

```text
CAPITAL INDEX 2026 =
central control plane
+ multi-source event ingestion
+ policy-first security
+ staged AI processing fabric
+ operational Firestore graph
+ BigQuery audit/history
+ configurable vector backend
+ canonical clustering
+ Vault/SHEETS/AI context projections
+ review and approval system
+ scoring and decision layer
+ multi-project governance
+ concurrency control
+ backpressure
+ disaster recovery
+ testing and drift monitoring
```

This is the unified production-grade architecture for CAPITAL INDEX 2026.
