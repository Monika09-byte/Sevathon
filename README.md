# Sevathon
# NGO Beneficiary Progress Assessment System

A comprehensive system for NGOs to objectively evaluate program impact through beneficiary progress tracking and risk assessment.

## Features

- **Data Upload**: CSV/Excel file processing with automatic validation and cleaning
- **Progress Scoring**: Weighted matrix calculation for unified beneficiary assessment
- **Risk Assessment**: Automatic categorization of at-risk and high-risk beneficiaries
- **Dashboard**: Real-time visualization of program performance and beneficiary status
- **Database**: SQLite storage for auditability and scalability

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**
   ```bash
   python app.py
   ```

3. **Access Dashboard**
   Open http://localhost:5000 in your browser

4. **Upload Sample Data**
   Use the provided `sample_data.csv` to test the system

## Data Format

Your CSV/Excel files should contain these columns:
- `name`: Beneficiary name
- `program`: Program name
- `attendance`: Attendance percentage (0-100)
- `skill_improvement`: Skill improvement score (0-100)
- `assessment_score`: Assessment score (0-100)

## Scoring Methodology

The system uses a weighted progress matrix as per technical workflow:
- **Attendance**: 40% weight
- **Skill Improvement**: 30% weight  
- **Assessment Score**: 30% weight

**Formula**: `Progress Score = (Attendance × 0.4) + (Skill Improvement × 0.3) + (Assessment Score × 0.3)`

## Risk Flag Logic

Multi-criteria risk assessment rules:
1. **Progress score < 50** → High Risk
2. **Attendance < 60%** → At Risk
3. **Skill improvement ≤ 0** → At Risk
4. **Otherwise** → Normal

## Technical Workflow (Step-by-Step)

1️⃣ **Data Ingestion**
- User uploads Excel/CSV file
- Flask API receives file
- Pandas loads data into DataFrame

2️⃣ **Data Preprocessing**
- Handle missing values
- Normalize values to 0–100 scale
- Validate required columns

3️⃣ **Progress Matrix Application**
- Apply weighted formula: `(Attendance × 0.4) + (Skill × 0.3) + (Assessment × 0.3)`

4️⃣ **Risk Flag Logic**
- Apply multi-criteria rules for risk categorization

5️⃣ **Data Storage**
- Store raw data, calculated scores, risk category in SQLite

6️⃣ **Dashboard Data API**
- Flask sends processed data as JSON
- Frontend fetches data via API calls

7️⃣ **Visualization & Reporting**
- Charts display average progress, program performance, risk distribution
- Table lists at-risk beneficiaries

🔁 **End-to-End Flow**: Excel Upload → Data Cleaning → Matrix Scoring → Risk Flagging → Dashboard Visualization

## API Endpoints

- `POST /api/upload` - Upload and process beneficiary data
- `GET /api/dashboard` - Get dashboard statistics
- `GET /api/beneficiaries` - Get beneficiary list with filters

## Technical Architecture

- **Backend**: Flask with Pandas for data processing
- **Database**: SQLite for lightweight storage
- **Frontend**: HTML/CSS/JavaScript with Chart.js
- **File Processing**: Support for CSV and Excel formats

## Deployment

The system is designed for easy deployment in NGO environments:
1. Minimal dependencies
2. Lightweight SQLite database
3. Self-contained Flask application
4. Responsive web interface

## Customization

You can modify scoring weights and risk thresholds in the `DataProcessor` class in `app.py`:

```python
self.weights = {
    'attendance': 0.4,        # 40%
    'skill_improvement': 0.3, # 30%
    'assessment_score': 0.3   # 30%
}

# Risk rules:
# 1. Progress score < 50 → High Risk
# 2. Attendance < 60% → At Risk  
# 3. Skill improvement ≤ 0 → At Risk
```