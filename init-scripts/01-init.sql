-- Initialize JARVIS database schema
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Jobs table for job automation
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portal VARCHAR(50) NOT NULL,
    job_id VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    company VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    url TEXT,
    description TEXT,
    salary_range VARCHAR(100),
    experience_level VARCHAR(50),
    job_type VARCHAR(50),
    posted_date TIMESTAMP,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMP,
    application_status VARCHAR(50),
    UNIQUE(portal, job_id)
);

-- Applications table
CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES jobs(id),
    portal VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response TEXT,
    resume_version VARCHAR(100),
    notes TEXT
);

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    message TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'info',
    metadata JSONB,
    sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pinterest automation tables
CREATE TABLE IF NOT EXISTS pinterest_pins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pin_id VARCHAR(255) UNIQUE,
    title VARCHAR(500),
    description TEXT,
    image_url TEXT,
    link_url TEXT,
    board_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    posted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS pinterest_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pin_id VARCHAR(255) REFERENCES pinterest_pins(pin_id),
    impressions BIGINT DEFAULT 0,
    saves BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    engagements BIGINT DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_jobs_portal ON jobs(portal);
CREATE INDEX IF NOT EXISTS idx_jobs_applied ON jobs(applied);
CREATE INDEX IF NOT EXISTS idx_jobs_scraped_at ON jobs(scraped_at);
CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_alerts_channel ON alerts(channel);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_pinterest_pins_status ON pinterest_pins(status);
CREATE INDEX IF NOT EXISTS idx_pinterest_analytics_pin_id ON pinterest_analytics(pin_id);