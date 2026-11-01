# Business Rules and Scoring Logic

## 1. Generation configuration

The supplied V2 event generator defines:

-   Seed: `20261022`
-   As-of timestamp: `2026-10-30 12:00:00`
-   Opportunity target: `3,000`
-   Output: `data/staging/generated_v2/`
-   Ground truth: `data/staging/ground_truth_v2/ground_truth.json`

The generator reads master CSV files from `data/generated/`. It does not
write to MySQL.

## 2. Fit score

Fit is calculated from company and product attributes.

-   Company size: SMB = 70, MID_MARKET = 85, ENTERPRISE = 100; unknown =
    40.
-   Industry match: 100 when the company's industry is in the configured
    industry set for the selected product; otherwise 30.
-   Employee count: 0 when \<= 0; 50 when below 50; 70 when below 250;
    85 when below 1,000; otherwise 100.

Formula:

`FIT = 0.40 × company_size_score + 0.35 × industry_match_score + 0.25 × employee_count_score`

Product-industry assumptions are defined in
`src/generators/generate_events.py`.

## 3. Intent score

-   Demo request: 100 points per `DEMO_REQUESTED`, capped at 100.
-   Form submission: 100 points per `FORM_SUBMITTED`, capped at 100.
-   High-intent page proxy: 25 points per `PAGE_VIEW`, capped at 100.

`INTENT = 0.50 × demo_request + 0.30 × form_submission + 0.20 × high_intent_page`

`PAGE_VIEW` is a synthetic proxy, not a verified expression of buying
intent.

## 4. Engagement score

-   Email open: 25 points per event, capped at 100.
-   Email click: 25 points per event, capped at 100.
-   Website visit: 20 points per event, capped at 100.
-   Meeting: 50 points per event, capped at 100.

`ENGAGEMENT = 0.25 × email_open + 0.35 × email_click + 0.20 × website_visit + 0.20 × meeting`

## 5. Overall score and qualification

`TOTAL = 0.35 × FIT + 0.35 × INTENT + 0.30 × ENGAGEMENT`

The generator sorts leads by total score descending, then `lead_id`
ascending. The first 3,000 leads form the qualified cohort. The
tie-breaker makes selection deterministic for a fixed input dataset and
code version.

## 6. Temporal scoring rule

Only activities with timestamps from lead creation through
`min(created_at + 30 days, NOW)` contribute to the initial score. Later
activities remain in the activity dataset for audit/analytics and must
not retroactively change the initial score.

The two deliberately injected post-generation anomaly events are
appended after score calculation.

## 7. Follow-up task rule

The due date is two days after lead creation.

-   Use a CALL task if phone-marketing consent is valid at the due time.
-   Otherwise use an EMAIL task if email-marketing consent is valid at
    the due time.
-   Do not create a task if neither channel is valid.
-   Priority is HIGH when total score \>= 75; otherwise MEDIUM.
-   Task status is PENDING.

## 8. Opportunity selection and outcomes

The top 3,000 qualified leads receive opportunities.

-   The top 30% of the ranked qualified cohort are labelled WON.
-   The remaining 70% are labelled LOST.
-   Ranking is total score descending, with `lead_id` ascending as
    tie-breaker.
-   This is a synthetic benchmark assumption, not an observed sales
    result or an independently measured conversion.

The generator records a reason string for each outcome. Do not describe
these labels as actual customer purchases.

## 9. Opportunity amount

Product base prices:

-   Business Analytics: INR 180,000
-   Cloud Management: INR 240,000
-   CRM Software: INR 150,000

Company-size multipliers:

-   SMB: 1.0
-   MID_MARKET: 2.5
-   ENTERPRISE: 5.0

Amount = product base price × company-size multiplier. When annual
revenue is positive, amount is capped at 1% of annual revenue. The cap
is applied last.

## 10. Consent and injected exception rules

Baseline generation avoids email opens/clicks without valid email
consent or after email consent revocation. It similarly avoids phone
calls without valid phone consent or after revocation.

Five labelled exceptions are added after baseline score calculation:

-   EX-001: opted-out lead contacted.
-   EX-002: post-conversion activity.
-   EX-003: lead assigned outside territory.
-   EX-004: duplicate opportunity attempt, recorded as rejected.
-   EX-005: missing stage-history transition.

See `ground_truth_documentation.md` for the labels and expected
decisions.
