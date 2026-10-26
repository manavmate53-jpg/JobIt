"""Lightweight local-first dashboard for JobIt."""

from __future__ import annotations

import os
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request, send_file
from src.tracker_db import TrackerDB

app = Flask(__name__)
db = TrackerDB()

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JobIt | Candidate Pipeline & Application Tracker</title>
<style>
  :root {
    --bg-primary: #0b0f19;
    --bg-card: #111827;
    --border: #1f2937;
    --text-primary: #f9fafb;
    --text-secondary: #9ca3af;
    --accent: #38bdf8;
    --accent-hover: #0284c7;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  body { background: var(--bg-primary); color: var(--text-primary); padding: 24px; line-height: 1.5; }
  .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 16px; }
  .logo { font-size: 24px; font-weight: 800; color: var(--accent); letter-spacing: -0.5px; }
  .candidate-badge { font-size: 13px; color: var(--text-secondary); background: #1e293b; padding: 6px 12px; border-radius: 9999px; }
  .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 14px; margin-bottom: 28px; }
  .metric-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 14px; text-align: center; }
  .metric-value { font-size: 26px; font-weight: 800; color: var(--text-primary); }
  .metric-label { font-size: 12px; text-transform: uppercase; color: var(--text-secondary); letter-spacing: 0.5px; margin-top: 4px; }
  .section-title { font-size: 18px; font-weight: 700; margin-bottom: 14px; }
  .table-container { background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; text-align: left; font-size: 13.5px; }
  th { background: #182234; padding: 12px 16px; color: #cbd5e1; font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; border-bottom: 1px solid var(--border); }
  td { padding: 12px 16px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:hover { background: #172033; }
  .badge { display: inline-block; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
  .badge-apply { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #059669; }
  .badge-consider { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #d97706; }
  .badge-skip { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #dc2626; }
  .score-pill { font-weight: 800; font-size: 14px; }
  .score-high { color: #34d399; }
  .score-med { color: #fbbf24; }
  .score-low { color: #f87171; }
  .btn { display: inline-block; background: var(--accent); color: #0b0f19; font-weight: 600; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 12px; transition: background 0.2s; }
  .btn:hover { background: var(--accent-hover); }
  .btn-outline { background: transparent; border: 1px solid var(--border); color: #cbd5e1; }
  .btn-outline:hover { background: #1f2937; }
</style>
</head>
<body>
  <div class="header">
    <div class="logo">⚡ JobIt Pipeline Dashboard</div>
    <div class="candidate-badge">Candidate: <strong>Manav Mate</strong> | Product Manager (0-3 yrs)</div>
  </div>

  <div class="metrics-grid">
    {% for status, count in stats.items() %}
    <div class="metric-card">
      <div class="metric-value">{{ count }}</div>
      <div class="metric-label">{{ status }}</div>
    </div>
    {% endfor %}
  </div>

  <div class="section-title">Active Applications & Scored Pipeline</div>
  <div class="table-container">
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Company</th>
          <th>Role</th>
          <th>Location</th>
          <th>Source</th>
          <th>Fit Score</th>
          <th>Decision</th>
          <th>Status</th>
          <th>HR Contact</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {% for app in applications %}
        <tr>
          <td>#{{ app.id }}</td>
          <td><strong>{{ app.company }}</strong></td>
          <td>{{ app.role }}</td>
          <td>{{ app.location }}</td>
          <td>{{ app.source }}</td>
          <td>
            <span class="score-pill {% if app.fit_score >= 75 %}score-high{% elif app.fit_score >= 55 %}score-med{% else %}score-low{% endif %}">
              {{ app.fit_score }}
            </span>
          </td>
          <td>
            <span class="badge {% if app.decision == 'APPLY' %}badge-apply{% elif app.decision == 'CONSIDER' %}badge-consider{% else %}badge-skip{% endif %}">
              {{ app.decision }}
            </span>
          </td>
          <td>{{ app.status }}</td>
          <td>{{ app.hr_name or 'Unassigned' }}</td>
          <td>
            <a href="{{ app.job_url }}" target="_blank" class="btn btn-outline">View Post</a>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

@app.route("/")
def dashboard():
    stats = db.get_pipeline_stats()
    applications = db.get_all_applications()
    return render_template_string(DASHBOARD_HTML, stats=stats, applications=applications)

@app.route("/api/applications")
def api_applications():
    apps = db.get_all_applications()
    return jsonify(apps)

@app.route("/api/stats")
def api_stats():
    return jsonify(db.get_pipeline_stats())

def run_dashboard(port: int = 5000):
    print(f"Starting JobIt Dashboard on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
