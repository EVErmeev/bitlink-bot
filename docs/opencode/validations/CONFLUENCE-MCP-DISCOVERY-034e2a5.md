# CONFLUENCE-MCP-DISCOVERY-034e2a5

**Дата:** 2026-08-01
**Проверяемый head:** `034e2a5adab04e737cfdcef8a24b80e1a75dd4a4`

## Discovery Results

| Поле | Значение |
|---|---|
| MCP server discovered | yes |
| Server name | Confluence (via OpenCode MCP) |
| Confluence base URL | `https://art-conf.spbco.1cbit.ru` |
| Available tools | `confluence_confluence_search`, `confluence_confluence_get_page`, `confluence_confluence_get_page_children`, `confluence_confluence_get_comments`, `confluence_confluence_get_labels` |
| Read access | **pass** |
| Write access | **not available** (no create/update/delete tools in MCP) |
| Runtime invocation from ordinary Python | **not supported** (MCP tools only via OpenCode) |
| Secrets committed | **no** |

## Space and Parent Page

| Поле | Значение |
|---|---|
| Selected space | TXT (Протоколы встреч) |
| Selected parent page title | Ананьев Никита |
| Selected parent page ID | 212730370 |
| Parent page URL | https://art-conf.spbco.1cbit.ru/pages/viewpage.action?pageId=212730370 |
| Child pages found | 9 existing protocol pages |

## Decision

MCP provides **read-only** access. No create/write tools available.
For publication, the app must use **REST API** (`CONFLUENCE_PROVIDER=rest`).
MCP will be used for **verification/read-back** of published pages.

## Architecture

```
App (REST POST) → Confluence → page created
OpenCode (MCP read) → Confluence → verify page exists, title, body, parent match
```
