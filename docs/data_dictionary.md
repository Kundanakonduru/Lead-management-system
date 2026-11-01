# Data Dictionary --- Lead Management System

This document describes the columns defined in `src/database/schema.sql`
and the generation-specific conventions visible in the current
`generate_events.py` implementation.

**Scope and interpretation** - SQL data types, nullability, defaults,
enumerations, primary keys, foreign keys, unique constraints and check
constraints below are taken from the supplied schema. - "Required" means
the SQL column is `NOT NULL`. "Optional" means it permits `NULL`. -
Units and semantic meanings are stated only where the schema or
generator makes them clear. Where the code does not establish a rule,
this document says "not specified". - The V2 event generator writes
staged CSV/JSON data. Its output is not automatically the same as the
rows currently loaded into MySQL. - The schema has 15 tables, including
two many-to-many bridge tables.

## 1. Company --- `companies`

  ------------------------------------------------------------------------------------------------------------------------------
  Field              SQL type                                       Required? Allowed values         Unique? Validation /
                                                                              / units                        relationship
  ------------------ ----------------------------------------- -------------- --------------- -------------- -------------------
  `company_id`       `VARCHAR(12)`                                        Yes Identifier;                 PK Primary key;
                                                                              generator                      immutable and
                                                                              convention                     referenced by
                                                                              should be                      contacts and leads
                                                                              `CO-000001`

  `company_name`     `VARCHAR(150)`                                       Yes Company name                No Maximum 150
                                                                                                             characters

  `industry`         `VARCHAR(80)`                                        Yes Industry label              No Maximum 80
                                                                                                             characters;
                                                                                                             product-industry
                                                                                                             matching uses
                                                                                                             labels from
                                                                                                             generator
                                                                                                             assumptions

  `company_size`     `ENUM('SMB','MID_MARKET','ENTERPRISE')`              Yes `SMB`,                      No Must be one of the
                                                                              `MID_MARKET`,                  listed values
                                                                              `ENTERPRISE`

  `employee_count`   `INT`                                                 No Number of                   No `NULL` or value \>=
                                                                              employees;                     0
                                                                              people/count

  `annual_revenue`   `DECIMAL(15,2)`                                       No Revenue in                  No `NULL` or value \>=
                                                                              currency units;                0;
                                                                              V2 generator                   amount-generation
                                                                              treats it as                   cap uses 1% of this
                                                                              INR                            value when \> 0

  `country`          `VARCHAR(80)`                                        Yes Country name                No Maximum 80
                                                                                                             characters

  `state`            `VARCHAR(80)`                                         No State/region                No Maximum 80
                                                                              name                           characters

  `city`             `VARCHAR(80)`                                         No City name                   No Maximum 80
                                                                                                             characters

  `website`          `VARCHAR(255)`                                        No Website                     No Maximum 255
                                                                              address/URL                    characters; URL
                                                                                                             format is not
                                                                                                             constrained by SQL

  `created_at`       `DATETIME`                                           Yes Date and time               No Required timestamp
  ------------------------------------------------------------------------------------------------------------------------------

## 2. Contact --- `contacts`

  -----------------------------------------------------------------------------------------------------
  Field          SQL type              Required? Allowed values        Unique? Validation /
                                                 / units                       relationship
  -------------- ---------------- -------------- -------------- -------------- ------------------------
  `contact_id`   `VARCHAR(12)`               Yes Identifier;                PK Primary key; referenced
                                                 convention                    by leads and optionally
                                                 `CON-000001`                  activities

  `company_id`   `VARCHAR(12)`               Yes Existing                   No FK →
                                                 company ID                    `companies.company_id`

  `first_name`   `VARCHAR(80)`               Yes First name                 No Maximum 80 characters

  `last_name`    `VARCHAR(80)`               Yes Last name                  No Maximum 80 characters

  `email`        `VARCHAR(254)`              Yes Email address             Yes Unique key
                                                                               `uq_contact_email`;
                                                                               maximum 254 characters

  `phone`        `VARCHAR(25)`                No Phone number               No Maximum 25 characters;
                                                 as text                       preserve country
                                                                               code/format as text

  `job_title`    `VARCHAR(100)`               No Job title                  No Maximum 100 characters

  `created_at`   `DATETIME`                  Yes Date and time              No Required timestamp
  -----------------------------------------------------------------------------------------------------

