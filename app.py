import os
import re
import uuid
from pathlib import Path
from difflib import SequenceMatcher
from urllib.parse import urlparse
from PIL import Image,ImageChops

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash
)
from werkzeug.utils import secure_filename

from database import (
    get_db_connection,
    get_brands,
    get_brand,
    save_scan_result,
    init_db
)

app = Flask(__name__)
app.secret_key = os.environ.get(
    "BRANDSHIELD_SECRET_KEY",
    "change-this-development-secret"
)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

init_db()


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def normalize(value):
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def similarity(first, second):
    first = normalize(first)
    second = normalize(second)

    if not first or not second:
        return 0.0

    return round(
        SequenceMatcher(None, first, second).ratio() * 100,
        1
    )
def compare_logo_images(official_path, candidate_path):
    """Return a rough visual similarity percentage."""
    try:
        with Image.open(official_path) as official_img:
            official = official_img.convert("RGB")
            official.thumbnail((128, 128))
            official = official.resize((128, 128))

        with Image.open(candidate_path) as candidate_img:
            candidate = candidate_img.convert("RGB")
            candidate.thumbnail((128, 128))
            candidate = candidate.resize((128, 128))

        difference = ImageChops.difference(official, candidate)
        histogram = difference.histogram()

        total_pixels = 128 * 128 * 3
        total_difference = sum(
            count * (index % 256)
            for index, count in enumerate(histogram)
        )

        mean_difference = total_difference / total_pixels
        score = max(0, 100 * (1 - mean_difference / 255))

        return round(score, 1)

    except (OSError, ValueError):
        return None

def assess_candidate(brand, candidate):
    score = max(
        similarity(brand["brand_name"], candidate),
        similarity(
            brand["official_username"].lstrip("@"),
            candidate.lstrip("@")
        )
    )

    if score >= 85:
        risk = "High"
        action = (
            "Manually verify the account or listing, preserve evidence, "
            "and submit a platform report if impersonation is confirmed."
        )
    elif score >= 60:
        risk = "Medium"
        action = (
            "Review the logo, biography, links, ownership, and "
            "developer details before deciding whether to report."
        )
    else:
        risk = "Low"
        action = (
            "Keep under observation. Similarity alone is not evidence "
            "of impersonation."
        )

    reason = (
        f"The name similarity score is {score}%. "
        "This is an automated name comparison, not proof of fraud."
    )

    return score, risk, reason, action


def record_result(
    brand, scan_type, name, candidate_url, platform
):
    score, risk, reason, action = assess_candidate(brand, name)

    save_scan_result(
        brand["id"],
        scan_type,
        name,
        candidate_url,
        platform,
        risk,
        score,
        reason,
        action
    )

    return {
        "candidate_name": name,
        "candidate_url": candidate_url,
        "platform": platform,
        "similarity_score": score,
        "risk_level": risk,
        "reason": reason,
        "recommended_action": action,
        "status": "Open"
    }


def get_dashboard_stats():
    conn = get_db_connection()

    stats = {
        "total_brands": conn.execute(
            "SELECT COUNT(*) FROM brands"
        ).fetchone()[0],
        "total_scans": conn.execute(
            "SELECT COUNT(*) FROM scan_results"
        ).fetchone()[0],
        "high_risks": conn.execute(
            "SELECT COUNT(*) FROM scan_results "
            "WHERE risk_level = 'High'"
        ).fetchone()[0],
        "open_cases": conn.execute(
            "SELECT COUNT(*) FROM scan_results "
            "WHERE status = 'Open'"
        ).fetchone()[0]
    }

    conn.close()
    return stats


# HOME AND DASHBOARD

