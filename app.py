"""
NGO Beneficiary Progress Assessment System
Flask Backend with SQLite Database and Complete API
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pandas as pd
import sqlite3
import os
from datetime import datetime

from progress_logic import process_beneficiary_data

def assess_data_quality(df):
    """Comprehensive data quality assessment with scoring and alerts"""
    quality_score = 100.0
    quality_flags = []
    alerts = []
    
    # Check for missing values
    missing_critical = df[['attendance', 'skill_before', 'skill_after', 'assessment']].isnull().sum().sum()
    if missing_critical > 0:
        quality_score -= min(20, missing_critical * 2)
        quality_flags.append("Missing critical values")
        alerts.append({
            'type': 'missing_data',
            'severity': 'medium',
            'message': f'{missing_critical} missing values in critical columns',
            'affected_records': missing_critical
        })
    
    # Check for unrealistic values
    unrealistic_attendance = ((df['attendance'] < 0) | (df['attendance'] > 100)).sum()
    unrealistic_skills = ((df['skill_before'] < 0) | (df['skill_before'] > 10) | 
                         (df['skill_after'] < 0) | (df['skill_after'] > 10)).sum()
    unrealistic_assessment = ((df['assessment'] < 0) | (df['assessment'] > 100)).sum()
    
    total_unrealistic = unrealistic_attendance + unrealistic_skills + unrealistic_assessment
    if total_unrealistic > 0:
        quality_score -= min(15, total_unrealistic * 1.5)
        quality_flags.append("Unrealistic values detected")
        alerts.append({
            'type': 'unrealistic_values',
            'severity': 'high',
            'message': f'{total_unrealistic} records with unrealistic values',
            'affected_records': total_unrealistic
        })
    
    # Check for skill regression (skill_after < skill_before)
    skill_regression = (df['skill_after'] < df['skill_before']).sum()
    if skill_regression > len(df) * 0.3:  # More than 30% regression is suspicious
        quality_score -= 10
        quality_flags.append("High skill regression rate")
        alerts.append({
            'type': 'skill_regression',
            'severity': 'medium',
            'message': f'{skill_regression} beneficiaries show skill regression ({skill_regression/len(df)*100:.1f}%)',
            'affected_records': skill_regression
        })
    
    # Check for duplicate names (potential data entry errors)
    duplicates = df['name'].duplicated().sum() if 'name' in df.columns else 0
    if duplicates > 0:
        quality_score -= min(10, duplicates * 2)
        quality_flags.append("Duplicate names found")
        alerts.append({
            'type': 'duplicates',
            'severity': 'low',
            'message': f'{duplicates} duplicate names detected',
            'affected_records': duplicates
        })
    
    # Check for perfect scores (potential data fabrication)
    perfect_scores = ((df['attendance'] == 100) & (df['assessment'] == 100) & 
                     (df['skill_after'] == 10)).sum()
    if perfect_scores > len(df) * 0.1:  # More than 10% perfect scores is suspicious
        quality_score -= 5
        quality_flags.append("Unusually high perfect scores")
        alerts.append({
            'type': 'perfect_scores',
            'severity': 'low',
            'message': f'{perfect_scores} beneficiaries with perfect scores ({perfect_scores/len(df)*100:.1f}%)',
            'affected_records': perfect_scores
        })
    
    return max(0, quality_score), quality_flags, alerts

def calculate_program_effectiveness(conn, program_name, batch_id):
    """Calculate comprehensive program effectiveness metrics"""
    # Get current batch data
    current_df = pd.read_sql_query(
        "SELECT * FROM beneficiaries WHERE program = ? AND upload_batch_id = ?",
        conn, params=[program_name, batch_id]
    )
    
    if len(current_df) == 0:
        return None
    
    # Get historical data for comparison
    historical_df = pd.read_sql_query(
        "SELECT * FROM beneficiaries WHERE program = ? AND upload_batch_id < ?",
        conn, params=[program_name, batch_id]
    )
    
    metrics = {
        'program_name': program_name,
        'upload_batch_id': batch_id,
        'avg_progress': current_df['progress_score'].mean(),
        'total_beneficiaries': len(current_df),
        'improvement_rate': 0.0,
        'retention_rate': 100.0,  # Default for first upload
        'effectiveness_score': 0.0
    }
    
    # Calculate improvement rate (compared to historical average)
    if len(historical_df) > 0:
        historical_avg = historical_df['progress_score'].mean()
        current_avg = current_df['progress_score'].mean()
        metrics['improvement_rate'] = ((current_avg - historical_avg) / historical_avg) * 100
        
        # Calculate retention rate (beneficiaries appearing in multiple uploads)
        if 'beneficiary_id' in current_df.columns and 'beneficiary_id' in historical_df.columns:
            retained = len(set(current_df['beneficiary_id']) & set(historical_df['beneficiary_id']))
            metrics['retention_rate'] = (retained / len(current_df)) * 100
    
    # Calculate effectiveness score (composite metric)
    progress_component = min(metrics['avg_progress'] / 100, 1.0) * 40  # 40% weight
    improvement_component = max(0, min(metrics['improvement_rate'] / 20, 1.0)) * 30  # 30% weight
    retention_component = (metrics['retention_rate'] / 100) * 20  # 20% weight
    risk_component = max(0, 1 - (current_df['risk_level'] == 'Critical Risk').sum() / len(current_df)) * 10  # 10% weight
    
    metrics['effectiveness_score'] = progress_component + improvement_component + retention_component + risk_component
    
    return metrics

app = Flask(__name__)
CORS(app)

# Database setup
DATABASE = 'beneficiaries.db'

def init_db():
    """Initialize SQLite database with enhanced schema for longitudinal tracking"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Enhanced beneficiaries table with longitudinal tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS beneficiaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            beneficiary_id TEXT,  -- Unique identifier across uploads
            name TEXT,
            program TEXT,
            email TEXT,
            phone TEXT,
            attendance REAL,
            skill_before REAL,
            skill_after REAL,
            assessment REAL,
            skill_improvement_score REAL,
            progress_score REAL,
            category TEXT,
            risk_level TEXT,
            risk_reasons TEXT,
            upload_batch_id INTEGER,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_quality_score REAL DEFAULT 100.0,
            data_quality_flags TEXT
        )
    ''')
    
    # Upload batches for longitudinal analysis
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS upload_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            total_records INTEGER,
            avg_progress_score REAL,
            critical_risk_count INTEGER,
            data_quality_issues INTEGER,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    ''')
    
    # Program effectiveness tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS program_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_name TEXT,
            upload_batch_id INTEGER,
            avg_progress REAL,
            total_beneficiaries INTEGER,
            improvement_rate REAL,
            retention_rate REAL,
            effectiveness_score REAL,
            calculated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Data quality alerts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quality_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT,
            severity TEXT,
            message TEXT,
            affected_records INTEGER,
            upload_batch_id INTEGER,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved BOOLEAN DEFAULT FALSE
        )
    ''')
    
    conn.commit()
    conn.close()

@app.route("/")
def home():
    """Serve the main dashboard"""
    return render_template('dashboard.html')

@app.route("/test")
def test_upload():
    """Test upload page"""
    return render_template('test_upload.html')

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "Backend running", "database": "connected"})

@app.route("/api/upload", methods=["POST"])
def upload_file():
    """Enhanced upload with longitudinal tracking and data quality assessment"""
    print("🔥 UPLOAD HIT - Request received!")  # Debug print
    
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    try:
        # Read file based on extension
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
        else:
            return jsonify({"error": "Unsupported file format. Use CSV or Excel"}), 400

    except Exception as e:
        return jsonify({"error": f"Error reading file: {str(e)}"}), 400

    # Validate required columns
    REQUIRED_COLS = {"attendance", "skill_before", "skill_after", "assessment"}
    missing = REQUIRED_COLS - set(df.columns)

    if missing:
        return jsonify({
            "error": f"Missing required columns: {list(missing)}"
        }), 400

    # Add default columns if missing
    if 'name' not in df.columns:
        df['name'] = [f"Beneficiary_{i+1}" for i in range(len(df))]
    if 'program' not in df.columns:
        df['program'] = "General Program"
    if 'email' not in df.columns:
        df['email'] = df['name'].str.lower().str.replace(' ', '.') + '@example.com'
    if 'phone' not in df.columns:
        df['phone'] = [f"+1-555-{1000+i:04d}" for i in range(len(df))]
    
    # Generate beneficiary IDs for longitudinal tracking
    if 'beneficiary_id' not in df.columns:
        df['beneficiary_id'] = df['name'].str.replace(' ', '_') + '_' + df['program'].str.replace(' ', '_')

    # Assess data quality BEFORE cleaning
    original_quality_score, quality_flags, quality_alerts = assess_data_quality(df.copy())

    # Data validation and cleaning
    df["attendance"] = pd.to_numeric(df["attendance"], errors='coerce').clip(0, 100)
    df["assessment"] = pd.to_numeric(df["assessment"], errors='coerce').clip(0, 100)
    df["skill_before"] = pd.to_numeric(df["skill_before"], errors='coerce').clip(0, 10)
    df["skill_after"] = pd.to_numeric(df["skill_after"], errors='coerce').clip(0, 10)

    # Remove rows with missing critical data
    original_count = len(df)
    df = df.dropna(subset=['attendance', 'skill_before', 'skill_after', 'assessment'])
    cleaned_count = len(df)

    if cleaned_count == 0:
        return jsonify({"error": "No valid data rows found after cleaning"}), 400

    # Apply progress logic
    try:
        result_df = process_beneficiary_data(df)
        
        # Add original columns back
        result_df['name'] = df['name'].values
        result_df['program'] = df['program'].values
        result_df['beneficiary_id'] = df['beneficiary_id'].values
        result_df['email'] = df['email'].values
        result_df['phone'] = df['phone'].values
        
    except Exception as e:
        return jsonify({"error": f"Error processing data: {str(e)}"}), 500

    # Store in database with enhanced tracking
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Create upload batch record
        cursor.execute(
            """INSERT INTO upload_batches 
               (filename, total_records, avg_progress_score, critical_risk_count, data_quality_issues) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                file.filename, 
                len(result_df),
                result_df['progress_score'].mean(),
                (result_df['risk_level'] == 'Critical Risk').sum(),
                len(quality_alerts)
            )
        )
        
        batch_id = cursor.lastrowid
        
        # Add batch ID and quality metrics to results
        result_df['upload_batch_id'] = batch_id
        result_df['data_quality_score'] = original_quality_score
        result_df['data_quality_flags'] = ', '.join(quality_flags) if quality_flags else None
        
        # Store processed beneficiary data
        result_df.to_sql('beneficiaries', conn, if_exists='append', index=False)
        
        # Store quality alerts
        for alert in quality_alerts:
            cursor.execute(
                """INSERT INTO quality_alerts 
                   (alert_type, severity, message, affected_records, upload_batch_id) 
                   VALUES (?, ?, ?, ?, ?)""",
                (alert['type'], alert['severity'], alert['message'], 
                 alert['affected_records'], batch_id)
            )
        
        # Calculate and store program effectiveness metrics
        programs = result_df['program'].unique()
        for program in programs:
            metrics = calculate_program_effectiveness(conn, program, batch_id)
            if metrics:
                cursor.execute(
                    """INSERT INTO program_metrics 
                       (program_name, upload_batch_id, avg_progress, total_beneficiaries, 
                        improvement_rate, retention_rate, effectiveness_score) 
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (metrics['program_name'], metrics['upload_batch_id'], 
                     metrics['avg_progress'], metrics['total_beneficiaries'],
                     metrics['improvement_rate'], metrics['retention_rate'], 
                     metrics['effectiveness_score'])
                )
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    # Prepare response with enhanced insights
    response = {
        "message": "File processed successfully",
        "records_processed": len(result_df),
        "records_cleaned": original_count - cleaned_count,
        "filename": file.filename,
        "batch_id": batch_id,
        "data_quality": {
            "score": round(original_quality_score, 1),
            "flags": quality_flags,
            "alerts_count": len(quality_alerts)
        },
        "insights": {
            "avg_progress": round(float(result_df['progress_score'].mean()), 1),
            "critical_risk_count": int((result_df['risk_level'] == 'Critical Risk').sum()),
            "programs_analyzed": len(programs)
        }
    }

    return jsonify(response)

@app.route("/api/dashboard", methods=["GET"])
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        conn = sqlite3.connect(DATABASE)
        
        # Overall stats
        total_beneficiaries = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM beneficiaries", conn
        ).iloc[0]['count']
        
        # Average progress score
        avg_progress = pd.read_sql_query(
            "SELECT AVG(progress_score) as avg_score FROM beneficiaries", conn
        ).iloc[0]['avg_score'] or 0
        
        # Risk distribution
        risk_dist = pd.read_sql_query(
            "SELECT risk_level, COUNT(*) as count FROM beneficiaries GROUP BY risk_level", conn
        )
        
        # Program performance
        program_stats = pd.read_sql_query(
            """SELECT program, 
               AVG(progress_score) as avg_score,
               COUNT(*) as total_beneficiaries,
               SUM(CASE WHEN risk_level = 'Critical Risk' THEN 1 ELSE 0 END) as high_risk_count
               FROM beneficiaries 
               GROUP BY program""", conn
        )
        
        # Category distribution
        category_dist = pd.read_sql_query(
            "SELECT category, COUNT(*) as count FROM beneficiaries GROUP BY category", conn
        )
        
        conn.close()
        
        return jsonify({
            "total_beneficiaries": int(total_beneficiaries),
            "average_progress": round(float(avg_progress), 2),
            "risk_distribution": risk_dist.to_dict('records'),
            "program_performance": program_stats.to_dict('records'),
            "category_distribution": category_dist.to_dict('records')
        })
        
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/api/beneficiaries", methods=["GET"])
def get_beneficiaries():
    """Get beneficiary list with optional filters"""
    try:
        conn = sqlite3.connect(DATABASE)
        
        # Get query parameters
        risk_filter = request.args.get('risk_level')
        program_filter = request.args.get('program')
        limit = request.args.get('limit', 100)
        
        # Build query
        query = "SELECT * FROM beneficiaries WHERE 1=1"
        params = []
        
        if risk_filter:
            query += " AND risk_level = ?"
            params.append(risk_filter)
            
        if program_filter:
            query += " AND program = ?"
            params.append(program_filter)
            
        query += f" ORDER BY progress_score ASC LIMIT {limit}"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return jsonify(df.to_dict('records'))
        
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/api/at-risk", methods=["GET"])
def get_at_risk_beneficiaries():
    """Get list of at-risk beneficiaries"""
    try:
        conn = sqlite3.connect(DATABASE)
        
        df = pd.read_sql_query(
            """SELECT name, program, progress_score, risk_level, risk_reasons 
               FROM beneficiaries 
               WHERE risk_level IN ('Critical Risk', 'Warning')
               ORDER BY progress_score ASC""", conn
        )
        
        conn.close()
        return jsonify(df.to_dict('records'))
        
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/api/analytics/progress-distribution", methods=["GET"])
def get_progress_distribution():
    """Get progress score distribution for histogram"""
    try:
        conn = sqlite3.connect(DATABASE)
        
        df = pd.read_sql_query("SELECT progress_score FROM beneficiaries", conn)
        conn.close()
        
        if len(df) == 0:
            return jsonify({"ranges": [], "counts": []})
        
        # Create bins for histogram
        bins = [0, 20, 40, 60, 80, 100]
        labels = ['0-20', '20-40', '40-60', '60-80', '80-100']
        
        df['range'] = pd.cut(df['progress_score'], bins=bins, labels=labels, include_lowest=True)
        distribution = df['range'].value_counts().sort_index()
        
        return jsonify({
            "ranges": distribution.index.tolist(),
            "counts": distribution.values.tolist()
        })
        
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/api/analytics/indicator-contribution", methods=["GET"])
def get_indicator_contribution():
    """Get indicator contribution breakdown by program"""
    try:
        conn = sqlite3.connect(DATABASE)
        
        df = pd.read_sql_query(
            """SELECT program, 
               AVG(attendance * 0.4) as attendance_contribution,
               AVG(skill_improvement_score * 0.3) as skill_contribution,
               AVG(assessment * 0.3) as assessment_contribution
               FROM beneficiaries 
               GROUP BY program""", conn
        )
        
        conn.close()
        return jsonify(df.to_dict('records'))
        
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/api/analytics/attendance-vs-progress", methods=["GET"])
def get_attendance_vs_progress():
    """Get attendance vs progress scatter plot data"""
    try:
        conn = sqlite3.connect(DATABASE)
        
        df = pd.read_sql_query(
            "SELECT attendance, progress_score, program FROM beneficiaries", conn
        )
        
        conn.close()
        return jsonify(df.to_dict('records'))
        
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/api/analytics/top-at-risk", methods=["GET"])
def get_top_at_risk():
    """Get top 10 at-risk beneficiaries for action prioritization"""
    try:
        conn = sqlite3.connect(DATABASE)
        
        df = pd.read_sql_query(
            """SELECT name, program, email, phone, progress_score, risk_level, risk_reasons,
               attendance, skill_improvement_score, assessment
               FROM beneficiaries 
               WHERE risk_level IN ('Critical Risk', 'Warning')
               ORDER BY progress_score ASC 
               LIMIT 10""", conn
        )
        
        conn.close()
        return jsonify(df.to_dict('records'))
        
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/api/analytics/upload-trends", methods=["GET"])
def get_upload_trends():
    """Get upload trends over time for longitudinal analysis"""
    try:
        conn = sqlite3.connect(DATABASE)
        
        # Get average progress by upload batch
        df = pd.read_sql_query(
            """SELECT 
               DATE(upload_date) as upload_date,
               AVG(progress_score) as avg_progress,
               COUNT(*) as beneficiary_count
               FROM beneficiaries 
               GROUP BY DATE(upload_date)
               ORDER BY upload_date""", conn
        )
        
        conn.close()
        
        # Convert date column to string for JSON serialization
        if not df.empty and 'upload_date' in df.columns:
            df['upload_date'] = df['upload_date'].astype(str)
        
        return jsonify(df.to_dict('records'))
        
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/api/analytics/longitudinal/<beneficiary_id>", methods=["GET"])
def get_beneficiary_trajectory(beneficiary_id):
    """Get individual beneficiary progress trajectory over time"""
    try:
        conn = sqlite3.connect(DATABASE)
        
        df = pd.read_sql_query(
            """SELECT upload_date, progress_score, attendance, 
               skill_improvement_score, assessment, risk_level
               FROM beneficiaries 
               WHERE beneficiary_id = ?
               ORDER BY upload_date""", 
            conn, params=[beneficiary_id]
        )
        
        conn.close()
        
        # Convert datetime column to string for JSON serialization
        if not df.empty and 'upload_date' in df.columns:
            df['upload_date'] = df['upload_date'].astype(str)
        
        return jsonify(df.to_dict('records'))
        
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/api/analytics/program-effectiveness", methods=["GET"])
def get_program_effectiveness():
    """Get comprehensive program effectiveness analysis"""
    try:
        conn = sqlite3.connect(DATABASE)
        
        # Get latest effectiveness metrics for each program
        df = pd.read_sql_query(
            """SELECT pm.program_name, pm.avg_progress, pm.total_beneficiaries,
               pm.improvement_rate, pm.retention_rate, pm.effectiveness_score,
               pm.calculated_date,
               COUNT(DISTINCT b.upload_batch_id) as total_uploads
               FROM program_metrics pm
               JOIN beneficiaries b ON pm.program_name = b.program
               WHERE pm.calculated_date = (
                   SELECT MAX(calculated_date) 
                   FROM program_metrics pm2 
                   WHERE pm2.program_name = pm.program_name
               )
               GROUP BY pm.program_name
               ORDER BY pm.effectiveness_score DESC""", conn
        )
        
        conn.close()
        return jsonify(df.to_dict('records'))
        
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/api/analytics/data-quality", methods=["GET"])
def get_data_quality_overview():
    """Get data quality assessment and alerts"""
    try:
        conn = sqlite3.connect(DATABASE)
        
        # Get quality scores by upload batch (simplified)
        quality_df = pd.read_sql_query(
            """SELECT ub.filename, ub.upload_date, 
               COALESCE(ub.data_quality_issues, 0) as data_quality_issues,
               AVG(COALESCE(b.data_quality_score, 100)) as avg_quality_score
               FROM upload_batches ub
               LEFT JOIN beneficiaries b ON ub.id = b.upload_batch_id
               GROUP BY ub.id, ub.filename, ub.upload_date
               ORDER BY ub.upload_date DESC
               LIMIT 10""", conn
        )
        
        # Get simple alert count
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM quality_alerts WHERE created_date >= date('now', '-30 days')")
        alert_count = cursor.fetchone()[0]
        
        conn.close()
        
        # Convert datetime column to string for JSON serialization
        if not quality_df.empty and 'upload_date' in quality_df.columns:
            quality_df['upload_date'] = quality_df['upload_date'].astype(str)
        
        return jsonify({
            "recent_alerts_count": alert_count,
            "quality_trends": quality_df.to_dict('records')
        })
        
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/api/analytics/explainability/<int:beneficiary_db_id>", methods=["GET"])
def get_score_explainability(beneficiary_db_id):
    """Get detailed score breakdown for transparency"""
    try:
        conn = sqlite3.connect(DATABASE)
        
        df = pd.read_sql_query(
            """SELECT name, program, attendance, skill_improvement_score, 
               assessment, progress_score, risk_level, risk_reasons
               FROM beneficiaries 
               WHERE id = ?""", 
            conn, params=[beneficiary_db_id]
        )
        
        if len(df) == 0:
            return jsonify({"error": "Beneficiary not found"}), 404
        
        beneficiary = df.iloc[0]
        
        # Calculate component contributions
        attendance_contribution = beneficiary['attendance'] * 0.4
        skill_contribution = beneficiary['skill_improvement_score'] * 0.3
        assessment_contribution = beneficiary['assessment'] * 0.3
        
        explanation = {
            "beneficiary": {
                "name": beneficiary['name'],
                "program": beneficiary['program'],
                "final_score": beneficiary['progress_score'],
                "risk_level": beneficiary['risk_level']
            },
            "score_breakdown": {
                "attendance": {
                    "raw_value": beneficiary['attendance'],
                    "weight": 40,
                    "contribution": round(attendance_contribution, 2),
                    "explanation": f"Attendance of {beneficiary['attendance']}% contributes {attendance_contribution:.1f} points (40% weight)"
                },
                "skill_improvement": {
                    "raw_value": beneficiary['skill_improvement_score'],
                    "weight": 30,
                    "contribution": round(skill_contribution, 2),
                    "explanation": f"Skill improvement of {beneficiary['skill_improvement_score']}% contributes {skill_contribution:.1f} points (30% weight)"
                },
                "assessment": {
                    "raw_value": beneficiary['assessment'],
                    "weight": 30,
                    "contribution": round(assessment_contribution, 2),
                    "explanation": f"Assessment score of {beneficiary['assessment']}% contributes {assessment_contribution:.1f} points (30% weight)"
                }
            },
            "risk_analysis": {
                "level": beneficiary['risk_level'],
                "reasons": beneficiary['risk_reasons'],
                "recommendations": generate_recommendations(beneficiary)
            }
        }
        
        conn.close()
        return jsonify(explanation)
        
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

def generate_recommendations(beneficiary):
    """Generate actionable recommendations based on beneficiary data"""
    recommendations = []
    
    if beneficiary['attendance'] < 60:
        recommendations.append("Focus on improving attendance through engagement strategies")
    
    if beneficiary['skill_improvement_score'] <= 0:
        recommendations.append("Reassess training methodology - no skill improvement detected")
    
    if beneficiary['assessment'] < 50:
        recommendations.append("Provide additional learning support and remedial training")
    
    if beneficiary['risk_level'] == 'Critical Risk':
        recommendations.append("Immediate intervention required - consider one-on-one support")
    
    if not recommendations:
        recommendations.append("Continue current approach - beneficiary is progressing well")
    
    return recommendations

@app.route("/api/analytics/decision-insights", methods=["GET"])
def get_decision_insights():
    """Get high-level decision insights for NGO leadership"""
    try:
        conn = sqlite3.connect(DATABASE)
        
        # Program comparison for resource allocation
        program_comparison = pd.read_sql_query(
            """SELECT program, 
               COUNT(*) as total_beneficiaries,
               AVG(progress_score) as avg_progress,
               SUM(CASE WHEN risk_level = 'Critical Risk' THEN 1 ELSE 0 END) as critical_count,
               (SUM(CASE WHEN risk_level = 'Critical Risk' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as critical_rate
               FROM beneficiaries 
               GROUP BY program
               ORDER BY avg_progress DESC""", conn
        )
        
        # Trend analysis
        trend_analysis = pd.read_sql_query(
            """SELECT 
               DATE(upload_date) as period,
               AVG(progress_score) as avg_progress,
               COUNT(*) as beneficiaries,
               SUM(CASE WHEN risk_level = 'Critical Risk' THEN 1 ELSE 0 END) as critical_count
               FROM beneficiaries 
               GROUP BY DATE(upload_date)
               ORDER BY period""", conn
        )
        
        # Resource allocation recommendations
        recommendations = []
        
        if len(program_comparison) > 1:
            best_program = program_comparison.iloc[0]
            worst_program = program_comparison.iloc[-1]
            
            recommendations.append({
                "type": "scale_success",
                "priority": "high",
                "message": f"Scale up '{best_program['program']}' program - highest effectiveness ({best_program['avg_progress']:.1f} avg progress)",
                "action": "increase_funding"
            })
            
            if worst_program['critical_rate'] > 30:
                recommendations.append({
                    "type": "redesign_program",
                    "priority": "high",
                    "message": f"Redesign '{worst_program['program']}' program - {worst_program['critical_rate']:.1f}% critical risk rate",
                    "action": "program_review"
                })
        
        conn.close()
        
        return jsonify({
            "program_comparison": program_comparison.to_dict('records'),
            "trend_analysis": trend_analysis.to_dict('records'),
            "recommendations": recommendations
        })
        
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host='0.0.0.0', port=8000)