## 3. Campaign --- `campaigns`

  ----------------------------------------------------------------------------------------------------------------------------------------------
  Field             SQL type                                                            Required? Allowed             Unique? Validation /
                                                                                                  values /                    relationship
                                                                                                  units
  ----------------- -------------------------------------------------------------- -------------- ------------ -------------- ------------------
  `campaign_id`     `VARCHAR(12)`                                                             Yes Campaign                 PK Primary key;
                                                                                                  identifier                  referenced by
                                                                                                                              activities and
                                                                                                                              `lead_campaigns`

  `campaign_name`   `VARCHAR(150)`                                                            Yes Campaign                 No Maximum 150
                                                                                                  name                        characters

  `campaign_type`   `ENUM('EMAIL','WEBINAR','SOCIAL','PAID_AD','EVENT','OTHER')`              Yes Listed enum              No Must match one of
                                                                                                  values                      the allowed
                                                                                                                              campaign types

  `start_date`      `DATE`                                                                    Yes Calendar                 No Required
                                                                                                  date

  `end_date`        `DATE`                                                                     No Calendar                 No `NULL` or \>=
                                                                                                  date                        `start_date`

  `budget`          `DECIMAL(14,2)`                                                            No Monetary                 No Defaults to 0;
                                                                                                  amount;                     must be \>= 0
                                                                                                  currency not
                                                                                                  specified in
                                                                                                  this table

  `status`          `ENUM('PLANNED','ACTIVE','COMPLETED','CANCELLED')`                        Yes Listed enum              No Must match one of
                                                                                                  values                      the allowed
                                                                                                                              statuses
  ----------------------------------------------------------------------------------------------------------------------------------------------

## 4. Territory --- `territories`

  ---------------------------------------------------------------------------------------------
  Field              SQL type              Required? Allowed             Unique? Validation /
                                                     values /                    relationship
                                                     units
  ------------------ ---------------- -------------- ------------ -------------- --------------
  `territory_id`     `VARCHAR(12)`               Yes Territory                PK Primary key;
                                                     identifier                  referenced by
                                                                                 sales reps and
                                                                                 leads

  `territory_name`   `VARCHAR(100)`              Yes Territory               Yes Unique;
                                                     name                        maximum 100
                                                                                 characters

  `region`           `VARCHAR(80)`               Yes Region label             No Maximum 80
                                                                                 characters

  `country`          `VARCHAR(80)`               Yes Country name             No Maximum 80
                                                                                 characters
  ---------------------------------------------------------------------------------------------

## 5. Product --- `products`

  ---------------------------------------------------------------------------------------------------
  Field            SQL type              Required? Allowed             Unique? Validation /
                                                   values /                    relationship
                                                   units
  ---------------- ---------------- -------------- ------------ -------------- ----------------------
  `product_id`     `VARCHAR(12)`               Yes Product                  PK Primary key;
                                                   identifier                  referenced by leads
                                                                               and
                                                                               `sales_rep_products`

  `product_name`   `VARCHAR(120)`              Yes Product name            Yes Unique; maximum 120
                                                                               characters

  `category`       `VARCHAR(80)`                No Product                  No Maximum 80 characters
                                                   category

  `active`         `BOOLEAN`                   Yes TRUE/FALSE               No Defaults to TRUE; V2
                                                                               generator rejects
                                                                               leads referencing an
                                                                               inactive product
  ---------------------------------------------------------------------------------------------------