@app.route("/")
def index():
    conn = get_db_connection()

    recent_results = conn.execute("""
        SELECT scan_results.*, brands.brand_name
        FROM scan_results
        JOIN brands ON brands.id = scan_results.brand_id
        ORDER BY scan_results.id DESC
        LIMIT 8
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        stats=get_dashboard_stats(),
        recent_results=recent_results
    )


@app.route("/dashboard")
def dashboard():
    return redirect(url_for("index"))


# ABOUT

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/about-page")
def about_page():
    return render_template("about.html")


# BRAND REGISTRATION

@app.route("/brand-profile", methods=["GET", "POST"])
def brand_profile():
    if request.method == "POST":
        brand_name = request.form.get("brand_name", "").strip()
        official_username = request.form.get(
            "official_username", ""
        ).strip()
        official_website = request.form.get(
            "official_website", ""
        ).strip()
        social_usernames = request.form.get(
            "social_usernames", ""
        ).strip()
        official_apps = request.form.get(
            "official_apps", ""
        ).strip()
        brand_identifiers = request.form.get(
            "brand_identifiers", ""
        ).strip()

        if not brand_name or not official_username:
            flash(
                "Brand name and official username are required.",
                "error"
            )
            return redirect(url_for("brand_profile"))

        logo_path = ""

        logo = request.files.get("logo")
        if logo and logo.filename:
            if not allowed_file(logo.filename):
                flash(
                    "Logo must be PNG, JPG, JPEG, or WEBP.",
                    "error"
                )
                return redirect(url_for("brand_profile"))

            filename = secure_filename(logo.filename)
            unique_name = f"{uuid.uuid4().hex}_{filename}"
            logo.save(UPLOAD_DIR / unique_name)
            logo_path = f"uploads/{unique_name}"

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO brands (
                brand_name, official_username,
                official_website, social_usernames,
                official_apps, brand_identifiers, logo_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            brand_name,
            official_username,
            official_website,
            social_usernames,
            official_apps,
            brand_identifiers,
            logo_path
        ))
        conn.commit()
        conn.close()

        flash("Brand registered successfully.", "success")
        return redirect(url_for("brand_profile"))

    return render_template(
        "brand_profile.html",
        brands=get_brands()
    )


# SOCIAL MEDIA MONITORING
# Candidate accounts below are DEMO examples, not live search results.

@app.route("/social-monitoring", methods=["GET", "POST"])
def social_monitoring():
    brands = get_brands()
    candidates = []
    selected_brand = None

    if request.method == "POST":
        brand_id = request.form.get("brand_id", type=int)
        selected_brand = get_brand(brand_id) if brand_id else None

        if not selected_brand:
            flash("Register or select a brand first.", "error")
        else:
            brand_slug = normalize(selected_brand["brand_name"])
            official = normalize(
                selected_brand["official_username"].lstrip("@")
            )

            examples = [
                (f"@{brand_slug}_support_help", "Instagram"),
                (f"@{brand_slug}_offers", "Facebook"),
                (f"official_{brand_slug}_store", "Instagram"),
                (f"{brand_slug}_customer_care", "YouTube"),
                (f"{brand_slug}_deals_online", "X")
            ]

            for username, platform in examples:
                if normalize(username.lstrip("@")) == official:
                    continue

                result = record_result(
                    selected_brand,
                    "Social Media",
                    username,
                    "",
                    platform
                )
                result["demo"] = True
                candidates.append(result)

            flash(
                "Demo comparison complete. These example accounts "
                "have not been found or verified on live platforms.",
                "success"
            )

    return render_template(
        "social_monitoring.html",
        brands=brands,
        selected_brand=selected_brand,
        candidates=candidates
    )


# WEBSITE MONITORING

@app.route("/website-monitoring", methods=["GET", "POST"])
def website_monitoring():
    brands = get_brands()
    result = None
    selected_brand = None

    if request.method == "POST":
        brand_id = request.form.get("brand_id", type=int)
        domain = request.form.get("candidate_domain", "").strip()

        selected_brand = get_brand(brand_id) if brand_id else None

        if not selected_brand:
            flash("Please select a registered brand.", "error")
        elif not domain:
            flash("Enter a candidate website or domain.", "error")
        else:
            parsed = urlparse(
                domain if "://" in domain else "https://" + domain
            )

            if not parsed.hostname or "." not in parsed.hostname:
                flash("Enter a valid domain, such as example.com.", "error")
            else:
                result = record_result(
                    selected_brand,
                    "Website",
                    parsed.hostname,
                    domain,
                    "Website"
                )

                flash(
                    "Domain name comparison complete. Ownership, "
                    "website content, and malicious behavior were "
                    "not verified.",
                    "success"
                )

    return render_template(
        "website_monitoring.html",
        brands=brands,
        selected_brand=selected_brand,
        result=result
    )


# APP MONITORING

@app.route("/app-monitoring", methods=["GET", "POST"])
def app_monitoring():
    brands = get_brands()
    result = None
    selected_brand = None

    if request.method == "POST":
        brand_id = request.form.get("brand_id", type=int)
        candidate_app = request.form.get(
            "candidate_app", ""
        ).strip()
        developer_name = request.form.get(
            "developer_name", ""
        ).strip()
        listing_url = request.form.get(
            "listing_url", ""
        ).strip()

        selected_brand = get_brand(brand_id) if brand_id else None

        if not selected_brand:
            flash("Please select a registered brand.", "error")

        elif not candidate_app:
            flash("Enter the candidate app name.", "error")

        else:
            candidate_logo = request.files.get("candidate_logo")
            candidate_logo_path = ""

            if candidate_logo and candidate_logo.filename:
                if not allowed_file(candidate_logo.filename):
                    flash(
                        "Logo must be PNG, JPG, JPEG, or WEBP.",
                        "error"
                    )
                    return render_template(
                        "app_monitoring.html",
                        brands=brands,
                        selected_brand=selected_brand,
                        result=None
                    )

                unique_name = (
                    f"{uuid.uuid4().hex}_"
                    f"{secure_filename(candidate_logo.filename)}"
                )
                saved_path = UPLOAD_DIR / unique_name
                candidate_logo.save(saved_path)
                candidate_logo_path = f"uploads/{unique_name}"

            logo_score = None
            official_logo_path = (
                BASE_DIR / "static" /
                (selected_brand["logo_path"] or "")
            )

            if candidate_logo_path and official_logo_path.is_file():
                logo_score = compare_logo_images(
                    str(official_logo_path),
                    str(UPLOAD_DIR / Path(candidate_logo_path).name)
                )

            result = record_result(
                selected_brand,
                "Mobile App",
                candidate_app,
                listing_url,
                developer_name or "Developer not supplied"
            )

            result["candidate_logo_path"] = candidate_logo_path
            result["official_logo_path"] = (
                selected_brand["logo_path"] or ""
            )
            result["logo_similarity"] = logo_score

            if logo_score is not None:
                result["logo_note"] = (
                    "Experimental pixel similarity only; "
                    "not proof of copied branding."
                )
            elif not selected_brand["logo_path"]:
                result["logo_note"] = (
                    "Register an official brand logo to enable "
                    "the visual comparison."
                )
            else:
                result["logo_note"] = (
                    "Logo comparison unavailable. Check that both "
                    "images are valid and readable."
                )

            flash(
                "App comparison completed. Verify the actual store "
                "listing and developer before taking action.",
                "success"
            )

    return render_template(
        "app_monitoring.html",
        brands=brands,
        selected_brand=selected_brand,
        result=result
    )

# GENERAL SCAN PAGE

@app.route("/scan")
def scan():
    return render_template("scan.html", brands=get_brands())


# REPORTS

@app.route("/reports")
def reports():
    conn = get_db_connection()

    results = conn.execute("""
        SELECT scan_results.*, brands.brand_name
        FROM scan_results
        JOIN brands ON brands.id = scan_results.brand_id
        ORDER BY scan_results.id DESC
    """).fetchall()

    conn.close()

    return render_template("reports.html", results=results)


# UPDATE REPORT STATUS

@app.route("/update-result/<int:result_id>", methods=["POST"])
def update_result(result_id):
    status = request.form.get("status", "")

    allowed_statuses = {
        "Open", "Under Review", "Resolved", "False Positive"
    }

    if status not in allowed_statuses:
        flash("Invalid report status.", "error")
        return redirect(url_for("reports"))

    conn = get_db_connection()
    conn.execute(
        "UPDATE scan_results SET status = ? WHERE id = ?",
        (status, result_id)
    )
    conn.commit()
    conn.close()

    flash("Report status updated.", "success")
    return redirect(url_for("reports"))


if __name__ == "__main__":
    app.run(debug=True)
