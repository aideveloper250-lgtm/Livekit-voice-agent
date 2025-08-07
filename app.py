import asyncio
from flask import Flask, request, render_template
from main import make_outbound_call  # adjust if needed

app = Flask(__name__)

@app.route("/", methods=["GET","POST"])
def index():
    msg = None
    alert_type = "success"
    if request.method == "POST":
        phone = request.form["phone"].strip()
        try:
            room_info, sip_info = asyncio.run(make_outbound_call(phone))
            msg = f"Call initiated to {phone}"
        except Exception as e:
            msg = f"Error: {e}"
            alert_type = "danger"
    return render_template("index.html", msg=msg, alert_type=alert_type)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
