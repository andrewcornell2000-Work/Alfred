import traceback
from flask import Flask, render_template, jsonify, request
import aggregator
import backtest as bt
import fetcher
import trade_engine
import institutional_agent
import learning_engine
from config import STOCKS, PORT

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", stocks=STOCKS)


@app.route("/api/analyze/<ticker>")
def analyze(ticker: str):
    ticker = ticker.upper()
    if ticker not in STOCKS:
        return jsonify({"error": f"Unknown ticker '{ticker}'"}), 400
    try:
        return jsonify(aggregator.full_analysis(ticker))
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


@app.route("/api/macro")
def macro():
    try:
        return jsonify(aggregator.macro_analysis())
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


@app.route("/api/backtest/<ticker>")
def backtest(ticker: str):
    ticker = ticker.upper()
    if ticker not in STOCKS:
        return jsonify({"error": f"Unknown ticker '{ticker}'"}), 400
    try:
        return jsonify(bt.run(ticker))
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


@app.route("/api/refresh")
def refresh():
    fetcher.invalidate()
    return jsonify({"status": "cache cleared"})


@app.route("/api/opportunities")
def opportunities():
    try:
        results = [trade_engine.evaluate(t) for t in STOCKS]
        return jsonify({"opportunities": results})
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


@app.route("/api/alerts")
def alerts():
    try:
        return jsonify({"alerts": trade_engine.get_recent_alerts()})
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


@app.route("/api/paper")
def paper():
    try:
        return jsonify(trade_engine.get_paper_stats())
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


@app.route("/api/settings", methods=["GET", "POST"])
def settings():
    try:
        if request.method == "POST":
            data = request.get_json(force=True) or {}
            return jsonify(trade_engine.update_settings(data))
        return jsonify(trade_engine.get_settings())
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


@app.route("/api/institutional/<ticker>")
def institutional(ticker: str):
    ticker = ticker.upper()
    if ticker not in STOCKS:
        return jsonify({"error": f"Unknown ticker '{ticker}'"}), 400
    try:
        opts_score = 0.0
        try:
            analysis = aggregator.full_analysis(ticker)
            opts_score = analysis["options"].get("options_score", 0.0)
        except Exception:
            pass
        return jsonify(institutional_agent.analyze(ticker, opts_score))
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


@app.route("/api/learning")
def learning():
    try:
        return jsonify(learning_engine.get_performance_review())
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


@app.route("/api/learning/recommendations/<int:rec_id>", methods=["POST"])
def learning_recommendation(rec_id: int):
    try:
        action = (request.get_json(force=True) or {}).get("action", "")
        if action == "approve":
            return jsonify(learning_engine.approve_recommendation(rec_id))
        if action == "dismiss":
            return jsonify(learning_engine.dismiss_recommendation(rec_id))
        return jsonify({"error": "action must be 'approve' or 'dismiss'"}), 400
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


if __name__ == "__main__":
    print(f"\n  Quant Intelligence System")
    print(f"  Tracking: {', '.join(STOCKS)}")
    print(f"  Open http://127.0.0.1:{PORT}\n")
    app.run(debug=False, host="0.0.0.0", port=PORT)