## 6. Sales Representative --- `sales_reps`

  -------------------------------------------------------------------------------------------------------------
  Field            SQL type              Required? Allowed values /        Unique? Validation / relationship
                                                   units
  ---------------- ---------------- -------------- ---------------- -------------- ----------------------------
  `sales_rep_id`   `VARCHAR(12)`               Yes Representative               PK Primary key; referenced by
                                                   identifier                      leads, tasks and stage
                                                                                   history

  `rep_name`       `VARCHAR(120)`              Yes Representative               No Maximum 120 characters
                                                   name

  `email`          `VARCHAR(254)`              Yes Email address               Yes Unique; maximum 254
                                                                                   characters

  `territory_id`   `VARCHAR(12)`               Yes Existing                     No FK →
                                                   territory ID                    `territories.territory_id`

  `active`         `BOOLEAN`                   Yes TRUE/FALSE                   No Defaults to TRUE

  `created_at`     `DATETIME`                  Yes Date and time                No Required timestamp
  -------------------------------------------------------------------------------------------------------------

## 7. Sales Representative/Product bridge --- `sales_rep_products`

This bridge implements the many-to-many relationship between sales
representatives and products.

  -----------------------------------------------------------------------------------------------------------
  Field            SQL type             Required? Allowed values /        Unique? Validation / relationship
                                                  units
  ---------------- --------------- -------------- ---------------- -------------- ---------------------------
  `sales_rep_id`   `VARCHAR(12)`              Yes Existing           Composite PK FK →
                                                  representative             part `sales_reps.sales_rep_id`
                                                  ID

  `product_id`     `VARCHAR(12)`              Yes Existing product   Composite PK FK → `products.product_id`
                                                  ID                         part
  -----------------------------------------------------------------------------------------------------------

The pair (`sales_rep_id`, `product_id`) is the composite primary key, so
the same representative/product pairing cannot be inserted twice.

## 8. Lead --- `leads`

  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Field                    SQL type                                                                                   Required? Allowed values /            Unique? Validation / relationship
                                                                                                                                units
  ------------------------ ------------------------------------------------------------------------------------- -------------- -------------------- -------------- ----------------------------
  `lead_id`                `VARCHAR(25)`                                                                                    Yes Identifier                       PK Primary key; immutable
                                                                                                                                convention
                                                                                                                                `LEAD-2026-000001`

  `contact_id`             `VARCHAR(12)`                                                                                    Yes Existing contact ID              No FK → `contacts.contact_id`

  `company_id`             `VARCHAR(12)`                                                                                    Yes Existing company ID              No FK → `companies.company_id`

  `source`                 `ENUM('WEBSITE','EMAIL','REFERRAL','SOCIAL','EVENT','PAID_AD','OTHER')`                          Yes Listed enum values               No Must match an allowed lead
                                                                                                                                                                    source

  `product_id`             `VARCHAR(12)`                                                                                    Yes Existing product ID              No FK → `products.product_id`

  `territory_id`           `VARCHAR(12)`                                                                                    Yes Existing territory               No FK →
                                                                                                                                ID                                  `territories.territory_id`

  `lead_status`            `ENUM('NEW','QUALIFIED','CONTACTED','NURTURING','CONVERTED','DISQUALIFIED','LOST')`              Yes Listed enum values               No Defaults to `NEW`; lifecycle
                                                                                                                                                                    transition sequence is not
                                                                                                                                                                    enforced by this enum alone

  `fit_score`              `DECIMAL(5,2)`                                                                                   Yes Score points, 0--100             No Defaults to 0; CHECK 0--100

  `intent_score`           `DECIMAL(5,2)`                                                                                   Yes Score points, 0--100             No Defaults to 0; CHECK 0--100

  `engagement_score`       `DECIMAL(5,2)`                                                                                   Yes Score points, 0--100             No Defaults to 0; CHECK 0--100

  `total_score`            `DECIMAL(5,2)`                                                                                   Yes Score points, 0--100             No Defaults to 0; CHECK 0--100

  `created_at`             `DATETIME`                                                                                       Yes Date and time                    No Required timestamp

  `last_activity_at`       `DATETIME`                                                                                        No Date and time                    No Optional; should not be
                                                                                                                                                                    earlier than the lead
                                                                                                                                                                    creation time

  `assigned_rep_id`        `VARCHAR(12)`                                                                                     No Existing                         No Nullable FK →
                                                                                                                                representative ID                   `sales_reps.sales_rep_id`

  `is_duplicate`           `BOOLEAN`                                                                                        Yes TRUE/FALSE                       No Defaults to FALSE

  `duplicate_of_lead_id`   `VARCHAR(25)`                                                                                     No Existing lead ID                 No Nullable self-referencing FK
                                                                                                                                                                    → `leads.lead_id`
  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Indexes are defined for `total_score`, `lead_status`, (`territory_id`,
`product_id`) and `created_at`. The schema does not itself enforce that
an assigned representative belongs to the lead's territory; this is a
business-rule validation.

