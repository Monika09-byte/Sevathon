"""
CSV INPUT CONTRACT:
Required columns:
- attendance (0-100)
- skill_before (0-10)
- skill_after (0-10)
- assessment (0-100)
"""

from flask import Flask, request, jsonify
import pandas as pd

from progress_logic import process_beneficiary_data

app = Flask(__name__)


@app.route("/")
def home():
    return "Sevathon Backend Running"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "Backend running"})


@app.route("/upload", methods=["POST"])
def upload_csv():
    # 1️. Check if file exists
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    # 2️. Read CSV safely
    try:
        df = pd.read_csv(file)
    except Exception:
        return jsonify({"error": "Invalid CSV file"}), 400

    # 3️.Validate required columns
    REQUIRED_COLS = {"attendance", "skill_before", "skill_after", "assessment"}
    missing = REQUIRED_COLS - set(df.columns)

    if missing:
        return jsonify({
            "error": f"Missing required columns: {list(missing)}"
        }), 400

    # 4️.Clamp values to safe ranges (demo-safe)
    df["attendance"] = df["attendance"].clip(0, 100)
    df["assessment"] = df["assessment"].clip(0, 100)
    df["skill_before"] = df["skill_before"].clip(0, 10)
    df["skill_after"] = df["skill_after"].clip(0, 10)

    # 5️.Apply progress logic
    try:
        result_df = process_beneficiary_data(df)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # 6️.Return JSON response
    return jsonify(result_df.to_dict(orient="records"))


if __name__ == "__main__":
    app.run(debug=True)
