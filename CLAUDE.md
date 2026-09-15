# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single custom Odoo 18 addon, `addons/freight_forwarding`, implementing Freight Forwarding operations (Air + Sea) for Clavis Group. `enterprise/` is a vendored copy of Odoo Enterprise addons required as a dependency — not part of this module's source.

## Running the stack

```bash
cp config/odoo.conf.example config/odoo.conf   # first time only; set admin_passwd / db_password
docker-compose up -d                            # Odoo at http://localhost:8066, Postgres on 5435
```
`docker-compose.yml` mounts `./addons` → `/mnt/extra-addons/base` and `./enterprise` → `/mnt/extra-addons/enterprise`, and runs a long-lived `odoo` process (no `-u` on boot in the base compose file).

To apply code changes to a running container, update the module explicitly:
```bash
docker compose exec odoo18 odoo -u freight_forwarding -d <dbname> --stop-after-init
```
**Do not** run this while another Odoo process (e.g. the container's own long-running server, or a second `docker exec`) is loading the same database — two processes upserting `ir_model_data` concurrently reliably deadlock in Postgres. If the container's own CMD already runs `-u freight_forwarding` on boot, just `docker restart` it instead of also exec'ing a manual update.

## Tests

Tests are explicitly listed in `__manifest__.py` under `"tests"` (not auto-discovered), and use `FreightTestBase` (`addons/freight_forwarding/tests/common.py`, a `TransactionCase` subclass) for shared master-data fixtures and factory methods (`_create_booking`, `_create_hbl`, `_create_quotation`, ...). Run inside the container:
```bash
odoo -d <dbname> -u freight_forwarding --test-enable --stop-after-init
odoo -d <dbname> -u freight_forwarding --test-enable --stop-after-init --test-tags /freight_forwarding:TestSeaHbl.test_method_name  # single test
```
No linter/formatter is configured for this module.

## Architecture

### Sea and Air are parallel, mirrored domains
Both `models/sea/` and `models/air/` (and their `views/sea/`, `views/menus/sea/` / `views/air/`, `views/menus/air/` counterparts) follow the same internal shape:
- `booking/` — the pre-job booking stage (`freight.sea.booking` / `freight.air.booking`).
- `hbl/` (Sea) / `hawb/` (Air) — the core Jobsheet model (`freight.sea.hbl` / `freight.air.hawb`), the heart of the domain: parties, shipment info, cargo/dimensions, and downstream Purchase Order / Sales Order / Document List / costing.
- `common/` — Abstract mixins shared only within that domain (e.g. `freight.air.shipment.info.mixin`, `freight.air.cargo.info.mixin`, `freight.sea.vessel.details.mixin`), inherited by both the booking and Jobsheet models so field definitions aren't duplicated.
- `master_data/` — domain-specific reference data (airports/airlines for Air; ports/vessels/shipping lines for Sea).
- `sales/` — quotation-side logic that ultimately creates `sale.order` records (`freight_business_type` distinguishes air/sea on the shared quotation).

Code genuinely shared *across* both domains lives at the top level: `models/common/` (cargo info mixin, purchase order integration, shared quotation base, `res.city`), `models/master_data/` (delivery type, commodity, container type, incoterm, shipment type), and `models/acct/` (account.move extensions, area).

### One core model per direction, not one model per Import/Export
`freight.air.hawb` and `freight.sea.hbl` each represent **both** Import and Export via a `freight_type` selection field (plus `awb_type`/`container_type` for further subtype) — there is deliberately no separate Import/Export model. Booking → Jobsheet is a real flow at the model level (`action_create_hawb`/equivalent copies booking fields into a new Jobsheet), but don't assume it's always the operationally correct UI flow for every direction — e.g. Air Import bypasses the Booking step at WPC in practice even though `freight.air.booking` still exists and is still reachable. Check the relevant Jira ticket's "confirmed flow" before assuming Sea/Air or Import/Export symmetry.

### Actions/views/menus: one model, many actions differentiated by domain+context
Most `ir.actions.act_window` records for these models share the *same* model and (by default) the same view, differing only in `domain` and default `context` (e.g. `action_freight_air_hawb_export` vs `..._import`). When two directions genuinely need different presentation (not just a filtered list), the established pattern is `ir.ui.view` inheritance (`inherit_id` + `xpath`) to add/move/hide whole sections, wiring the action's `views` field to the specific inherited view — not one giant shared arch that hides large sections with `invisible`. Small intra-type differences (e.g. House vs Direct vs Master AWB field visibility) still use plain `invisible` conditions on a shared arch.

### Security is flat
`security/*/ir.model.access.csv` grants full CRUD to `base.group_user` across the board — there are no `ir.rule` record rules anywhere in the module.

### Sequences and migrations
Job/booking numbering (`job_no`, `awb_no`, etc.) comes from `ir.sequence` records under `data/air/*.xml` / `data/sea/*.xml`, referenced by code (e.g. `freight.air.hawb.job_no.exp` / `.imp`) rather than hardcoded. Schema/data fixes ship as `migrations/<version>/pre-migrate.py`, keyed to the `version` in `__manifest__.py` — bump the manifest version when adding a new migration folder.

### Knowledge graph
This repo has a graphify knowledge graph at `graphify-out/` (see `.agents/rules/graphify.md`). For architecture/relationship questions, prefer `graphify query "<question>"` / `graphify path` / `graphify explain` over broad grep when that folder is present, and run `graphify update .` after modifying code in a session.

### Ticket & branch convention
Jira project `FF` (see `.agents/skills/ticket/SKILL.md`). Branches follow `FF-<ticket_number>-<kebab-case-description>`. Tickets are structured with Ref / Lokasi / Branch / Perubahan / Acceptance Criteria sections — read the linked ticket before implementing, since it's typically the source of truth for scope decisions (what to change vs. explicitly preserve).

# Project Working Rules

## Source of Truth

- Jira ticket adalah source of truth untuk requirement dan scope task.
- Jangan mengimplementasikan requirement yang tidak tertulis atau belum dikonfirmasi di tiket.
- Jika tiket ambigu pada hal yang memengaruhi model, workflow, cardinality, atau placement UI, jangan menebak. Laporkan ambiguity terlebih dahulu.
- Bedakan dengan jelas antara confirmed requirement, assumption, open question, dan out of scope.

## Before Changing Code

- Selalu inspect implementasi existing sebelum membuat perubahan.
- Cari model, mixin, action, menu, view, field, relation, dan behavior yang sudah tersedia sebelum membuat object baru.
- Jangan menyatakan sesuatu "belum ada" sebelum mencari implementasinya di codebase.
- Prefer reuse terhadap model/action/view/mixin existing dibanding membuat duplikasi baru.

## Odoo Architecture

- Jangan menyamakan model, form view, action, menu, dan workflow. Satu model dapat memiliki beberapa form view, action, dan menu.
- Jangan memecah model hanya karena UI atau menu berbeda.
- Gunakan `invisible` untuk variasi kecil. Jika keseluruhan section/tab berbeda secara signifikan, pertimbangkan form view terpisah dengan model yang sama.
- Hindari duplikasi source of truth field hanya untuk kebutuhan tampilan.
- Existing data harus tetap kompatibel setelah perubahan.

## Scope Discipline

- Implementasikan perubahan yang diperlukan oleh tiket saja.
- Jangan melakukan unrelated refactor, cleanup, redesign, atau penambahan flexibility tanpa requirement.
- Jika menemukan technical debt di luar scope, laporkan sebagai follow-up; jangan otomatis memperbaikinya di task aktif.
- Jangan menghapus legacy code/action/model sebelum memastikan tidak ada dependency yang masih menggunakannya.

## Freight Forwarding Domain

- Sysfreight adalah referensi AS-IS untuk memahami workflow, terminology, layout, dan existing behavior. Sysfreight bukan blueprint yang harus disalin 1:1 ke Odoo.
- Screenshot, sample report, dan dokumen operasional adalah requirement evidence. Jangan mengabaikan placement atau struktur yang sudah eksplisit pada evidence tersebut.
- Jangan memindahkan field ke tab/section lain hanya karena secara teknis terasa lebih "logis" apabila requirement/layout existing sudah menunjukkan lokasi yang berbeda.
- Jika sebuah field ada di Sysfreight tetapi fungsi bisnisnya belum dipahami atau belum dikonfirmasi digunakan oleh WPC, jangan otomatis mengimplementasikannya.
- Consolidation tidak dianggap sebagai requirement WPC kecuali tiket secara eksplisit mengatakan sebaliknya.

## res.partner

- `res.partner` dapat merepresentasikan business party, organization, contact, atau external business location/facility.
- Role partner dalam transaksi harus dibedakan dari model partner itu sendiri.
- Jangan menggunakan `stock.warehouse` hanya karena sebuah field bernama "Warehouse". Gunakan `stock.warehouse` hanya untuk warehouse inventory yang memang dikelola melalui Odoo Inventory.
- Jangan hardcode numeric database ID untuk domain atau business logic.
- Jangan melakukan refactor global partner-role architecture dalam tiket yang tidak memiliki scope tersebut.

## UI / Layout Implementation

- Jika tiket memberikan layout field/tab yang eksplisit, ikuti grouping, tab, dan urutan tersebut.
- Jangan menentukan placement field berdasarkan nama field saja.
- Sebelum memindahkan atau menambahkan field, cek screenshot/layout requirement pada tiket.
- Preserve existing downstream sections yang berada di luar scope tiket.

## Completion

Sebelum menyatakan task selesai:
- cek bahwa acceptance criteria Jira terpenuhi;
- cek existing record masih dapat dibuka;
- cek flow existing yang tidak termasuk perubahan tidak rusak;
- sebutkan file yang diubah;
- sebutkan keputusan atau assumption yang dibuat selama implementasi.