## 9. Consent --- `consents`

  ------------------------------------------------------------------------------------------------------------------------------------------------
  Field              SQL type                                                             Required? Allowed             Unique? Validation /
                                                                                                    values /                    relationship
                                                                                                    units
  ------------------ --------------------------------------------------------------- -------------- ------------ -------------- ------------------
  `consent_id`       `VARCHAR(30)`                                                              Yes Consent                  PK Primary key
                                                                                                    identifier

  `lead_id`          `VARCHAR(25)`                                                              Yes Existing                 No FK →
                                                                                                    lead ID                     `leads.lead_id`

  `consent_type`     `ENUM('EMAIL_MARKETING','PHONE_MARKETING','DATA_PROCESSING')`              Yes Listed enum              No Must match one of
                                                                                                    values                      the consent types

  `consent_status`   `ENUM('GRANTED','REVOKED','PENDING')`                                      Yes Listed enum              No Must match one of
                                                                                                    values                      the consent states

  `effective_from`   `DATETIME`                                                                 Yes Date and                 No Required
                                                                                                    time

  `effective_to`     `DATETIME`                                                                  No Date and                 No `NULL` or \>=
                                                                                                    time                        `effective_from`

  `recorded_at`      `DATETIME`                                                                 Yes Date and                 No Required record
                                                                                                    time                        timestamp

  `source`           `VARCHAR(80)`                                                               No Source label             No Maximum 80
                                                                                                                                characters; V2
                                                                                                                                generator uses
                                                                                                                                `SYNTHETIC_FORM`
  ------------------------------------------------------------------------------------------------------------------------------------------------

Index: (`lead_id`, `consent_type`, `effective_from`). The generator
creates consent rows for email marketing, phone marketing and data
processing. For granted marketing consent, it may generate a revocation
date; data-processing consent is generated as granted in the supplied V2
generator.

## 10. Score Rule --- `score_rules`

  ------------------------------------------------------------------------------------------------------------------------
  Field              SQL type                                   Required? Allowed values        Unique? Validation /
                                                                          / units                       relationship
  ------------------ ------------------------------------- -------------- -------------- -------------- ------------------
  `rule_id`          `VARCHAR(20)`                                    Yes Rule                       PK Primary key
                                                                          identifier; V2
                                                                          convention
                                                                          `RULE-0001`

  `rule_name`        `VARCHAR(120)`                                   Yes Rule/feature               No Maximum 120
                                                                          label                         characters

  `feature_type`     `ENUM('FIT','INTENT','ENGAGEMENT')`              Yes Listed score               No Must match a score
                                                                          groups                        group

  `feature_name`     `VARCHAR(100)`                                   Yes Feature name               No Maximum 100
                                                                                                        characters

  `weight`           `DECIMAL(6,3)`                                   Yes Fraction from              No CHECK 0 \<= weight
                                                                          0 to 1                        \<= 1

  `effective_from`   `DATETIME`                                       Yes Date and time              No Required

  `effective_to`     `DATETIME`                                        No Date and time              No `NULL` or \>=
                                                                                                        `effective_from`

  `active`           `BOOLEAN`                                        Yes TRUE/FALSE                 No Defaults to TRUE
  ------------------------------------------------------------------------------------------------------------------------

The V2 generator creates 10 feature rules. Component weights are: FIT
0.40/0.35/0.25; INTENT 0.50/0.30/0.20; ENGAGEMENT 0.25/0.35/0.20/0.20.
Overall component weights are FIT 0.35, INTENT 0.35 and ENGAGEMENT 0.30;
these overall weights are recorded in the generation summary rather than
as additional rows in `score_rules`.

