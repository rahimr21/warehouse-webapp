# Database Migrations

This application uses Flask-Migrate to handle database schema changes safely without losing data.

## Available Commands

### Initialize Migration Repository
```bash
python -m flask db init
```
*Note: This is a one-time setup that has already been completed.*

### Create a New Migration
When you make changes to the database models in `app.py`, create a migration:
```bash
python -m flask db migrate -m "Description of changes"
```

### Apply Migrations
To update your database with the latest changes:
```bash
python -m flask db upgrade
```

### Assign Container Numbers to Existing Containers (Optional)
If you want to assign tracking numbers to containers that don't have them:
```bash
python -m flask assign-container-numbers
```
*Note: Container numbers are optional and only needed for tracking shipping containers.*

### Other Useful Commands

#### Check Migration Status
```bash
python -m flask db current
```

#### View Migration History
```bash
python -m flask db history
```

#### Downgrade Database (if needed)
```bash
python -m flask db downgrade
```

## How to Update Database Schema

1. Make your changes to the models in `app.py`
2. Create a migration: `python -m flask db migrate -m "Your description"`
3. Review the generated migration file in `migrations/versions/`
4. Apply the migration: `python -m flask db upgrade`

## Important Notes

- Always backup your database before applying migrations in production
- Review migration files before applying them
- Test migrations on a copy of your data first
- The `migrations/` folder should be included in version control

## Container Numbers Feature

Container numbers are **optional** fields used for tracking actual shipping containers. The main identifier for containers in the system is the container name. Container numbers can be added when needed for external tracking purposes (e.g., shipping company container numbers like "MSKU1234567"). 