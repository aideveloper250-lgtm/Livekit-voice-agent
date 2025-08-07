import asyncio
from flask import Flask, render_template, request, redirect, url_for, flash
from main import make_outbound_call  # adjust import if needed

app = Flask(__name__)
app.secret_key = "REPLACE_WITH_A_RANDOM_SECRET"  # 🔒 keep this secret!

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        phone = request.form["phone"].strip()
        try:
            # your existing call logic
            room_info, sip_info = asyncio.run(make_outbound_call(phone))
            flash(f"Call initiated to {phone}", "success")
        except Exception as e:
            flash(f"Error: {e}", "danger")
        # redirect after POST to avoid resubmission on refresh
        return redirect(url_for("index"))

    # GET → just render form
    return render_template("index.html")


if __name__ == "__main__":
    # debug=False for production; set host=0.0.0.0 so EC2/Nginx can reach it
    app.run(host="0.0.0.0", port=5000, debug=False)