## 11. Activity --- `activities`

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Field                  SQL type                                                                                                                                                                                        Required? Allowed              Unique? Validation / relationship
                                                                                                                                                                                                                                   values /
                                                                                                                                                                                                                                   units
  ---------------------- ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ -------------- ------------- -------------- -------------------------
  `activity_id`          `VARCHAR(45)`                                                                                                                                                                                         Yes Activity                  PK Primary key; V2 normal
                                                                                                                                                                                                                                   identifier                   IDs use `ACT-` plus lead
                                                                                                                                                                                                                                                                ID and a counter;
                                                                                                                                                                                                                                                                injected cases use
                                                                                                                                                                                                                                                                labelled suffixes

  `lead_id`              `VARCHAR(25)`                                                                                                                                                                                         Yes Existing lead             No FK → `leads.lead_id`
                                                                                                                                                                                                                                   ID

  `contact_id`           `VARCHAR(12)`                                                                                                                                                                                          No Existing                  No Nullable FK →
                                                                                                                                                                                                                                   contact ID                   `contacts.contact_id`

  `campaign_id`          `VARCHAR(12)`                                                                                                                                                                                          No Existing                  No Nullable FK →
                                                                                                                                                                                                                                   campaign ID                  `campaigns.campaign_id`

  `activity_type`        `ENUM('EMAIL_SENT','EMAIL_OPENED','EMAIL_CLICKED','WEBSITE_VISIT','PAGE_VIEW','BROCHURE_DOWNLOAD','DEMO_REQUESTED','DEMO_COMPLETED','PHONE_CALL','MEETING','FORM_SUBMITTED','PURCHASE')`              Yes Listed enum               No Must match the SQL enum;
                                                                                                                                                                                                                                   values                       see V2 mismatch note
                                                                                                                                                                                                                                                                below

  `activity_timestamp`   `DATETIME`                                                                                                                                                                                            Yes Date and time             No Required event timestamp

  `activity_value`       `DECIMAL(10,2)`                                                                                                                                                                                        No Numeric event             No Defaults to 0
                                                                                                                                                                                                                                   value; unit
                                                                                                                                                                                                                                   depends on
                                                                                                                                                                                                                                   event

  `description`          `VARCHAR(500)`                                                                                                                                                                                         No Free-text                 No Maximum 500 characters
                                                                                                                                                                                                                                   description
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Index: (`lead_id`, `activity_timestamp`). The supplied SQL enum
includes `DEMO_COMPLETED`, and the injected `EMAIL_SENT` event is also an
allowed enum value. These two activity types are therefore compatible
with the reviewed schema. This does not by itself confirm that all V2
staged activity rows have been imported into MySQL.

## 12. Lead/Campaign bridge --- `lead_campaigns`

This bridge implements the many-to-many relationship between leads and
campaigns.

  ------------------------------------------------------------------------------------------------------
  Field           SQL type             Required? Allowed values        Unique? Validation / relationship
                                                 / units
  --------------- --------------- -------------- -------------- -------------- -------------------------
  `lead_id`       `VARCHAR(25)`              Yes Existing lead    Composite PK FK → `leads.lead_id`
                                                 ID                       part

  `campaign_id`   `VARCHAR(12)`              Yes Existing         Composite PK FK →
                                                 campaign ID              part `campaigns.campaign_id`

  `linked_at`     `DATETIME`                 Yes Date and time              No Required timestamp
                                                 the
                                                 relationship
                                                 was recorded
  ------------------------------------------------------------------------------------------------------

The pair (`lead_id`, `campaign_id`) is the composite primary key.
The master generator writes `data/generated/lead_campaigns.csv` with
`lead_id`, `campaign_id` and `linked_at`. The table is imported separately
using `scripts/load_lead_campaigns.py`; this dedicated loader is separate
from the general `load_data.py` workflow.

