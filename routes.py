import logging

from flask import flash, jsonify, redirect, render_template, request, url_for

from app import app, db
from models import Counter, DemoEntry


@app.route("/")
def index():
    """Main dashboard showing all demo sections"""
    # Get some basic stats
    total_entries = DemoEntry.query.count()
    categories = (
        db.session.query(DemoEntry.category, db.func.count(DemoEntry.id))
        .group_by(DemoEntry.category)
        .all()
    )

    return render_template(
        "index.html", total_entries=total_entries, categories=categories
    )


@app.route("/forms-demo")
def forms_demo():
    """Demo page for form handling"""
    recent_entries = (
        DemoEntry.query.order_by(DemoEntry.created_at.desc()).limit(5).all()
    )
    return render_template("forms_demo.html", recent_entries=recent_entries)


@app.route("/submit-form", methods=["POST"])
def submit_form():
    """Handle form submissions"""
    try:
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        category = request.form.get("category", "general")

        # Basic validation
        if not name or not email:
            flash("Name and email are required!", "error")
            return redirect(url_for("forms_demo"))

        # Create new entry
        entry = DemoEntry(name=name, email=email, message=message, category=category)

        db.session.add(entry)
        db.session.commit()

        flash(f"Thank you {name}! Your submission has been received.", "success")
        logging.info(f"New form submission from {email}")

    except Exception as e:
        logging.error(f"Error processing form submission: {e}")
        flash("An error occurred while processing your submission.", "error")
        db.session.rollback()

    return redirect(url_for("forms_demo"))


@app.route("/api-demo")
def api_demo():
    """Demo page for API endpoints"""
    return render_template("api_demo.html")


@app.route("/api/entries")
def api_entries():
    """API endpoint to get all entries"""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        entries = DemoEntry.query.order_by(DemoEntry.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify(
            {
                "entries": [entry.to_dict() for entry in entries.items],
                "total": entries.total,
                "page": page,
                "pages": entries.pages,
                "has_next": entries.has_next,
                "has_prev": entries.has_prev,
            }
        )
    except Exception as e:
        logging.error(f"Error fetching entries: {e}")
        return jsonify({"error": "Failed to fetch entries"}), 500


@app.route("/api/stats")
def api_stats():
    """API endpoint for statistics"""
    try:
        total_entries = DemoEntry.query.count()
        categories = (
            db.session.query(DemoEntry.category, db.func.count(DemoEntry.id))
            .group_by(DemoEntry.category)
            .all()
        )

        category_data = {cat: count for cat, count in categories}

        return jsonify(
            {
                "total_entries": total_entries,
                "categories": category_data,
                "timestamp": db.func.now(),
            }
        )
    except Exception as e:
        logging.error(f"Error fetching stats: {e}")
        return jsonify({"error": "Failed to fetch statistics"}), 500


@app.route("/charts-demo")
def charts_demo():
    """Demo page for data visualization"""
    return render_template("charts_demo.html")


@app.route("/interactive-demo")
def interactive_demo():
    """Demo page for interactive features"""
    # Get or create counters
    click_counter = Counter.query.filter_by(name="clicks").first()
    if not click_counter:
        click_counter = Counter(name="clicks", value=0)
        db.session.add(click_counter)
        db.session.commit()

    return render_template("interactive_demo.html", click_count=click_counter.value)


@app.route("/api/counter/<action>")
def api_counter(action):
    """API endpoint for counter operations"""
    try:
        counter = Counter.query.filter_by(name="clicks").first()
        if not counter:
            counter = Counter(name="clicks", value=0)
            db.session.add(counter)
            db.session.commit()

        if action == "increment":
            new_value = counter.increment()
            return jsonify({"value": new_value, "action": "incremented"})
        elif action == "get":
            return jsonify({"value": counter.value})
        else:
            return jsonify({"error": "Invalid action"}), 400

    except Exception as e:
        logging.error(f"Error with counter action {action}: {e}")
        return jsonify({"error": "Counter operation failed"}), 500


@app.errorhandler(404)
def not_found(error):
    """Custom 404 error handler"""
    return (
        render_template(
            "base.html",
            page_title="Page Not Found",
            error_message="The page you requested could not be found.",
        ),
        404,
    )


@app.errorhandler(500)
def internal_error(error):
    """Custom 500 error handler"""
    db.session.rollback()
    return (
        render_template(
            "base.html",
            page_title="Server Error",
            error_message="An internal server error occurred.",
        ),
        500,
    )
