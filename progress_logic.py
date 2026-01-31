import pandas as pd

# -----------------------------
# 1. Skill Improvement Scoring
# -----------------------------
def skill_improvement_score(before, after, max_level=10):
    """
    Calculates normalized skill improvement score (0–100).
    Negative or zero improvement returns 0.
    """
    improvement = after - before
    if improvement <= 0:
        return 0.0
    return (improvement / max_level) * 100.0


# -----------------------------
# 2. Final Progress Score
# -----------------------------
def calculate_progress_score(attendance, skill_score, assessment):
    """
    Weighted progress score:
    Attendance (40%), Skill Improvement (30%), Assessment (30%)
    """
    return (
        0.4 * attendance +
        0.3 * skill_score +
        0.3 * assessment
    )


# -----------------------------
# 3. Progress Category
# -----------------------------
def progress_category(score):
    if score >= 75:
        return "Excellent"
    elif score >= 50:
        return "Good"
    else:
        return "Needs Support"


# -----------------------------
# 4. Risk Flag Logic
# -----------------------------
def risk_flags(attendance, skill_score, progress_score):
    """
    Rule-based risk detection.
    """
    warnings = []

    if attendance < 60:
        warnings.append("Low Attendance")

    if skill_score == 0:
        warnings.append("No Skill Improvement")

    if progress_score < 50:
        warnings.append("Low Progress Score")

    if len(warnings) >= 2:
        return "Critical Risk", warnings
    elif len(warnings) == 1:
        return "Warning", warnings
    else:
        return "No Risk", warnings


# -----------------------------
# 5. Process CSV / DataFrame
# -----------------------------
def process_beneficiary_data(df):
    """
    Expects columns:
    - attendance (0–100)
    - skill_before (0–10)
    - skill_after (0–10)
    - assessment (0–100)
    """

    results = []

    for _, row in df.iterrows():
        attendance = float(row["attendance"])
        skill_before = float(row["skill_before"])
        skill_after = float(row["skill_after"])
        assessment = float(row["assessment"])

        skill_score = skill_improvement_score(skill_before, skill_after)
        progress_score = calculate_progress_score(
            attendance, skill_score, assessment
        )
        category = progress_category(progress_score)
        risk, reasons = risk_flags(attendance, skill_score, progress_score)

        results.append({
            "attendance": attendance,
            "skill_improvement_score": round(skill_score, 2),
            "assessment": assessment,
            "progress_score": round(progress_score, 2),
            "category": category,
            "risk_level": risk,
            "risk_reasons": ", ".join(reasons)
        })

    return pd.DataFrame(results)


# -----------------------------
# 6. Local Test (RUN THIS)
# -----------------------------
if __name__ == "__main__":
    # Sample test data
    data = {
        "attendance": [85, 65, 55],
        "skill_before": [3, 4, 3],
        "skill_after": [7, 5, 3],
        "assessment": [78, 60, 48]
    }

    df = pd.DataFrame(data)
    output = process_beneficiary_data(df)
    print(output)