## 13. Task --- `tasks`

  --------------------------------------------------------------------------------------------------------------------------------------------------------------
  Field               SQL type                                                       Required? Allowed values / units        Unique? Validation / relationship
  ------------------- --------------------------------------------------------- -------------- ---------------------- -------------- ---------------------------
  `task_id`           `VARCHAR(45)`                                                        Yes Task identifier; V2                PK Primary key
                                                                                               convention
                                                                                               `TASK-<lead-id>-001`

  `lead_id`           `VARCHAR(25)`                                                        Yes Existing lead ID                   No FK → `leads.lead_id`

  `assigned_rep_id`   `VARCHAR(12)`                                                        Yes Existing                           No FK →
                                                                                               representative ID                     `sales_reps.sales_rep_id`

  `task_type`         `ENUM('CALL','EMAIL','DEMO','MEETING','FOLLOW_UP')`                  Yes Listed task types                  No Must match an allowed task
                                                                                                                                     type

  `priority`          `ENUM('LOW','MEDIUM','HIGH','URGENT')`                               Yes Listed priorities                  No Must match an allowed
                                                                                                                                     priority

  `due_at`            `DATETIME`                                                           Yes Date and time                      No Required due timestamp; V2
                                                                                                                                     generator sets lead
                                                                                                                                     creation + 2 days

  `task_status`       `ENUM('PENDING','IN_PROGRESS','COMPLETED','CANCELLED')`              Yes Listed task states                 No Defaults to `PENDING`

  `created_at`        `DATETIME`                                                           Yes Date and time                      No Required timestamp

  `completed_at`      `DATETIME`                                                            No Date and time                      No `NULL` or \>= `created_at`
  --------------------------------------------------------------------------------------------------------------------------------------------------------------

Index: (`task_status`, `due_at`). The V2 generator chooses CALL when
phone consent remains valid at the due time; otherwise it chooses EMAIL
if email consent remains valid. It does not create a task when neither
channel is valid.

## 14. Opportunity --- `opportunities`

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Field                 SQL type                                                                              Required? Allowed values /           Unique? Validation /
                                                                                                                        units                              relationship
  --------------------- -------------------------------------------------------------------------------- -------------- ------------------- -------------- ------------------
  `opportunity_id`      `VARCHAR(25)`                                                                               Yes V2 convention                   PK Primary key
                                                                                                                        `OPP-2026-000001`

  `lead_id`             `VARCHAR(25)`                                                                               Yes Existing lead ID               Yes Unique FK →
                                                                                                                                                           `leads.lead_id`;
                                                                                                                                                           at most one
                                                                                                                                                           opportunity per
                                                                                                                                                           lead

  `opportunity_name`    `VARCHAR(150)`                                                                              Yes Opportunity name                No Maximum 150
                                                                                                                                                           characters

  `amount`              `DECIMAL(15,2)`                                                                             Yes Monetary amount; V2             No Must be \>= 0
                                                                                                                        generator uses INR

  `currency`            `CHAR(3)`                                                                                   Yes Three-character                 No Defaults to `INR`
                                                                                                                        currency code

  `opportunity_stage`   `ENUM('QUALIFICATION','NEEDS_ANALYSIS','PROPOSAL','NEGOTIATION','WON','LOST')`              Yes Listed opportunity              No Closed stages
                                                                                                                        stages                             WON/LOST require
                                                                                                                                                           `closed_at`; open
                                                                                                                                                           stages require it
                                                                                                                                                           to be NULL

  `created_at`          `DATETIME`                                                                                  Yes Date and time                   No Required timestamp

  `closed_at`           `DATETIME`                                                                                   No Date and time                   No `NULL` or \>=
                                                                                                                                                           `created_at`;
                                                                                                                                                           required for
                                                                                                                                                           WON/LOST by CHECK

  `outcome_reason`      `VARCHAR(255)`                                                                               No Outcome explanation             No Maximum 255
                                                                                                                                                           characters
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Index: `opportunity_stage`. The V2 generator selects the top 3,000 leads
by total score (descending, then lead ID ascending). It labels the top
30% of that ranked cohort WON and the remaining 70% LOST. This is a
synthetic benchmark assumption, not an observed sales outcome.
Opportunity amount is product base price multiplied by company-size
multiplier, capped at 1% of annual revenue when annual revenue is
positive.

