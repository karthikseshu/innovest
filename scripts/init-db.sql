-- PostgreSQL initialization script for Email Transaction Parser
-- This script creates the database and initial tables

-- Create database if it doesn't exist (this will be handled by docker-compose)
-- CREATE DATABASE email_parser;

-- Connect to the database
\c email_parser;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Note: The actual table creation will be handled by SQLAlchemy models
-- This script can be used for any additional database setup needed
