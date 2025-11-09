# Admin CLI Quick Reference

Command-line tool for managing AX5 plotter users.

## Installation

```bash
chmod +x scripts/admin.py
pip install click tabulate  # If not already installed
```

## Commands

### Create User

```bash
# Interactive
python scripts/admin.py create

# With options
python scripts/admin.py create --username john --email john@example.com --password SecurePass123

# Create admin
python scripts/admin.py create --admin
```

### List Users

```bash
python scripts/admin.py list
```

Output:
```
╔════╤═══════════╤═══════════════════╤════════╤═══════╤══════╤════════╤════════════╗
║ ID │ Username  │ Email             │ Active │ Admin │ Jobs │ Time   │ Created    ║
╠════╪═══════════╪═══════════════════╪════════╪═══════╪══════╪════════╪════════════╣
║  1 │ admin     │ admin@example.com │ ✓      │ ✓     │ 142  │ 245.3m │ 2025-01-15 ║
║  2 │ john      │ john@example.com  │ ✓      │       │ 23   │ 45.2m  │ 2025-01-20 ║
╚════╧═══════════╧═══════════════════╧════════╧═══════╧══════╧════════╧════════════╝
```

### User Info

```bash
python scripts/admin.py info john
```

### Reset Password

```bash
python scripts/admin.py reset-password john
```

### Reset API Key

```bash
python scripts/admin.py reset-api-key john
```

### Set Rate Limits

```bash
# Set all limits
python scripts/admin.py set-limits john --jobs-per-hour 20 --jobs-per-day 100 --max-duration 7200

# Set individual limits
python scripts/admin.py set-limits john --jobs-per-hour 50
```

### Modify Permissions

```bash
# Disable user
python scripts/admin.py modify john --inactive

# Enable user
python scripts/admin.py modify john --active

# Make admin
python scripts/admin.py modify john --admin

# Remove admin
python scripts/admin.py modify john --no-admin
```

### Delete User

```bash
python scripts/admin.py delete john
```

## Common Tasks

### Initial Setup

```bash
# 1. System creates default admin on first run
# Check logs for API key

# 2. Change admin password immediately
python scripts/admin.py reset-password admin

# 3. Create regular users
python scripts/admin.py create
```

### User Management

```bash
# Add new user
python scripts/admin.py create --username artist1 --email artist1@example.com

# Increase limits for power user
python scripts/admin.py set-limits artist1 --jobs-per-hour 50 --jobs-per-day 200

# Temporarily disable problematic user
python scripts/admin.py modify spammer --inactive

# Re-enable after investigation
python scripts/admin.py modify spammer --active
```

### Troubleshooting

```bash
# Check user's API key
python scripts/admin.py info username

# Reset if compromised
python scripts/admin.py reset-api-key username

# Check all users and their usage
python scripts/admin.py list
```

## Security Tips

1. **Strong Passwords**: Enforce minimum 12 characters
2. **API Key Rotation**: Reset keys periodically or after suspected compromise
3. **Monitor Usage**: Check `list` regularly for unusual activity
4. **Disable Inactive**: Disable unused accounts
5. **Admin Access**: Limit number of admin users

## Automation Examples

### Bulk User Creation

```bash
#!/bin/bash
# create_users.sh

while IFS=, read -r username email; do
    password=$(openssl rand -base64 12)
    python scripts/admin.py create \
        --username "$username" \
        --email "$email" \
        --password "$password"
    echo "$username,$email,$password" >> user_credentials.csv
done < users.csv
```

### Daily Usage Report

```bash
#!/bin/bash
# daily_report.sh

python scripts/admin.py list > reports/users_$(date +%Y%m%d).txt
```

Add to crontab:
```bash
crontab -e
# Add: 0 0 * * * /path/to/daily_report.sh
```

## Database Direct Access (Advanced)

For complex queries, access SQLite directly:

```bash
sqlite3 users.db "SELECT username, total_jobs, total_plot_time FROM users ORDER BY total_plot_time DESC LIMIT 10;"
```

Common queries:
```sql
-- Most active users
SELECT username, total_jobs FROM users ORDER BY total_jobs DESC LIMIT 10;

-- Users created in last week
SELECT username, email, created_at FROM users WHERE created_at > date('now', '-7 days');

-- Inactive users (no login in 30 days)
SELECT username, last_login FROM users WHERE last_login < date('now', '-30 days') OR last_login IS NULL;

-- Total plotting time by user
SELECT username, ROUND(total_plot_time/3600, 2) as hours FROM users ORDER BY total_plot_time DESC;
```

## Backup & Restore

### Backup

```bash
# Backup database
cp users.db backups/users_$(date +%Y%m%d).db

# Or dump to SQL
sqlite3 users.db .dump > backups/users_$(date +%Y%m%d).sql
```

### Restore

```bash
# From database file
cp backups/users_YYYYMMDD.db users.db

# From SQL dump
sqlite3 users.db < backups/users_YYYYMMDD.sql
```

---

**Need help?** Run: `python scripts/admin.py --help`