## 15. Stage History --- `stage_history`

  ----------------------------------------------------------------------------------------------------------------------------------
  Field                SQL type                       Required? Allowed values /            Unique? Validation / relationship
                                                                units
  -------------------- ------------------------- -------------- -------------------- -------------- --------------------------------
  `stage_history_id`   `BIGINT AUTO_INCREMENT`              Yes Database-generated               PK Primary key generated by MySQL
                                                                integer

  `lead_id`            `VARCHAR(25)`                        Yes Existing lead ID                 No FK → `leads.lead_id`

  `opportunity_id`     `VARCHAR(25)`                         No Existing opportunity             No Nullable FK →
                                                                ID                                  `opportunities.opportunity_id`

  `previous_stage`     `VARCHAR(40)`                         No Previous stage label             No Optional; maximum 40 characters

  `new_stage`          `VARCHAR(40)`                        Yes New stage label                  No Required; maximum 40 characters

  `changed_at`         `DATETIME`                           Yes Date and time                    No Required transition timestamp

  `changed_by`         `VARCHAR(12)`                         No Existing sales                   No Nullable FK →
                                                                representative ID                   `sales_reps.sales_rep_id`

  `change_reason`      `VARCHAR(255)`                        No Explanation for                  No Maximum 255 characters
                                                                transition
  ----------------------------------------------------------------------------------------------------------------------------------

Index: (`lead_id`, `changed_at`). The table is intended to preserve
stage transitions as separate records. The schema does not itself
enforce chronological continuity or prohibit updates/deletes;
append-only behavior must be enforced by application policy, permissions
or triggers.

## Relationship and cardinality summary

  ----------------------------------------------------------------------------------
  Parent            Child / bridge       Cardinality       Optionality / notes
  ----------------- -------------------- ----------------- -------------------------
  Company           Contacts             1:N               Each contact must
                                                           reference one company

  Company           Leads                1:N               Each lead must reference
                                                           one company

  Contact           Leads                1:N               Each lead must reference
                                                           one contact

  Territory         Sales reps           1:N               Each sales rep must
                                                           reference one territory

  Territory         Leads                1:N               Each lead must reference
                                                           one territory

  Product           Leads                1:N               Each lead must reference
                                                           one product

  Sales reps        Sales-rep/products   1:N               Bridge records represent
                                                           eligible products

  Product           Sales-rep/products   1:N               Together these form
                                                           SalesRep N:M Product

  Lead              Consents             1:N               A lead may have multiple
                                                           consent types/history
                                                           records

  Lead              Activities           1:N               Each activity must
                                                           reference one lead

  Contact           Activities           1:N               Activity contact
                                                           reference is optional

  Campaign          Activities           1:N               Activity campaign
                                                           reference is optional

  Lead              Tasks                1:N               Each task must reference
                                                           one lead

  Sales reps        Tasks                1:N               Each task must reference
                                                           one representative

  Lead              Opportunity          1:0..1            `opportunities.lead_id`
                                                           is UNIQUE

  Lead              Stage history        1:N               Each history record must
                                                           reference one lead

  Opportunity       Stage history        1:N               Stage-history opportunity
                                                           reference is optional

  Sales reps        Stage history        1:N               `changed_by` is optional

  Lead              Lead/campaigns       1:N               Bridge records represent
                                                           linked campaigns

  Campaign          Lead/campaigns       1:N               Together these form Lead
                                                           N:M Campaign

  Lead              Lead (duplicate      1:N               `duplicate_of_lead_id` is
                    reference)                             an optional
                                                           self-reference
  ----------------------------------------------------------------------------------

## V2 scoring and generation rules

