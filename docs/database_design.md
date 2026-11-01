# Database Design and Relationships

## 1. Schema source

The database definition is maintained in `src/database/schema.sql`.

The schema creates 15 tables: - 13 entity/event tables. - 2 many-to-many
bridge tables: `sales_rep_products` and `lead_campaigns`.

## 2. Entity groups

### Master/reference data

-   `companies`
-   `contacts`
-   `campaigns`
-   `territories`
-   `products`
-   `sales_reps`

### Lead and operational data

-   `leads`
-   `consents`
-   `score_rules`
-   `activities`
-   `tasks`
-   `opportunities`
-   `stage_history`

### Bridge tables

-   `sales_rep_products`
-   `lead_campaigns`

## 3. Relationships and cardinality

-   Company 1:N Contact. Every contact references one company.
-   Company 1:N Lead. Every lead references one company.
-   Contact 1:N Lead. Every lead references one contact.
-   Territory 1:N SalesRep. Every sales rep references one territory.
-   Territory 1:N Lead. Every lead references one territory.
-   Product 1:N Lead. Every lead references one product.
-   SalesRep N:M Product through `sales_rep_products`.
-   Lead 1:N Consent.
-   Lead 1:N Activity. Activity's contact and campaign references are
    optional.
-   Lead N:M Campaign through `lead_campaigns`.
-   Lead 1:N Task; each task also references one sales rep.
-   Lead 1:0..1 Opportunity. `opportunities.lead_id` is UNIQUE.
-   Lead 1:N StageHistory. StageHistory may optionally reference an
    opportunity and a sales rep.
-   Lead 1:N Lead (duplicate self-reference) through nullable
    `duplicate_of_lead_id`.

## 4. Key and integrity strategy

-   Each table has a primary key. Bridge tables use composite primary
    keys.
-   Foreign keys prevent references to missing parent records.
-   Unique constraints prevent duplicate contact email, representative
    email, product name, territory name, and more than one opportunity
    per lead.
-   CHECK constraints enforce non-negative amounts/counts, score ranges,
    valid date ordering and closed-opportunity timestamp requirements.
-   Indexes support lead scoring/status/territory queries, activity
    timelines, task due queues and stage-history timelines.

## 5. Lifecycle and history

`consents` preserves consent states and effective dates as records.
`activities` records timestamped interactions. `stage_history` stores
previous and new stages as separate transition records.

The SQL schema restricts allowed enum values but does not by itself
enforce every valid transition sequence or make `stage_history`
physically append-only. Application validation, permissions or triggers
are needed for those controls.

## 6. Important implementation gaps and loading notes

-   `lead_campaigns` is generated in `data/generated/lead_campaigns.csv`
    and imported separately using `scripts/load_lead_campaigns.py`.
    The dedicated loader successfully imported 20,000 records. It is
    separate from the general `load_data.py` workflow and should only be
    run when the destination table is empty.
-   The SQL `activities.activity_type` ENUM includes `DEMO_COMPLETED`,
    so the reviewed schema supports this V2 activity type. The injected
    `EMAIL_SENT` event is also an allowed enum value. This confirms
    compatibility for these event types, not that all V2 staged activity
    rows have been loaded into MySQL.
-   A foreign key confirms that an assigned sales representative exists;
    it does not ensure the representative's territory matches the lead's
    territory. This needs business-rule validation.
-   SQL enums constrain allowed status and stage values, but do not
    enforce every valid lifecycle transition sequence. Application
    validation, permissions or triggers are needed for those controls.
-   The schema describes `stage_history` records, but does not itself
    prohibit updates or deletes. Append-only behavior requires application
    policy, permissions or triggers.
