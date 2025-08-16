# Database Migration Guide

## Setup Instructions
1. Install PostgreSQL
2. Create database: `createdb kai_core`
3. Run schema: `psql kai_core < database_schema.sql`

## Migration Commands
- Development: `python manage.py migrate`
- Production: `alembic upgrade head`