The supplied V2 generator uses `SEED = 20261022` and
`NOW = 2026-10-30 12:00:00`.

  ------------------------------------------------------------------------
  Score component  Feature          Feature value                   Weight
                                    rule
  ---------------- ---------------- ---------------- ---------------------
  Fit              Company size     SMB 70;                           0.40
                                    MID_MARKET 85;
                                    ENTERPRISE 100;
                                    unknown 40

  Fit              Industry match   100 if company                    0.35
                                    industry is in
                                    product's
                                    configured
                                    industry set;
                                    otherwise 30

  Fit              Employee count   \<=0: 0; \<50:                    0.25
                                    50; \<250: 70;
                                    \<1000: 85;
                                    otherwise 100

  Intent           Demo request     100 per event,                    0.50
                                    capped at 100

  Intent           Form submission  100 per event,                    0.30
                                    capped at 100

  Intent           PAGE_VIEW proxy  25 per event,                     0.20
                                    capped at 100

  Engagement       Email opened     25 per event,                     0.25
                                    capped at 100

  Engagement       Email clicked    25 per event,                     0.35
                                    capped at 100

  Engagement       Website visit    20 per event,                     0.20
                                    capped at 100

  Engagement       Meeting          50 per event,                     0.20
                                    capped at 100
  ------------------------------------------------------------------------

Overall score =
`0.35 × fit_score + 0.35 × intent_score + 0.30 × engagement_score`.

Only events from lead creation through `min(created_at + 30 days, NOW)`
are used for the initial score. Injected anomalies are appended after
scoring. Qualification is the top 3,000 leads by total score descending,
with `lead_id` ascending as the tie-breaker. The top 30% of the
qualified cohort by rank is labelled WON; the remainder LOST.

### Consent and task assumptions

-   Email and phone marketing consent are generated separately;
    data-processing consent is generated as granted.
-   Marketing consent may be revoked. The generator avoids creating
    email-open/email-click or phone-call events after revocation or
    without grant during its baseline event-generation loop.
-   A follow-up task is due two days after lead creation.
-   A CALL task is selected when phone consent is valid at due time;
    otherwise an EMAIL task is selected when email consent is valid. No
    task is created if neither channel is valid.
-   The opted-out-contact exception is deliberately injected after
    baseline generation and is kept as an anomaly case.

### Opportunity amount assumptions

-   Product base prices: Business Analytics INR 180,000; Cloud
    Management INR 240,000; CRM Software INR 150,000.
-   Company-size multipliers: SMB 1.0; MID_MARKET 2.5; ENTERPRISE 5.0.
-   Calculated amount = product base price × company-size multiplier.
-   If annual revenue is positive, the amount is capped at 1% of annual
    revenue. The cap is applied last.

## Known schema and implementation gaps to resolve

1.  **Activity ID convention:** the challenge example suggests
    `ACT-<lead-id>-001`. The V2 generator constructs the normal activity
    ID with `len(activities)+1`, which is a global counter across all
    leads, not a per-lead counter. Injected anomaly IDs use
    `EX001`/`EX002` suffixes. Document this as the current convention or
    change it to the requested per-lead counter before final submission.
2.  **Stage-history gap injection:** the generator deliberately removes
    one `NEEDS_ANALYSIS` event for EX-005. This is an intentional
    exception and should be represented in ground truth and detected by
    validation/anomaly analysis.
3.  **Lifecycle enforcement:** SQL enums constrain allowed status/stage
    values, but do not enforce every valid transition sequence. The
    stage-history validator/application logic must check transition
    order and gaps.
4.  **Routing enforcement:** foreign keys ensure a representative
    exists, but do not enforce that the representative's territory
    equals the lead's territory. The application validator must check
    this; EX-003 deliberately violates it.
5.  **Ground-truth separation:** the V2 ground-truth JSON is written to
    `data/staging/ground_truth_v2/ground_truth.json`; the five injected
    labels are not added as lead scoring columns. Keep this file out of
    scoring feature construction.
6.  **Synthetic outcomes:** the WON/LOST split is determined by score
    rank (top 30% WON), not actual observed conversions. It is a
    benchmark assumption and must be described as synthetic.

## Before submission

-   Keep the SQL schema and this dictionary synchronized whenever
    columns or constraints change.
-   Keep activity enum documentation synchronized with
    `src/database/schema.sql` if activity types change.
-   Remember that `lead_campaigns` is imported separately with
    `scripts/load_lead_campaigns.py`; run it only when the destination
    table is empty.
-   Re-run validation, anomaly analysis and tests after any code/schema
    change.
-   Keep ground truth separate from scoring inputs and preserve the
    generated manifest and validation reports.
