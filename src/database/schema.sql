CREATE DATABASE IF NOT EXISTS lead_management_db;
USE lead_management_db;

-- 1. COMPANY
CREATE TABLE companies (
    company_id VARCHAR(12) PRIMARY KEY,
    company_name VARCHAR(150) NOT NULL,
    industry VARCHAR(80) NOT NULL,
    company_size ENUM('SMB','MID_MARKET','ENTERPRISE') NOT NULL,
    employee_count INT,
    annual_revenue DECIMAL(15,2),
    country VARCHAR(80) NOT NULL,
    state VARCHAR(80),
    city VARCHAR(80),
    website VARCHAR(255),
    created_at DATETIME NOT NULL,
    CHECK (employee_count IS NULL OR employee_count >= 0),
    CHECK (annual_revenue IS NULL OR annual_revenue >= 0)
);

-- 2. CONTACT
CREATE TABLE contacts (
    contact_id VARCHAR(12) PRIMARY KEY,
    company_id VARCHAR(12) NOT NULL,
    first_name VARCHAR(80) NOT NULL,
    last_name VARCHAR(80) NOT NULL,
    email VARCHAR(254) NOT NULL,
    phone VARCHAR(25),
    job_title VARCHAR(100),
    created_at DATETIME NOT NULL,
    UNIQUE KEY uq_contact_email (email),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- 3. CAMPAIGN
CREATE TABLE campaigns (
    campaign_id VARCHAR(12) PRIMARY KEY,
    campaign_name VARCHAR(150) NOT NULL,
    campaign_type ENUM('EMAIL','WEBINAR','SOCIAL','PAID_AD','EVENT','OTHER') NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    budget DECIMAL(14,2) DEFAULT 0,
    status ENUM('PLANNED','ACTIVE','COMPLETED','CANCELLED') NOT NULL,
    CHECK (budget >= 0),
    CHECK (end_date IS NULL OR end_date >= start_date)
);

-- 4. TERRITORY
CREATE TABLE territories (
    territory_id VARCHAR(12) PRIMARY KEY,
    territory_name VARCHAR(100) NOT NULL UNIQUE,
    region VARCHAR(80) NOT NULL,
    country VARCHAR(80) NOT NULL
);

-- 5. PRODUCT
CREATE TABLE products (
    product_id VARCHAR(12) PRIMARY KEY,
    product_name VARCHAR(120) NOT NULL UNIQUE,
    category VARCHAR(80),
    active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 6. SALES REPRESENTATIVE
CREATE TABLE sales_reps (
    sales_rep_id VARCHAR(12) PRIMARY KEY,
    rep_name VARCHAR(120) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    territory_id VARCHAR(12) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (territory_id) REFERENCES territories(territory_id)
);

-- Sales representative and product eligibility (N:M)
CREATE TABLE sales_rep_products (
    sales_rep_id VARCHAR(12) NOT NULL,
    product_id VARCHAR(12) NOT NULL,
    PRIMARY KEY (sales_rep_id, product_id),
    FOREIGN KEY (sales_rep_id) REFERENCES sales_reps(sales_rep_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- 7. LEAD
CREATE TABLE leads (
    lead_id VARCHAR(25) PRIMARY KEY,
    contact_id VARCHAR(12) NOT NULL,
    company_id VARCHAR(12) NOT NULL,
    source ENUM('WEBSITE','EMAIL','REFERRAL','SOCIAL','EVENT','PAID_AD','OTHER') NOT NULL,
    product_id VARCHAR(12) NOT NULL,
    territory_id VARCHAR(12) NOT NULL,
    lead_status ENUM(
        'NEW','QUALIFIED','CONTACTED','NURTURING',
        'CONVERTED','DISQUALIFIED','LOST'
    ) NOT NULL DEFAULT 'NEW',
    fit_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    intent_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    engagement_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    total_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    last_activity_at DATETIME,
    assigned_rep_id VARCHAR(12),
    is_duplicate BOOLEAN NOT NULL DEFAULT FALSE,
    duplicate_of_lead_id VARCHAR(25),
    CHECK (fit_score BETWEEN 0 AND 100),
    CHECK (intent_score BETWEEN 0 AND 100),
    CHECK (engagement_score BETWEEN 0 AND 100),
    CHECK (total_score BETWEEN 0 AND 100),
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (territory_id) REFERENCES territories(territory_id),
    FOREIGN KEY (assigned_rep_id) REFERENCES sales_reps(sales_rep_id),
    FOREIGN KEY (duplicate_of_lead_id) REFERENCES leads(lead_id),
    INDEX idx_lead_score (total_score),
    INDEX idx_lead_status (lead_status),
    INDEX idx_lead_territory (territory_id, product_id),
    INDEX idx_lead_created (created_at)
);

-- 8. CONSENT (preserve consent history)
CREATE TABLE consents (
    consent_id VARCHAR(30) PRIMARY KEY,
    lead_id VARCHAR(25) NOT NULL,
    consent_type ENUM('EMAIL_MARKETING','PHONE_MARKETING','DATA_PROCESSING') NOT NULL,
    consent_status ENUM('GRANTED','REVOKED','PENDING') NOT NULL,
    effective_from DATETIME NOT NULL,
    effective_to DATETIME,
    recorded_at DATETIME NOT NULL,
    source VARCHAR(80),
    CHECK (effective_to IS NULL OR effective_to >= effective_from),
    FOREIGN KEY (lead_id) REFERENCES leads(lead_id),
    INDEX idx_consent_lead (lead_id, consent_type, effective_from)
);

-- 9. SCORE RULE
CREATE TABLE score_rules (
    rule_id VARCHAR(20) PRIMARY KEY,
    rule_name VARCHAR(120) NOT NULL,
    feature_type ENUM('FIT','INTENT','ENGAGEMENT') NOT NULL,
    feature_name VARCHAR(100) NOT NULL,
    weight DECIMAL(6,3) NOT NULL,
    effective_from DATETIME NOT NULL,
    effective_to DATETIME,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (weight >= 0 AND weight <= 1),
    CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

-- 10. ACTIVITY
CREATE TABLE activities (
    activity_id VARCHAR(45) PRIMARY KEY,
    lead_id VARCHAR(25) NOT NULL,
    contact_id VARCHAR(12),
    campaign_id VARCHAR(12),
    activity_type ENUM(
        'EMAIL_SENT','EMAIL_OPENED','EMAIL_CLICKED',
        'WEBSITE_VISIT','PAGE_VIEW','BROCHURE_DOWNLOAD',
        'DEMO_REQUESTED','DEMO_COMPLETED','PHONE_CALL',
        'MEETING','FORM_SUBMITTED','PURCHASE'
    ) NOT NULL,
    activity_timestamp DATETIME NOT NULL,
    activity_value DECIMAL(10,2) DEFAULT 0,
    description VARCHAR(500),
    FOREIGN KEY (lead_id) REFERENCES leads(lead_id),
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id),
    INDEX idx_activity_lead_time (lead_id, activity_timestamp)
);

-- Campaign and lead relationship (N:M)
CREATE TABLE lead_campaigns (
    lead_id VARCHAR(25) NOT NULL,
    campaign_id VARCHAR(12) NOT NULL,
    linked_at DATETIME NOT NULL,
    PRIMARY KEY (lead_id, campaign_id),
    FOREIGN KEY (lead_id) REFERENCES leads(lead_id),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id)
);

-- 11. TASK
CREATE TABLE tasks (
    task_id VARCHAR(45) PRIMARY KEY,
    lead_id VARCHAR(25) NOT NULL,
    assigned_rep_id VARCHAR(12) NOT NULL,
    task_type ENUM('CALL','EMAIL','DEMO','MEETING','FOLLOW_UP') NOT NULL,
    priority ENUM('LOW','MEDIUM','HIGH','URGENT') NOT NULL,
    due_at DATETIME NOT NULL,
    task_status ENUM('PENDING','IN_PROGRESS','COMPLETED','CANCELLED') NOT NULL DEFAULT 'PENDING',
    created_at DATETIME NOT NULL,
    completed_at DATETIME,
    FOREIGN KEY (lead_id) REFERENCES leads(lead_id),
    FOREIGN KEY (assigned_rep_id) REFERENCES sales_reps(sales_rep_id),
    CHECK (completed_at IS NULL OR completed_at >= created_at),
    INDEX idx_task_due (task_status, due_at)
);

-- OPPORTUNITY
CREATE TABLE opportunities (
    opportunity_id VARCHAR(25) PRIMARY KEY,
    lead_id VARCHAR(25) NOT NULL UNIQUE,
    opportunity_name VARCHAR(150) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    opportunity_stage ENUM(
        'QUALIFICATION','NEEDS_ANALYSIS','PROPOSAL',
        'NEGOTIATION','WON','LOST'
    ) NOT NULL,
    created_at DATETIME NOT NULL,
    closed_at DATETIME,
    outcome_reason VARCHAR(255),
    CHECK (amount >= 0),
    CHECK (closed_at IS NULL OR closed_at >= created_at),
    CHECK (
        (opportunity_stage IN ('WON','LOST') AND closed_at IS NOT NULL)
        OR
        (opportunity_stage NOT IN ('WON','LOST'))
    ),
    FOREIGN KEY (lead_id) REFERENCES leads(lead_id),
    INDEX idx_opportunity_stage (opportunity_stage)
);

-- STAGE HISTORY (append-only event history)
CREATE TABLE stage_history (
    stage_history_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    lead_id VARCHAR(25) NOT NULL,
    opportunity_id VARCHAR(25),
    previous_stage VARCHAR(40),
    new_stage VARCHAR(40) NOT NULL,
    changed_at DATETIME NOT NULL,
    changed_by VARCHAR(12),
    change_reason VARCHAR(255),
    FOREIGN KEY (lead_id) REFERENCES leads(lead_id),
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(opportunity_id),
    FOREIGN KEY (changed_by) REFERENCES sales_reps(sales_rep_id),
    INDEX idx_stage_lead_time (lead_id, changed_at)
);