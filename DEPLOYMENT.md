# Deployment Guide - NGO Beneficiary Progress Assessment System

## Quick Start (5 Minutes)

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Installation Steps

1. **Clone/Download the Project**
   ```bash
   # If using git
   git clone <repository-url>
   cd sevathon
   
   # Or download and extract the ZIP file
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Application**
   ```bash
   python app.py
   ```

4. **Access the Dashboard**
   - Open your web browser
   - Navigate to: `http://localhost:5000`
   - You should see the NGO Beneficiary Progress Dashboard

## Testing with Sample Data

1. **Upload Sample Data**
   - Click "Choose File" on the dashboard
   - Select `sample_data.csv` from the project folder
   - Wait for processing confirmation

2. **Explore the Dashboard**
   - View statistics cards (total beneficiaries, average progress, at-risk count)
   - Examine charts (risk distribution, progress categories, program performance)
   - Review the at-risk beneficiaries table

## Production Deployment

### Option 1: Local Server Deployment

1. **Install Production WSGI Server**
   ```bash
   pip install gunicorn
   ```

2. **Run with Gunicorn**
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

3. **Configure Firewall** (if needed)
   ```bash
   # Allow port 5000
   sudo ufw allow 5000
   ```

### Option 2: Docker Deployment

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.9-slim
   
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY . .
   
   EXPOSE 5000
   CMD ["python", "app.py"]
   ```

2. **Build and Run**
   ```bash
   docker build -t ngo-dashboard .
   docker run -p 5000:5000 ngo-dashboard
   ```

### Option 3: Cloud Deployment (Heroku)

1. **Create Procfile**
   ```
   web: gunicorn app:app
   ```

2. **Deploy to Heroku**
   ```bash
   heroku create your-ngo-dashboard
   git push heroku main
   ```

## Configuration Options

### Environment Variables

Create a `.env` file for configuration:
```
FLASK_ENV=production
DATABASE_URL=sqlite:///beneficiaries.db
MAX_UPLOAD_SIZE=16777216  # 16MB
DEBUG=False
```

### Database Configuration

For production, consider upgrading to PostgreSQL:
```python
# In app.py, replace SQLite with PostgreSQL
import psycopg2
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///beneficiaries.db')
```

## Security Hardening

### 1. File Upload Security
```python
# Add to app.py
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB limit
```

### 2. HTTPS Configuration
```bash
# Use SSL certificate
gunicorn --certfile=cert.pem --keyfile=key.pem -b 0.0.0.0:443 app:app
```

### 3. Access Control
```python
# Add basic authentication if needed
from flask_httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    return username == 'admin' and password == 'secure_password'
```

## Monitoring and Maintenance

### 1. Log Configuration
```python
import logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
```

### 2. Database Backup
```bash
# Backup SQLite database
cp beneficiaries.db backup_$(date +%Y%m%d).db

# Automated backup script
#!/bin/bash
sqlite3 beneficiaries.db ".backup backup_$(date +%Y%m%d_%H%M%S).db"
```

### 3. Health Monitoring
```bash
# Check application health
curl http://localhost:5000/health
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Find process using port 5000
   lsof -i :5000
   # Kill the process
   kill -9 <PID>
   ```

2. **Permission Denied**
   ```bash
   # Fix file permissions
   chmod +x app.py
   ```

3. **Module Not Found**
   ```bash
   # Reinstall dependencies
   pip install -r requirements.txt --force-reinstall
   ```

4. **Database Locked**
   ```bash
   # Remove database file and restart
   rm beneficiaries.db
   python app.py
   ```

### Performance Optimization

1. **Large File Handling**
   - Process files in chunks for datasets > 10,000 records
   - Implement progress indicators for long uploads

2. **Database Optimization**
   - Add indexes for frequently queried columns
   - Consider database connection pooling

3. **Caching**
   - Implement Redis for dashboard statistics caching
   - Cache processed results for repeated queries

## Backup and Recovery

### Automated Backup Script
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
sqlite3 beneficiaries.db ".backup backups/backup_$DATE.db"
echo "Backup created: backup_$DATE.db"
```

### Recovery Process
```bash
# Restore from backup
cp backups/backup_YYYYMMDD_HHMMSS.db beneficiaries.db
python app.py
```

## Support and Maintenance

- **Log Files**: Check `app.log` for error messages
- **Database**: SQLite file located at `beneficiaries.db`
- **Uploads**: Temporary files cleaned automatically
- **Updates**: Pull latest code and restart application

For technical support, refer to the project documentation or contact the development team.