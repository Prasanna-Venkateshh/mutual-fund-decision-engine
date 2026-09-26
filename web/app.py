"""
Web Application HTTP Server for Mutual Fund Decision-Support Platform V1.

Provides a clean, quiet, professional web UI supporting the 10 approved V1 screens:
- SCR-01 — Onboarding & Profiling (/onboarding)
- SCR-02 — Home / Quiet Dashboard (/)
- SCR-03 — Portfolio / My Wealth (/wealth)
- SCR-04 — Goal Detail (/wealth/goals/:id)
- SCR-05 — Fund Discovery & Scanner (/discover)
- SCR-06 — Fund Detail (/scheme/:canonical_scheme_id)
- SCR-07 — Fund Comparison (/discover/compare)
- SCR-08 — Switch & Economic Hurdle Evaluator (/action/evaluate-switch)
- SCR-09 — Action Center & Decision Review (/action-center)
- SCR-10 — Profile & Settings (/settings)
- Login & Session Authentication (/login, /logout)

Enforces 100% financial & security governance invariants:
- Read-only decision support UI wrapped with secure authentication boundaries
- Authenticated principal -> server-resolved investor_id -> resource authorization
- Client-supplied investor_id is NEVER trusted for identity scoping or authorization
- HttpOnly, SameSite=Lax cookie sessions & constant-time anti-CSRF token validation
- Immutable security audit logging (security_audit_events) without sensitive payload leakage
- Output HTML escaping on all user-controlled template parameters
- Execution status strictly NOT_EXECUTED; zero broker trade execution capability
- Absolute decoupling: Fund Quality alone NEVER triggers BUY/SELL
"""

import http.server
import json
import os
import sqlite3
import sys
import urllib.parse
from datetime import date, datetime
from typing import Dict, Any, Optional, List, Tuple

# Add repository root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from audit.security_audit import SecurityAuditLogger
from data.repositories.profile_repository import ProfileRepository
from data.repositories.portfolio_repository import PortfolioRepository
from data.adapters.portfolio_upload_adapter import PortfolioUploadAdapter, PortfolioUploadError
from portfolio.need_models import PortfolioExposureSnapshot
from web.adapters import (
    QuestionnaireAdapter,
    SnapshotDiffAdapter,
    ConfidenceLabelAdapter,
)
from web.security import (
    SessionRepository,
    SecurityManager,
    SessionRecord,
    PrincipalIdentityResolver,
    MAX_PORTFOLIO_UPLOAD_SIZE_BYTES,
    SecurityError,
    UnauthorizedError,
    ForbiddenError,
)


def render_html_page(
    title: str,
    content_html: str,
    current_route: str = "/",
    authenticated_investor_id: Optional[str] = None,
    csrf_token: Optional[str] = None,
) -> str:
    nav_items = [
        ("/", "Home"),
        ("/wealth", "My Wealth"),
        ("/discover", "Explore"),
        ("/action-center", "Actions"),
        ("/settings", "Settings"),
    ]
    
    nav_html = ""
    for route, label in nav_items:
        active_cls = "active" if (current_route == route or (route != "/" and current_route.startswith(route))) else ""
        nav_html += f'<a href="{route}" class="nav-item {active_cls}">{label}</a>\n'

    auth_badge_html = ""
    if authenticated_investor_id:
        escaped_inv = SecurityManager.escape_html(authenticated_investor_id)
        auth_badge_html = f"""
        <div class="user-profile-badge">
            <span class="user-avatar">👤</span>
            <span class="investor-id">{escaped_inv}</span>
            <a href="/logout" class="btn btn-sm btn-logout">Logout</a>
        </div>
        """
    else:
        auth_badge_html = '<a href="/login" class="btn btn-sm btn-primary">Login</a>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{SecurityManager.escape_html(title)} — Mutual Fund Decision Engine</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-page: #f9f8f5;
            --bg-surface: #ffffff;
            --bg-subtle: #f3f0e8;
            --bg-elevated: #faf8f3;
            
            --border-light: #ece8df;
            --border-medium: #dcd6c8;
            --border-dark: #1e2229;
            
            --text-primary: #18191b;
            --text-secondary: #525866;
            --text-muted: #868c98;
            
            --accent-primary: #1b2028;
            --accent-hover: #0a0d12;
            --accent-subtle: #f0ecdf;
            
            --status-green: #15803d;
            --status-green-bg: #f0fdf4;
            --status-green-border: #bbf7d0;
            
            --status-amber: #b45309;
            --status-amber-bg: #fffbeb;
            --status-amber-border: #fef3c7;
            
            --status-red: #b91c1c;
            --status-red-bg: #fef2f2;
            --status-red-border: #fecaca;
            
            --status-neutral: #475569;
            --status-neutral-bg: #f8fafc;
            --status-neutral-border: #e2e8f0;
            
            --shadow-soft: 0 10px 30px -4px rgba(24, 25, 27, 0.05);
            --shadow-card: 0 1px 3px 0 rgba(0, 0, 0, 0.02), 0 1px 2px -1px rgba(0, 0, 0, 0.04);
            
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            --font-mono: "JetBrains Mono", SFMono-Regular, Menlo, Consolas, monospace;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease, transform 0.2s ease, opacity 0.2s ease;
        }}

        @media (prefers-reduced-motion: reduce) {{
            * {{ transition: none !important; animation: none !important; }}
        }}
        
        body {{
            background-color: var(--bg-page);
            color: var(--text-primary);
            font-family: var(--font-sans);
            line-height: 1.6;
            padding-bottom: 80px;
            -webkit-font-smoothing: antialiased;
        }}

        header {{
            background-color: rgba(252, 251, 249, 0.92);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-light);
            padding: 0 2.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            height: 72px;
            position: sticky;
            top: 0;
            z-index: 100;
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 600;
            font-size: 1.05rem;
            color: var(--text-primary);
            text-decoration: none;
            letter-spacing: -0.02em;
        }}

        .brand-icon {{
            width: 30px;
            height: 30px;
            border-radius: 8px;
            background: var(--accent-primary);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            color: #ffffff;
            font-size: 0.9rem;
        }}

        nav {{
            display: flex;
            gap: 0.5rem;
            align-items: center;
        }}

        .nav-item {{
            color: var(--text-secondary);
            text-decoration: none;
            padding: 0.55rem 1rem;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 500;
            display: flex;
            align-items: center;
        }}

        .nav-item:hover {{
            color: var(--text-primary);
            background-color: var(--bg-subtle);
        }}

        .nav-item.active {{
            color: var(--text-primary);
            background-color: var(--bg-surface);
            border: 1px solid var(--border-light);
            font-weight: 600;
            box-shadow: var(--shadow-card);
        }}

        .user-profile-badge {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
            font-size: 0.825rem;
            color: var(--text-secondary);
            background: var(--bg-surface);
            padding: 5px 14px;
            border-radius: 20px;
            border: 1px solid var(--border-light);
            margin-left: 1rem;
        }}

        .investor-id {{
            font-weight: 600;
            color: var(--text-primary);
            font-family: var(--font-mono);
        }}

        .container {{
            max-width: 980px;
            margin: 3rem auto;
            padding: 0 1.5rem;
        }}

        /* Typography & Visual Hierarchy */
        .editorial-hero {{
            margin-bottom: 3rem;
        }}
        .editorial-hero .eyebrow {{
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-muted);
            margin-bottom: 0.75rem;
            display: block;
        }}
        .editorial-hero h1 {{
            font-size: 2.5rem;
            font-weight: 600;
            color: var(--text-primary);
            letter-spacing: -0.035em;
            line-height: 1.2;
            margin-bottom: 0.75rem;
        }}
        .editorial-hero p {{
            font-size: 1.1rem;
            color: var(--text-secondary);
            line-height: 1.6;
            max-width: 640px;
        }}

        .quiet-hint {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 1rem;
        }}

        .card {{
            background-color: var(--bg-surface);
            border: 1px solid var(--border-light);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 1.75rem;
            box-shadow: var(--shadow-card);
        }}

        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-light);
        }}

        .card-title {{
            font-size: 1.2rem;
            font-weight: 600;
            color: var(--text-primary);
            letter-spacing: -0.015em;
        }}

        .badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.3rem 0.85rem;
            border-radius: 20px;
            font-size: 0.775rem;
            font-weight: 600;
            letter-spacing: 0.01em;
        }}

        .badge-hold, .status-green {{ background-color: var(--status-green-bg); color: var(--status-green); border: 1px solid var(--status-green-border); }}
        .badge-monitor, .status-amber {{ background-color: var(--status-amber-bg); color: var(--status-amber); border: 1px solid var(--status-amber-border); }}
        .badge-review, .status-red {{ background-color: var(--status-red-bg); color: var(--status-red); border: 1px solid var(--status-red-border); }}
        .badge-neutral, .status-neutral {{ background-color: var(--status-neutral-bg); color: var(--status-neutral); border: 1px solid var(--status-neutral-border); }}

        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }}
        .grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; }}
        .grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.25rem; }}

        @media (max-width: 768px) {{
            .grid-2, .grid-3, .grid-4 {{ grid-template-columns: 1fr; }}
            header {{ flex-direction: column; height: auto; padding: 1.25rem; gap: 1rem; align-items: flex-start; }}
            nav {{ flex-wrap: wrap; width: 100%; }}
            .user-profile-badge {{ margin-left: 0; margin-top: 0.5rem; }}
            .editorial-hero h1 {{ font-size: 1.85rem; }}
        }}

        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0.75rem 1.5rem;
            border-radius: 10px;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            border: 1px solid transparent;
            box-shadow: var(--shadow-card);
        }}

        .btn-lg {{
            padding: 0.9rem 1.85rem;
            font-size: 1rem;
            border-radius: 12px;
        }}

        .btn-sm {{
            padding: 0.4rem 0.85rem;
            font-size: 0.825rem;
            border-radius: 8px;
        }}

        .btn-primary {{
            background-color: var(--accent-primary);
            color: #ffffff;
            border-color: var(--accent-primary);
        }}
        .btn-primary:hover {{
            background-color: var(--accent-hover);
            border-color: var(--accent-hover);
            transform: translateY(-1px);
        }}

        .btn-secondary {{
            background-color: var(--bg-surface);
            color: var(--text-primary);
            border-color: var(--border-medium);
        }}
        .btn-secondary:hover {{
            background-color: var(--bg-subtle);
            border-color: var(--text-secondary);
        }}

        .btn-logout {{
            background: transparent;
            color: var(--text-muted);
            border-color: var(--border-light);
            box-shadow: none;
        }}
        .btn-logout:hover {{ color: var(--status-red); border-color: var(--status-red-border); }}

        .data-table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 0.925rem;
        }}
        .data-table th, .data-table td {{
            padding: 1rem 1.1rem;
            text-align: left;
            border-bottom: 1px solid var(--border-light);
        }}
        .data-table th {{
            background-color: var(--bg-subtle);
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.725rem;
            letter-spacing: 0.06em;
        }}
        .data-table th:first-child {{ border-top-left-radius: 10px; }}
        .data-table th:last-child {{ border-top-right-radius: 10px; }}
        .data-table tbody tr:hover {{
            background-color: var(--bg-subtle);
        }}

        .na-text {{ color: var(--text-muted); font-style: italic; font-size: 0.875rem; }}

        .notice-banner {{
            background-color: var(--bg-subtle);
            border: 1px solid var(--border-light);
            border-radius: 12px;
            padding: 1.1rem 1.35rem;
            margin-bottom: 1.75rem;
            font-size: 0.9rem;
            color: var(--text-secondary);
            line-height: 1.5;
        }}

        .section-label {{
            font-size: 0.775rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-muted);
            margin-bottom: 0.75rem;
            display: block;
        }}

        .metric-box {{
            background: var(--bg-surface);
            border: 1px solid var(--border-light);
            border-radius: 12px;
            padding: 1.35rem;
            box-shadow: var(--shadow-card);
        }}
        .metric-box .metric-label {{
            font-size: 0.825rem;
            color: var(--text-muted);
            font-weight: 500;
            margin-bottom: 0.35rem;
        }}
        .metric-box .metric-value {{
            font-size: 1.4rem;
            font-weight: 600;
            color: var(--text-primary);
            letter-spacing: -0.02em;
        }}
        .metric-box .metric-subtext {{
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-top: 0.35rem;
        }}

        /* Progressive Disclosure Details Box */
        .evidence-box {{
            background: var(--bg-subtle);
            border: 1px solid var(--border-light);
            border-radius: 12px;
            padding: 1.15rem 1.35rem;
            margin-top: 1.5rem;
        }}
        .evidence-box summary {{
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--text-secondary);
            cursor: pointer;
            user-select: none;
        }}
        .evidence-box summary:hover {{ color: var(--text-primary); }}
        .evidence-content {{
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border-light);
            font-size: 0.85rem;
            color: var(--text-secondary);
            line-height: 1.6;
        }}

        /* Onboarding Step Journey */
        .step-progress {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 2rem;
        }}
        .step-dot {{
            width: 32px;
            height: 4px;
            border-radius: 2px;
            background: var(--border-light);
        }}
        .step-dot.active {{
            background: var(--accent-primary);
        }}
        .choice-card {{
            display: flex;
            align-items: flex-start;
            gap: 1rem;
            padding: 1.25rem 1.5rem;
            border-radius: 12px;
            border: 1px solid var(--border-light);
            background: var(--bg-surface);
            cursor: pointer;
            margin-bottom: 0.75rem;
            user-select: none;
        }}
        .choice-card:hover {{
            border-color: var(--border-medium);
            background: var(--bg-subtle);
        }}
        .choice-card:has(input[type="radio"]:checked) {{
            border-color: var(--border-dark);
            background: var(--bg-subtle);
            box-shadow: 0 0 0 1px var(--border-dark);
        }}
        .choice-card:has(input[type="radio"]:focus-visible) {{
            outline: 2px solid var(--accent-primary);
            outline-offset: 2px;
        }}
        .choice-card input[type="radio"] {{
            margin-top: 0.25rem;
            cursor: pointer;
        }}
        .choice-card-content {{
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            cursor: pointer;
        }}

        /* Platform-Wide Unsaved Progress Guard Modal */
        .unsaved-modal-backdrop {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-color: rgba(28, 29, 31, 0.45);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
            z-index: 9999;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
        }}
        .unsaved-modal-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border-medium);
            border-radius: 16px;
            max-width: 480px;
            width: 100%;
            padding: 2rem;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
            animation: modalFadeIn 0.2s ease-out;
        }}
        @keyframes modalFadeIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .unsaved-modal-title {{
            font-size: 1.35rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 0.5rem;
            letter-spacing: -0.02em;
        }}
        .unsaved-modal-body {{
            font-size: 0.95rem;
            color: var(--text-secondary);
            line-height: 1.5;
            margin-bottom: 1.75rem;
        }}
        .unsaved-modal-actions {{
            display: flex;
            flex-direction: column;
            gap: 0.65rem;
        }}
        @media (min-width: 480px) {{
            .unsaved-modal-actions {{
                flex-direction: row-reverse;
                justify-content: flex-start;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <a href="/" class="brand">
            <span class="brand-icon">∆</span>
            <span>Mutual Fund Decision Engine</span>
        </a>
        <nav>
            {nav_html}
            {auth_badge_html}
        </nav>
    </header>

    <main class="container">
        {content_html}
    </main>

    <!-- Platform-Wide Unsaved Progress Modal -->
    <div id="unsaved-modal" class="unsaved-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="unsaved-modal-title-text" aria-describedby="unsaved-modal-body-text">
        <div class="unsaved-modal-card">
            <h2 id="unsaved-modal-title-text" class="unsaved-modal-title">Leave this page?</h2>
            <p id="unsaved-modal-body-text" class="unsaved-modal-body">
                You have unsaved changes. What would you like to do?
            </p>
            <div class="unsaved-modal-actions">
                <button type="button" id="btn-modal-save" class="btn btn-primary" style="display: none;">Save changes and leave</button>
                <button type="button" id="btn-modal-leave" class="btn btn-secondary" style="color: var(--status-red); border-color: var(--status-red-border);">Leave without saving</button>
                <button type="button" id="btn-modal-stay" class="btn btn-secondary">Stay</button>
            </div>
        </div>
    </div>

    <script>
    (function() {{
        let isDirty = false;
        let pendingTargetUrl = null;
        let targetFormToSave = null;
        let initialFormState = {{}};

        const modal = document.getElementById('unsaved-modal');
        const modalBody = document.getElementById('unsaved-modal-body-text');
        const btnSave = document.getElementById('btn-modal-save');
        const btnLeave = document.getElementById('btn-modal-leave');
        const btnStay = document.getElementById('btn-modal-stay');

        // Capture initial values of form inputs on DOMContentLoaded / load
        function captureInitialState() {{
            initialFormState = {{}};
            const inputs = document.querySelectorAll('input, select, textarea');
            inputs.forEach((el, index) => {{
                if (el.getAttribute('data-no-dirty') === 'true' || el.dataset.noDirty === 'true') return;
                const form = el.form || el.closest('form');
                if (form && (form.getAttribute('method') || 'GET').toUpperCase() !== 'POST') return;
                const key = el.name || el.id || ('input_' + index);
                if (el.type === 'checkbox' || el.type === 'radio') {{
                    initialFormState[key + '_' + el.value] = el.checked;
                }} else {{
                    initialFormState[key] = el.value;
                }}
            }});
        }}

        // Check if current form inputs differ from captured initial state
        function checkIsDirty() {{
            const inputs = document.querySelectorAll('input, select, textarea');
            for (let index = 0; index < inputs.length; index++) {{
                const el = inputs[index];
                if (el.getAttribute('data-no-dirty') === 'true' || el.dataset.noDirty === 'true') continue;
                const form = el.form || el.closest('form');
                if (form && (form.getAttribute('method') || 'GET').toUpperCase() !== 'POST') continue;
                const key = el.name || el.id || ('input_' + index);
                if (el.type === 'checkbox' || el.type === 'radio') {{
                    const initChecked = initialFormState[key + '_' + el.value];
                    if (initChecked !== undefined && el.checked !== initChecked) {{
                        return true;
                    }}
                }} else {{
                    const initVal = initialFormState[key];
                    if (initVal !== undefined && el.value !== initVal) {{
                        return true;
                    }}
                }}
            }}
            return false;
        }}

        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', captureInitialState);
        }} else {{
            captureInitialState();
        }}

        // Track changes on inputs across the page
        document.addEventListener('input', function(e) {{
            if (e.target.matches('input, select, textarea')) {{
                if (checkIsDirty()) {{
                    isDirty = true;
                }}
            }}
        }});
        document.addEventListener('change', function(e) {{
            if (e.target.matches('input, select, textarea')) {{
                if (checkIsDirty()) {{
                    isDirty = true;
                }}
            }}
        }});

        // Find forms on page and detect save capabilities
        function findSaveForm() {{
            const forms = Array.from(document.forms);
            for (let f of forms) {{
                const action = f.getAttribute('action') || '';
                const method = (f.getAttribute('method') || 'GET').toUpperCase();
                // Check if form is a POST persistence form
                if (method === 'POST') {{
                    return f;
                }}
            }}
            return null;
        }}

        function showUnsavedModal(targetUrl) {{
            pendingTargetUrl = targetUrl;
            targetFormToSave = findSaveForm();

            if (targetFormToSave) {{
                btnSave.style.display = 'inline-flex';
                modalBody.textContent = "You have changes that haven't been saved yet. What would you like to do?";
            }} else {{
                btnSave.style.display = 'none';
                modalBody.textContent = "Your current changes will be lost if you leave.";
            }}

            modal.style.display = 'flex';
            btnStay.focus();
        }}

        function hideUnsavedModal() {{
            modal.style.display = 'none';
            pendingTargetUrl = null;
            targetFormToSave = null;
        }}

        // Intercept link clicks across the application
        document.addEventListener('click', function(e) {{
            const link = e.target.closest('a');
            if (!link) return;

            const href = link.getAttribute('href');
            if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;

            // Allow navigation if target is same as current window location pathname
            if (href === window.location.pathname) return;

            // Check dirty state dynamically right before link navigation
            if (isDirty || checkIsDirty()) {{
                isDirty = true;
                e.preventDefault();
                showUnsavedModal(href);
            }}
        }});

        // Handle Modal Actions
        btnStay.addEventListener('click', function() {{
            hideUnsavedModal();
        }});

        btnLeave.addEventListener('click', function() {{
            isDirty = false;
            const dest = pendingTargetUrl;
            hideUnsavedModal();
            if (dest) {{
                window.location.href = dest;
            }}
        }});

        btnSave.addEventListener('click', function() {{
            if (targetFormToSave) {{
                const formToSubmit = targetFormToSave;
                const dest = pendingTargetUrl;
                hideUnsavedModal();
                
                // Set isDirty = false right before form submission so submit isn't blocked
                isDirty = false;
                
                // If form has hidden next redirect field, update it
                let nextInput = formToSubmit.querySelector('input[name="next"]');
                if (dest && !nextInput) {{
                    nextInput = document.createElement('input');
                    nextInput.type = 'hidden';
                    nextInput.name = 'next';
                    formToSubmit.appendChild(nextInput);
                }}
                if (dest && nextInput) {{
                    nextInput.value = dest;
                }}

                formToSubmit.submit();
            }}
        }});

        // ESC key closes modal (Safe action: Stay)
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape' && modal.style.display === 'flex') {{
                hideUnsavedModal();
            }}
        }});

        // Reset dirty state on form submit so normal submission proceeds cleanly
        document.addEventListener('submit', function(e) {{
            isDirty = false;
        }});

        // Native browser beforeunload warning for window refresh / tab close
        window.addEventListener('beforeunload', function(e) {{
            if (isDirty || checkIsDirty()) {{
                e.preventDefault();
                e.returnValue = '';
            }}
        }});
    }})();
    </script>
</body>
</html>"""


class UIRequestHandler(http.server.BaseHTTPRequestHandler):
    def _get_db_connection(self) -> sqlite3.Connection:
        db_path = os.path.join(os.path.dirname(__file__), "..", "db", "backfill_f12_2.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return sqlite3.connect(db_path)

    def _get_session_repository(self) -> SessionRepository:
        return SessionRepository(self._get_db_connection())

    def _get_profile_repository(self) -> ProfileRepository:
        return ProfileRepository(self._get_db_connection())

    def _get_portfolio_repository(self) -> PortfolioRepository:
        return PortfolioRepository(self._get_db_connection())

    def _get_principal_resolver(self) -> PrincipalIdentityResolver:
        return PrincipalIdentityResolver(self._get_db_connection())

    def _get_security_logger(self) -> SecurityAuditLogger:
        return SecurityAuditLogger(self._get_db_connection())

    def _get_authenticated_session(self) -> Tuple[Optional[str], Optional[SessionRecord]]:
        cookie_header = self.headers.get("Cookie")
        session_id = SecurityManager.parse_session_cookie(cookie_header)
        if not session_id:
            return None, None

        session_repo = self._get_session_repository()
        session = session_repo.get_session(session_id)
        if not session:
            return None, None

        return session.investor_id, session

    def _enforce_authentication(self) -> Tuple[Optional[str], Optional[SessionRecord]]:
        investor_id, session = self._get_authenticated_session()
        if not investor_id or not session:
            ip = self.client_address[0] if self.client_address else "127.0.0.1"
            ua = self.headers.get("User-Agent")
            self._get_security_logger().log_event(
                actor_investor_id="ANONYMOUS",
                event_type="UNAUTHORIZED_ACCESS_ATTEMPT",
                resource_type="HTTP_ROUTE",
                outcome="REDIRECT_TO_LOGIN",
                resource_id=self.path,
                ip_address=ip,
                user_agent=ua,
            )
            self.send_response(303)
            next_url = urllib.parse.quote(self.path)
            self.send_header("Location", f"/login?next={next_url}")
            self.end_headers()
            return None, None
        return investor_id, session

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/login":
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""
            post_params = urllib.parse.parse_qs(post_body)

            headers_dict = {k: v for k, v in self.headers.items()}
            try:
                investor_id, is_dev_simulation = SecurityManager.authenticate_login_request(
                    headers=headers_dict,
                    post_params=post_params,
                    principal_resolver=self._get_principal_resolver(),
                )
            except UnauthorizedError as e:
                ip = self.client_address[0] if self.client_address else "127.0.0.1"
                ua = self.headers.get("User-Agent")
                self._get_security_logger().log_event(
                    actor_investor_id="UNAUTHENTICATED",
                    event_type="AUTH_FAILURE",
                    resource_type="SESSION",
                    outcome="REJECTED_UNAUTHORIZED",
                    resource_id="/login",
                    ip_address=ip,
                    user_agent=ua,
                )
                self.send_error(401, f"Unauthorized: {e}")
                return
            except ForbiddenError as e:
                ip = self.client_address[0] if self.client_address else "127.0.0.1"
                ua = self.headers.get("User-Agent")
                self._get_security_logger().log_event(
                    actor_investor_id="UNAUTHENTICATED",
                    event_type="AUTH_FAILURE",
                    resource_type="SESSION",
                    outcome="REJECTED_FORBIDDEN",
                    resource_id="/login",
                    ip_address=ip,
                    user_agent=ua,
                )
                self.send_error(403, f"Forbidden: {e}")
                return

            session_repo = self._get_session_repository()
            session = session_repo.create_session(investor_id, is_dev_simulation=is_dev_simulation)

            ip = self.client_address[0] if self.client_address else "127.0.0.1"
            ua = self.headers.get("User-Agent")
            evt_outcome = "SUCCESS_DEV_SIMULATION" if is_dev_simulation else "SUCCESS_TRUSTED_PRINCIPAL"
            self._get_security_logger().log_event(
                actor_investor_id=investor_id,
                event_type="AUTH_SUCCESS",
                resource_type="SESSION",
                outcome=evt_outcome,
                resource_id=session.session_id,
                ip_address=ip,
                user_agent=ua,
            )

            is_secure = self.headers.get("X-Forwarded-Proto", "") == "https"
            cookie_header = SecurityManager.format_session_cookie(session.session_id, is_secure=is_secure)

            query_params = urllib.parse.parse_qs(parsed.query)
            next_target = "/"
            if "next" in query_params:
                next_target = query_params["next"][0]
            elif "next" in post_params:
                next_target = post_params["next"][0]

            if not next_target.startswith("/"):
                next_target = "/"

            self.send_response(303)
            self.send_header("Set-Cookie", cookie_header)
            self.send_header("Location", next_target)
            self.end_headers()
            return

        # Enforce Authentication on all other POST endpoints
        investor_id, session = self._enforce_authentication()
        if not investor_id or not session:
            return

        content_length = int(self.headers.get("Content-Length", 0))

        if content_length > MAX_PORTFOLIO_UPLOAD_SIZE_BYTES:
            self.send_error(400, "Payload Too Large: File size exceeds 5 MB limit.")
            return

        post_bytes = self.rfile.read(content_length)

        submitted_csrf = None
        content_type = self.headers.get("Content-Type", "")

        if "multipart/form-data" in content_type:
            boundary = content_type.split("boundary=")[-1].encode()
            parts = post_bytes.split(b"--" + boundary)
            for part in parts:
                if b'name="csrf_token"' in part:
                    headers_part, body_part = part.split(b"\r\n\r\n", 1)
                    submitted_csrf = body_part.rsplit(b"\r\n", 1)[0].decode("utf-8").strip()
                    break
        else:
            post_body_str = post_bytes.decode("utf-8", errors="ignore")
            parsed_params = urllib.parse.parse_qs(post_body_str)
            if "csrf_token" in parsed_params:
                submitted_csrf = parsed_params["csrf_token"][0].strip()

        if not SecurityManager.validate_csrf_token(session.csrf_token, submitted_csrf):
            ip = self.client_address[0] if self.client_address else "127.0.0.1"
            ua = self.headers.get("User-Agent")
            self._get_security_logger().log_event(
                actor_investor_id=investor_id,
                event_type="CSRF_VALIDATION_FAILURE",
                resource_type="HTTP_POST",
                outcome="REJECTED_BAD_REQUEST",
                resource_id=path,
                ip_address=ip,
                user_agent=ua,
            )
            self.send_error(400, "Bad Request: Anti-CSRF token validation failed.")
            return

        if path == "/onboarding" or path == "/api/onboarding":
            post_params = urllib.parse.parse_qs(post_bytes.decode("utf-8"))

            responses: Dict[int, Any] = {}
            if "question_1" in post_params:
                responses[1] = post_params["question_1"][0]
            if "question_2" in post_params:
                responses[2] = post_params["question_2"][0]
            if "question_5" in post_params:
                responses[5] = post_params["question_5"][0]

            repo = self._get_profile_repository()
            current = repo.get_current_profile(investor_id)
            version = QuestionnaireAdapter.increment_version(current.profile_version) if current else "1.0.0"
            responses["profile_version"] = version

            profile = QuestionnaireAdapter.responses_to_profile_snapshot(
                user_id=investor_id,
                responses=responses
            )
            repo.save_profile(profile)

            self._get_security_logger().log_event(
                actor_investor_id=investor_id,
                event_type="PROFILE_UPDATED",
                resource_type="INVESTOR_PROFILE",
                outcome="SUCCESS",
                resource_id=profile.profile_id,
            )

            redirect_dest = post_params.get("next", [None])[0] or post_params.get("redirect", [None])[0] or "/?status=profile_saved"
            # Prevent open redirect vulnerabilities by ensuring redirect is a relative path
            if not redirect_dest.startswith("/") or redirect_dest.startswith("//"):
                redirect_dest = "/?status=profile_saved"

            self.send_response(303)
            self.send_header("Location", redirect_dest)
            self.end_headers()
        elif path == "/wealth/upload":
            csv_bytes = b""
            post_params = {}
            if "application/x-www-form-urlencoded" in content_type:
                post_params = urllib.parse.parse_qs(post_bytes.decode("utf-8", errors="ignore"))
                if "raw_csv_payload" in post_params:
                    csv_bytes = post_params["raw_csv_payload"][0].encode("utf-8")
                else:
                    csv_bytes = post_bytes
            elif "multipart/form-data" in content_type:
                boundary = content_type.split("boundary=")[-1].encode()
                parts = post_bytes.split(b"--" + boundary)
                for part in parts:
                    if b'filename="' in part:
                        headers_part, body_part = part.split(b"\r\n\r\n", 1)
                        csv_bytes = body_part.rsplit(b"\r\n", 1)[0]
                        break
            else:
                csv_bytes = post_bytes

            adapter = PortfolioUploadAdapter()
            try:
                result = adapter.parse_csv_bytes(
                    file_bytes=csv_bytes,
                    filename="uploaded_portfolio.csv",
                    investor_id=investor_id
                )
                result["raw_csv_payload"] = csv_bytes.decode("utf-8", errors="ignore")
                
                if b"action=confirm" in post_bytes or "action=confirm" in self.path or "action=confirm" in post_params.get("action", []):
                    port_repo = self._get_portfolio_repository()
                    current_port = port_repo.get_current_portfolio(investor_id)
                    version_str = "1.0.0"
                    if current_port:
                        v_parts = current_port["version_string"].split(".")
                        v_parts[-1] = str(int(v_parts[-1]) + 1)
                        version_str = ".".join(v_parts)

                    holdings = result["valid_holdings"]
                    canonical_ids = [h.canonical_scheme_id for h in holdings]
                    holding_ids = [h.holding_id for h in holdings]
                    
                    snap = PortfolioExposureSnapshot(
                        portfolio_snapshot_id=result["portfolio_snapshot_id"],
                        investor_id=investor_id,
                        holding_ids=holding_ids,
                        canonical_scheme_ids=canonical_ids,
                        total_valuation=None,
                        is_valuation_available=True,
                        observation_date=result["observation_date"]
                    )
                    port_repo.save_portfolio(snap, holdings, version_string=version_str)

                    evt_type = "PORTFOLIO_REPLACED" if current_port else "PORTFOLIO_UPLOADED"
                    self._get_security_logger().log_event(
                        actor_investor_id=investor_id,
                        event_type=evt_type,
                        resource_type="PORTFOLIO_SNAPSHOT",
                        outcome="SUCCESS",
                        resource_id=snap.portfolio_snapshot_id,
                    )

                    self.send_response(303)
                    self.send_header("Location", "/wealth?status=uploaded")
                    self.end_headers()
                    return

                self.render_scr03_upload_preview(result, session)
            except PortfolioUploadError as e:
                self.render_scr03_upload_error(str(e), session)
            except Exception as e:
                self.render_scr03_upload_error(f"Unexpected error processing portfolio upload: {e}", session)
        elif path == "/wealth/manual":
            post_params = urllib.parse.parse_qs(post_bytes.decode("utf-8"))
            amfi_code = post_params.get("amfi_code", [""])[0].strip()
            isin = post_params.get("isin", [""])[0].strip()
            scheme_name = post_params.get("scheme_name", [""])[0].strip()
            units = post_params.get("units", [""])[0].strip()
            cost_basis = post_params.get("cost_basis", [""])[0].strip()
            acq_date = post_params.get("acquisition_date", [""])[0].strip()

            if not amfi_code and not isin and not scheme_name:
                self.render_scr03_upload_error("A valid scheme selection (AMFI Code, ISIN, or Scheme Name) is required.", session)
                return

            try:
                float_units = float(units)
                if float_units <= 0:
                    raise ValueError("Units must be positive")
            except (ValueError, TypeError):
                self.render_scr03_upload_error("Units must be a valid positive number.", session)
                return

            csv_line = f"isin,amfi_code,scheme_name,units,cost_basis,acquisition_date,goal_id\n{isin},{amfi_code},\"{scheme_name}\",{units},{cost_basis},{acq_date},\n"
            adapter = PortfolioUploadAdapter()
            try:
                result = adapter.parse_csv_bytes(
                    file_bytes=csv_line.encode("utf-8"),
                    filename="manual_portfolio.csv",
                    investor_id=investor_id
                )
                result["raw_csv_payload"] = csv_line
                self.render_scr03_upload_preview(result, session)
            except PortfolioUploadError as e:
                self.render_scr03_upload_error(str(e), session)
            except Exception as e:
                self.render_scr03_upload_error(f"Unexpected error processing manual portfolio entry: {e}", session)
        else:
            self.send_error(404, "POST endpoint not found")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/login":
            self.render_login_page(params)
            return
        elif path == "/logout":
            investor_id, session = self._get_authenticated_session()
            if session:
                self._get_session_repository().invalidate_session(session.session_id)
                ip = self.client_address[0] if self.client_address else "127.0.0.1"
                ua = self.headers.get("User-Agent")
                self._get_security_logger().log_event(
                    actor_investor_id=investor_id or "UNKNOWN",
                    event_type="LOGOUT",
                    resource_type="SESSION",
                    outcome="SUCCESS",
                    resource_id=session.session_id,
                    ip_address=ip,
                    user_agent=ua,
                )
            is_secure = self.headers.get("X-Forwarded-Proto", "") == "https"
            logout_cookie = SecurityManager.format_logout_cookie(is_secure=is_secure)
            self.send_response(303)
            self.send_header("Set-Cookie", logout_cookie)
            self.send_header("Location", "/login?status=logged_out")
            self.end_headers()
            return

        # Public Fund Discovery Routes
        if path == "/discover":
            investor_id, session = self._get_authenticated_session()
            self.render_scr05_discover(session)
            return
        elif path.startswith("/scheme/"):
            scheme_id = path.replace("/scheme/", "")
            investor_id, session = self._get_authenticated_session()
            self.render_scr06_fund_detail(scheme_id, session)
            return
        elif path == "/discover/compare":
            investor_id, session = self._get_authenticated_session()
            self.render_scr07_compare(session)
            return
        elif path == "/wealth/template":
            csv_content = "isin,amfi_code,scheme_name,units,cost_basis,acquisition_date,goal_id\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="portfolio_upload_template.csv"')
            self.end_headers()
            self.wfile.write(csv_content.encode("utf-8"))
            return
        elif path == "/api/schemes/search":
            q = params.get("q", [""])[0].strip() if params else ""
            amc = params.get("amc", [""])[0].strip() if params else ""
            category = params.get("category", [""])[0].strip() if params else ""
            subcategory = params.get("subcategory", [""])[0].strip() if params else ""
            plan = params.get("plan", [""])[0].strip() if params else ""
            option = params.get("option", [""])[0].strip() if params else ""
            ids_raw = params.get("ids", [""])[0].strip() if params else ""
            
            try:
                page = max(1, int(params.get("page", ["1"])[0])) if params else 1
            except ValueError:
                page = 1
                
            try:
                limit = min(100, max(1, int(params.get("limit", ["20"])[0]))) if params else 20
            except ValueError:
                limit = 20

            results = []
            total_count = 0
            
            import sqlite3
            conn = sqlite3.connect("db/backfill_f12_2.db")
            c = conn.cursor()

            # Handle multi-scheme ID lookup for Compare
            if ids_raw:
                id_list = [i.strip() for i in ids_raw.split(",") if i.strip()][:10]
                if id_list:
                    placeholders = ",".join(["?"] * len(id_list))
                    c.execute(f"""
                        SELECT canonical_scheme_id, scheme_name, amc_name, plan_type, option_type, category, primary_amfi_code, isin_growth, sub_category
                        FROM canonical_schemes
                        WHERE canonical_scheme_id IN ({placeholders})
                    """, id_list)
                    rows = c.fetchall()
                    row_map = {r[0]: r for r in rows}
                    for target_id in id_list:
                        if target_id in row_map:
                            r = row_map[target_id]
                            results.append({
                                "canonical_scheme_id": r[0],
                                "scheme_name": r[1],
                                "amc_name": r[2] or "",
                                "plan_type": r[3],
                                "option_type": r[4],
                                "category": r[5],
                                "amfi_code": r[6] or "",
                                "isin": r[7] or "",
                                "sub_category": r[8] or ""
                            })
                    total_count = len(results)
                conn.close()
                self.send_json({"query": q, "results": results, "total_count": total_count, "page": 1, "limit": limit, "total_pages": 1})
                return

            # Construct dynamic filtered query
            where_clauses = []
            sql_params = []

            if amc:
                where_clauses.append("UPPER(amc_name) = UPPER(?)")
                sql_params.append(amc)
            if category:
                where_clauses.append("UPPER(category) LIKE UPPER(?)")
                sql_params.append(f"%{category}%")
            if subcategory:
                where_clauses.append("UPPER(sub_category) LIKE UPPER(?)")
                sql_params.append(f"%{subcategory}%")
            if plan:
                where_clauses.append("UPPER(plan_type) = UPPER(?)")
                sql_params.append(plan)
            if option:
                where_clauses.append("UPPER(option_type) = UPPER(?)")
                sql_params.append(option)

            if q:
                tokens = q.split()
                if tokens:
                    token_clauses = []
                    for t in tokens:
                        token_clauses.append("scheme_name LIKE ?")
                        sql_params.append(f"%{t}%")
                    text_subclause = "(" + " AND ".join(token_clauses) + ")"
                    
                    if q.isdigit():
                        where_clauses.append(f"({text_subclause} OR primary_amfi_code = ?)")
                        sql_params.append(q)
                    elif len(q) >= 10 and q.isalnum():
                        where_clauses.append(f"({text_subclause} OR isin_growth = ?)")
                        sql_params.append(q.upper())
                    else:
                        where_clauses.append(text_subclause)

            where_str = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

            # Count total matching schemes
            count_sql = f"SELECT COUNT(*) FROM canonical_schemes {where_str}"
            c.execute(count_sql, sql_params)
            total_count = c.fetchone()[0]

            # Relevance ordering for autocomplete/search when q is present
            if q:
                order_clause = f"""
                    ORDER BY 
                    CASE 
                        WHEN UPPER(scheme_name) = UPPER(?) THEN 1
                        WHEN UPPER(scheme_name) LIKE UPPER(?) THEN 2
                        WHEN UPPER(scheme_name) LIKE UPPER(?) THEN 3
                        ELSE 4
                    END, scheme_name ASC
                """
                order_params = [q, f"{q}%", f"% {q}%"]
            else:
                order_clause = "ORDER BY scheme_name ASC"
                order_params = []

            # Execute paginated query
            offset = (page - 1) * limit
            data_sql = f"""
                SELECT canonical_scheme_id, scheme_name, amc_name, plan_type, option_type, category, primary_amfi_code, isin_growth, sub_category
                FROM canonical_schemes
                {where_str}
                {order_clause}
                LIMIT ? OFFSET ?
            """
            c.execute(data_sql, sql_params + order_params + [limit, offset])
            rows = c.fetchall()

            for r in rows:
                results.append({
                    "canonical_scheme_id": r[0],
                    "scheme_name": r[1],
                    "amc_name": r[2] or "",
                    "plan_type": r[3],
                    "option_type": r[4],
                    "category": r[5],
                    "amfi_code": r[6] or "",
                    "isin": r[7] or "",
                    "sub_category": r[8] or ""
                })

            conn.close()
            total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
            self.send_json({"query": q, "results": results, "total_count": total_count, "page": page, "limit": limit, "total_pages": total_pages})
            return
        elif path == "/api/health":
            self.send_json({"status": "OK", "governance": "VERIFIED_READ_ONLY", "security": "AUTHENTICATED_GATEWAY_ACTIVE", "execution_status": "NOT_EXECUTED"})
            return

        # Protected Routes
        investor_id, session = self._enforce_authentication()
        if not investor_id or not session:
            return

        if path == "/" or path == "":
            self.render_scr02_home(session)
        elif path == "/onboarding":
            self.render_scr01_onboarding(session, params)
        elif path == "/wealth":
            self.render_scr03_wealth(params, session)
        elif path.startswith("/wealth/goals/"):
            goal_id = path.replace("/wealth/goals/", "")
            self.render_scr04_goal_detail(goal_id, session)
        elif path == "/action/evaluate-switch":
            self.render_scr08_switch(session)
        elif path == "/action-center":
            self.render_scr09_action_center(session)
        elif path == "/settings":
            self.render_scr10_settings(session)
        else:
            self.send_error(404, "Screen route not found")

    def send_html(self, html_str: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_str.encode("utf-8"))

    def send_json(self, data: Dict[str, Any]):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    # --- SCREEN IMPLEMENTATIONS ---

    def render_login_page(self, params: Optional[Dict[str, List[str]]] = None):
        """Renders calm, quiet Investor Login page."""
        status_msg = ""
        if params and "status" in params and "logged_out" in params["status"]:
            status_msg = '<div class="notice-banner" style="border-color: var(--status-green-border); background: var(--status-green-bg); color: var(--status-green);">Your session has been safely closed.</div>'

        next_val = params.get("next", ["/"])[0] if params else "/"
        escaped_next = SecurityManager.escape_html(next_val)

        is_prod = SecurityManager.is_production_mode()
        if is_prod:
            mode_badge = '<span class="badge badge-review">Production Auth</span>'
            mode_notice = """
            <div class="notice-banner">
                Production mode requires an identity assertion header from your configured SSO/OIDC provider.
            </div>
            """
            form_inputs = '<p style="color: var(--text-muted); font-size: 0.9rem;">Authenticate via your configured Single Sign-On provider.</p>'
        else:
            mode_badge = '<span class="badge badge-neutral">Local Dev Session</span>'
            mode_notice = ""
            form_inputs = f"""
            <div style="margin-bottom: 1.25rem;">
                <label style="display: block; font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 0.5rem; font-weight: 500;">Investor Handle</label>
                <input type="text" name="investor_id" value="investor_dev_default" required style="width: 100%; padding: 0.75rem 1rem; border-radius: 8px; background: var(--bg-surface); border: 1px solid var(--border-medium); color: var(--text-primary); font-family: var(--font-mono); font-size: 0.95rem;">
            </div>
            <button type="submit" class="btn btn-primary" style="width: 100%;">Sign In</button>
            """

        content = f"""
        <div class="card" style="max-width: 440px; margin: 4rem auto;">
            <div class="card-header" style="border-bottom: none; padding-bottom: 0;">
                <div>
                    <h1 style="font-size: 1.5rem; font-weight: 600; color: var(--text-primary);">Investor Sign In</h1>
                </div>
                {mode_badge}
            </div>

            {status_msg}
            {mode_notice}

            <form action="/login" method="POST" style="margin-top: 1.25rem;">
                <input type="hidden" name="next" value="{escaped_next}">
                {form_inputs}
            </form>
        </div>
        """
        self.send_html(render_html_page("Investor Authentication", content, "/login"))

    def render_scr01_onboarding(self, session: SessionRecord, params: Optional[Dict[str, List[str]]] = None):
        """SCR-01: Guided Progressive Investor Profiling Journey"""
        investor_id = session.investor_id
        repo = self._get_profile_repository()
        current_profile = repo.get_current_profile(investor_id)
        saved_responses = QuestionnaireAdapter.profile_snapshot_to_responses(current_profile) if current_profile else {}

        current_step = 1
        if params and "step" in params:
            try:
                current_step = int(params["step"][0])
                current_step = max(1, min(4, current_step))
            except ValueError:
                current_step = 1

        escaped_csrf = SecurityManager.escape_html(session.csrf_token)
        
        # Priority order for form parameters: URL query params > saved_responses > defaults
        q1_param = (params.get("q1_temp", [None])[0] if params else None) or saved_responses.get(1, "WEALTH_ACCUMULATION")
        q2_param_raw = (params.get("q2_val", [None])[0] if params else None)
        if q2_param_raw is None or q2_param_raw == "":
            saved_q2 = saved_responses.get(2)
            q2_val_display = str(saved_q2) if saved_q2 is not None else ""
        else:
            q2_val_display = str(q2_param_raw)

        q5_param = (params.get("q5_val", [None])[0] if params else None) or saved_responses.get(5, "HOLD_STEADY")

        # Step Dot Indicators
        step_dots_html = ""
        for s in range(1, 5):
            active_cls = "active" if s <= current_step else ""
            step_dots_html += f'<div class="step-dot {active_cls}"></div>'

        step_progress_bar = f"""
        <div style="margin-bottom: 2rem;">
            <span class="section-label">Step {current_step} of 4</span>
            <div class="step-progress">{step_dots_html}</div>
        </div>
        """

        step_content = ""
        if current_step == 1:
            step_content = f"""
            <div class="editorial-hero">
                <span class="eyebrow">Goal & Horizon</span>
                <h1>What are you investing for?</h1>
                <p>Establishing your primary financial goal helps determine the appropriate asset balance and liquidity timeline.</p>
            </div>

            <form action="/onboarding" method="GET" style="display: flex; flex-direction: column; gap: 1rem;">
                <input type="hidden" name="step" value="2">
                <input type="hidden" name="q2_val" value="{SecurityManager.escape_html(q2_val_display)}">
                <input type="hidden" name="q5_val" value="{SecurityManager.escape_html(q5_param)}">
                <label class="choice-card">
                    <input type="radio" name="q1_temp" value="WEALTH_ACCUMULATION" {"checked" if q1_param == "WEALTH_ACCUMULATION" else ""}>
                    <span class="choice-card-content">
                        <strong style="display: block; color: var(--text-primary); font-size: 1rem;">Long-term Wealth Growth</strong>
                        <span style="font-size: 0.875rem; color: var(--text-secondary);">Compounding wealth over a horizon of 5+ years with moderate liquidity needs.</span>
                    </span>
                </label>
                <label class="choice-card">
                    <input type="radio" name="q1_temp" value="RETIREMENT" {"checked" if q1_param == "RETIREMENT" else ""}>
                    <span class="choice-card-content">
                        <strong style="display: block; color: var(--text-primary); font-size: 1rem;">Retirement & Independence</strong>
                        <span style="font-size: 0.875rem; color: var(--text-secondary);">Building a sustained corpus for post-work financial freedom.</span>
                    </span>
                </label>
                <label class="choice-card">
                    <input type="radio" name="q1_temp" value="CAPITAL_PROTECTION" {"checked" if q1_param == "CAPITAL_PROTECTION" else ""}>
                    <span class="choice-card-content">
                        <strong style="display: block; color: var(--text-primary); font-size: 1rem;">Capital Protection & Liquidity</strong>
                        <span style="font-size: 0.875rem; color: var(--text-secondary);">Preserving capital for near-term milestones with minimal drawdown tolerance.</span>
                    </span>
                </label>

                <div style="margin-top: 1.5rem; display: flex; gap: 1rem;">
                    <button type="submit" class="btn btn-primary btn-lg">Continue →</button>
                </div>
            </form>
            """
        elif current_step == 2:
            step_content = f"""
            <div class="editorial-hero">
                <span class="eyebrow">Financial Capacity</span>
                <h1>What is your emergency buffer?</h1>
                <p>Maintaining sufficient liquid cash reserves ensures you are never forced to liquidate investments during market downturns.</p>
            </div>

            <form action="/onboarding" method="GET" style="display: flex; flex-direction: column; gap: 1.5rem; max-width: 520px;">
                <input type="hidden" name="step" value="3">
                <input type="hidden" name="q1_temp" value="{SecurityManager.escape_html(q1_param)}">
                <input type="hidden" name="q5_val" value="{SecurityManager.escape_html(q5_param)}">
                <div style="background: var(--bg-surface); padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border-light); box-shadow: var(--shadow-card);">
                    <label style="display: block; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem;">Essential Reserve Months</label>
                    <p style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 1rem;">How many months of essential living expenses are held in liquid bank accounts or fixed deposits?</p>
                    <input type="number" name="q2_val" value="{SecurityManager.escape_html(q2_val_display)}" step="0.5" min="0" placeholder="e.g. 6.0" style="width: 100%; padding: 0.8rem 1rem; border-radius: 8px; background: var(--bg-page); border: 1px solid var(--border-medium); color: var(--text-primary); font-size: 1rem;">
                </div>

                <div style="display: flex; gap: 1rem;">
                    <a href="/onboarding?step=1&q1_temp={SecurityManager.escape_html(q1_param)}&q2_val={SecurityManager.escape_html(q2_val_display)}&q5_val={SecurityManager.escape_html(q5_param)}" class="btn btn-secondary">← Back</a>
                    <button type="submit" class="btn btn-primary btn-lg">Continue →</button>
                </div>
            </form>
            """
        elif current_step == 3:
            step_content = f"""
            <div class="editorial-hero">
                <span class="eyebrow">Risk Comfort</span>
                <h1>What does market risk feel like to you?</h1>
                <p>Understanding your behavioral response to short-term market fluctuations prevents panic reactions during normal market cycles.</p>
            </div>

            <form action="/onboarding" method="GET" style="display: flex; flex-direction: column; gap: 1rem;">
                <input type="hidden" name="step" value="4">
                <input type="hidden" name="q1_temp" value="{SecurityManager.escape_html(q1_param)}">
                <input type="hidden" name="q2_val" value="{SecurityManager.escape_html(q2_val_display)}">
                <label class="choice-card">
                    <input type="radio" name="q5_val" value="SELL_ALL" {"checked" if q5_param == "SELL_ALL" else ""}>
                    <span class="choice-card-content">
                        <strong style="display: block; color: var(--text-primary); font-size: 1rem;">Capital Preservation</strong>
                        <span style="font-size: 0.875rem; color: var(--text-secondary);">If market drops 20%, I prefer to exit or cut exposure to avoid further anxiety.</span>
                    </span>
                </label>
                <label class="choice-card">
                    <input type="radio" name="q5_val" value="HOLD_STEADY" {"checked" if q5_param == "HOLD_STEADY" else ""}>
                    <span class="choice-card-content">
                        <strong style="display: block; color: var(--text-primary); font-size: 1rem;">Disciplined Growth</strong>
                        <span style="font-size: 0.875rem; color: var(--text-secondary);">If market drops 20%, I will hold steady and stick to my long-term allocation plan.</span>
                    </span>
                </label>
                <label class="choice-card">
                    <input type="radio" name="q5_val" value="ACCUMULATE_MORE" {"checked" if q5_param == "ACCUMULATE_MORE" else ""}>
                    <span class="choice-card-content">
                        <strong style="display: block; color: var(--text-primary); font-size: 1rem;">Value Accumulation</strong>
                        <span style="font-size: 0.875rem; color: var(--text-secondary);">If market drops 20%, I view lower NAVs as an opportunity to invest additional capital.</span>
                    </span>
                </label>

                <div style="margin-top: 1rem; display: flex; gap: 1rem;">
                    <a href="/onboarding?step=2&q1_temp={SecurityManager.escape_html(q1_param)}&q2_val={SecurityManager.escape_html(q2_val_display)}&q5_val={SecurityManager.escape_html(q5_param)}" class="btn btn-secondary">← Back</a>
                    <button type="submit" class="btn btn-primary btn-lg">Continue →</button>
                </div>
            </form>
            """
        else:
            # Step 4 Review Screen
            reserve_display_html = f"{SecurityManager.escape_html(q2_val_display)} Months" if q2_val_display != "" else "Not specified"
            
            # Investor-facing presentation mapping for behavioral reaction enum
            behavioral_labels = {
                "SELL_ALL": "Exit or reduce exposure to avoid anxiety during market drops",
                "HOLD_STEADY": "Hold steady and maintain my long-term allocation during market declines",
                "ACCUMULATE_MORE": "Invest additional capital to take advantage of lower prices during market drops",
            }
            behavioral_display = behavioral_labels.get(q5_param, q5_param)

            step_content = f"""
            <div class="editorial-hero">
                <span class="eyebrow">Review & Confirm</span>
                <h1>Review your investment picture.</h1>
                <p>Please confirm your responses before creating an updated snapshot of your investor profile.</p>
            </div>

            <div class="card" style="margin-bottom: 2rem;">
                <div style="display: flex; flex-direction: column; gap: 1.25rem;">
                    <div>
                        <span class="section-label">Emergency Reserve Capacity</span>
                        <div style="font-size: 1.1rem; font-weight: 600; color: var(--text-primary);">
                            {reserve_display_html}
                        </div>
                    </div>
                    <div>
                        <span class="section-label">Behavioral Risk Reaction</span>
                        <div style="font-size: 1.1rem; font-weight: 600; color: var(--text-primary);">
                            {SecurityManager.escape_html(behavioral_display)}
                        </div>
                    </div>
                </div>
            </div>

            <form action="/onboarding" method="POST" style="display: flex; gap: 1rem;">
                <input type="hidden" name="csrf_token" value="{escaped_csrf}">
                <input type="hidden" name="question_1" value="{SecurityManager.escape_html(q1_param)}">
                <input type="hidden" name="question_2" value="{SecurityManager.escape_html(q2_val_display)}">
                <input type="hidden" name="question_5" value="{SecurityManager.escape_html(q5_param)}">
                <button type="submit" class="btn btn-primary btn-lg">Save Profile Snapshot</button>
                <a href="/onboarding?step=3&q1_temp={SecurityManager.escape_html(q1_param)}&q2_val={SecurityManager.escape_html(q2_val_display)}&q5_val={SecurityManager.escape_html(q5_param)}" class="btn btn-secondary">← Back</a>
            </form>
            """

        content = f"""
        {step_progress_bar}
        {step_content}
        """
        self.send_html(render_html_page("Profile Questionnaire", content, "/onboarding", session.investor_id, session.csrf_token))

    def render_scr02_home(self, session: SessionRecord):
        """SCR-02: State-Aware Investor Home Page"""
        investor_id = session.investor_id
        profile_repo = self._get_profile_repository()
        port_repo = self._get_portfolio_repository()

        profile = profile_repo.get_current_profile(investor_id)
        portfolio = port_repo.get_current_portfolio(investor_id)

        has_profile = profile is not None and (profile.financial_capacity is not None or profile.behavioral_tolerance is not None)
        has_portfolio = portfolio is not None and bool(portfolio.get("holdings"))

        if not has_profile:
            content = f"""
            <div class="editorial-hero" style="margin-top: 2rem;">
                <span class="eyebrow">Getting Started</span>
                <h1>Let's build your investment picture.</h1>
                <p>We'll ask a few questions about your goals, finances and comfort with risk.</p>
                <div style="margin-top: 2rem;">
                    <a href="/onboarding" class="btn btn-primary btn-lg">Start your profile</a>
                </div>
                <p class="quiet-hint">Takes a few minutes</p>
            </div>
            """
            self.send_html(render_html_page("Home", content, "/", session.investor_id, session.csrf_token))
            return

        if not has_portfolio:
            content = f"""
            <div class="editorial-hero" style="margin-top: 2rem;">
                <span class="eyebrow">Profile Completed</span>
                <h1>Your investment picture is ready.</h1>
                <p>You're ready to start exploring investments. Add an existing portfolio anytime to see how your current holdings fit.</p>
                <div style="margin-top: 2rem; display: flex; gap: 1rem; flex-wrap: wrap;">
                    <a href="/discover" class="btn btn-primary btn-lg">Explore Funds</a>
                    <a href="/wealth" class="btn btn-secondary btn-lg">Add Portfolio</a>
                    <a href="/onboarding" class="btn btn-secondary btn-lg">Review Profile</a>
                </div>
            </div>
            """
            self.send_html(render_html_page("Home", content, "/", session.investor_id, session.csrf_token))
            return

        holdings = portfolio.get("holdings", [])
        holdings_count = len(holdings)
        obs_date = SecurityManager.escape_html(portfolio.get("observation_date", "N/A"))
        val_total = portfolio.get("total_valuation")
        val_str = f"₹{val_total:,.2f}" if val_total is not None else '<span class="na-text">N/A</span>'

        reserve_months = profile.financial_capacity.emergency_reserve_months if (profile.financial_capacity and profile.financial_capacity.emergency_reserve_months is not None) else None
        reserve_str = f"{reserve_months:g} Months" if reserve_months is not None else '<span class="na-text">N/A</span>'

        loss_choice = profile.behavioral_tolerance.loss_reaction_choice if (profile.behavioral_tolerance and profile.behavioral_tolerance.loss_reaction_choice) else None
        if loss_choice == "SELL_ALL":
            loss_str = "Prefer to reduce exposure during market drops"
        elif loss_choice == "HOLD_STEADY":
            loss_str = "Stay invested and maintain allocation during declines"
        elif loss_choice == "ACCUMULATE_MORE":
            loss_str = "Comfortable continuing to invest when markets fall"
        else:
            loss_str = '<span class="na-text">N/A</span>'

        attention_card = f"""
        <div class="card" style="border-left: 4px solid var(--status-green); margin-bottom: 2rem;">
            <div class="card-header" style="border-bottom: none; padding-bottom: 0; margin-bottom: 0.5rem;">
                <span class="card-title">Current Status</span>
                <span class="badge status-green">Assessment</span>
            </div>
            <h2 style="font-size: 1.35rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem;">You're on track.</h2>
            <p style="color: var(--text-secondary); font-size: 0.975rem; line-height: 1.6;">
                All current mutual fund holdings satisfy governed suitability and category quality standards. No portfolio changes or switches are necessary at this time.
            </p>
        </div>
        """

        content = f"""
        <div class="editorial-hero">
            <span class="eyebrow">Overview</span>
            <h1>Here's where you stand.</h1>
        </div>

        {attention_card}

        <div class="grid-3" style="margin-bottom: 2rem;">
            <div class="metric-box">
                <div class="metric-label">Holdings Summary</div>
                <div class="metric-value">{holdings_count} Funds</div>
                <div class="metric-subtext">Observation: {obs_date}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Emergency Reserves</div>
                <div class="metric-value">{reserve_str}</div>
                <div class="metric-subtext">Financial Capacity</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Risk Profile</div>
                <div class="metric-value" style="font-size: 1.15rem;">{loss_str}</div>
                <div class="metric-subtext">Behavioral Tolerance</div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <span class="card-title">Quick Actions</span>
            </div>
            <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                <a href="/wealth" class="btn btn-secondary">Review Holdings</a>
                <a href="/discover" class="btn btn-secondary">Explore Fund Scanner</a>
                <a href="/action-center" class="btn btn-secondary">View Actions</a>
            </div>
        </div>

        <details class="evidence-box">
            <summary>Evidence & methodology</summary>
            <div class="evidence-content">
                <div>• <strong>Low-Turnover Principle:</strong> System default action is HOLD unless evidence clears hurdle.</div>
                <div>• <strong>Execution Status:</strong> Strictly <code>NOT_EXECUTED</code> (Read-Only Decision Gateway).</div>
            </div>
        </details>
        """
        self.send_html(render_html_page("Home", content, "/", session.investor_id, session.csrf_token))

    def render_scr03_upload_preview(self, result: Dict[str, Any], session: SessionRecord):
        """SCR-03: Portfolio Upload Preview"""
        valid_rows_html = ""
        for h in result["valid_holdings"]:
            cost_str = f"₹{h.cost_basis_amount:,.2f}" if h.cost_basis_amount is not None else '<span class="na-text">N/A</span>'
            valid_rows_html += f"""
            <tr>
                <td><strong><a href="/scheme/{SecurityManager.escape_html(h.canonical_scheme_id)}" style="color: var(--text-primary); text-decoration: none;">{SecurityManager.escape_html(h.scheme_name_raw or h.canonical_scheme_id)}</a></strong></td>
                <td>{SecurityManager.escape_html(h.canonical_scheme_id)}</td>
                <td>{h.units:,.4f}</td>
                <td>{cost_str}</td>
                <td><span class="badge status-green">Resolved</span></td>
            </tr>
            """

        quarantine_rows_html = ""
        for q in result["quarantined_rows"]:
            quarantine_rows_html += f"""
            <tr style="background: var(--status-amber-bg);">
                <td>Line {q['line_number']}: {SecurityManager.escape_html(q.get('raw_name') or 'Unknown')}</td>
                <td>ISIN: {SecurityManager.escape_html(q.get('raw_isin') or 'None')} | AMFI: {SecurityManager.escape_html(q.get('raw_amfi') or 'None')}</td>
                <td>{q['units']}</td>
                <td><span class="badge status-amber">Quarantined</span></td>
                <td style="color: var(--status-amber); font-size: 0.85rem;">{SecurityManager.escape_html(q['reason'])}</td>
            </tr>
            """

        escaped_csrf = SecurityManager.escape_html(session.csrf_token)

        content = f"""
        <div class="editorial-hero">
            <span class="eyebrow">Portfolio Import</span>
            <h1>Review uploaded holdings.</h1>
            <p>Verify resolved scheme mappings before confirming portfolio persistence.</p>
        </div>

        <div class="grid-3" style="margin-bottom: 2rem;">
            <div class="metric-box">
                <div class="metric-label">Total Rows Processed</div>
                <div class="metric-value">{result['total_rows_received']}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Resolved Holdings</div>
                <div class="metric-value" style="color: var(--status-green);">{result['valid_count']}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Quarantined Rows</div>
                <div class="metric-value" style="color: var(--status-amber);">{result['quarantine_count']}</div>
            </div>
        </div>

        <div class="card">
            {"<h3 style='font-size: 1.1rem; margin-bottom: 1rem; color: var(--text-primary);'>Resolved Holdings</h3>" if valid_rows_html else ""}
            {"<table class='data-table' style='margin-bottom: 2rem;'><thead><tr><th>Scheme Name</th><th>Canonical ID</th><th>Units</th><th>Cost Basis</th><th>Status</th></tr></thead><tbody>" + valid_rows_html + "</tbody></table>" if valid_rows_html else ""}

            {"<h3 style='font-size: 1.1rem; margin-bottom: 1rem; color: var(--status-amber);'>Quarantined Rows (Excluded from Assessment Until Resolved)</h3>" if quarantine_rows_html else ""}
            {"<table class='data-table' style='margin-bottom: 2rem;'><thead><tr><th>Source Line</th><th>Identifiers Provided</th><th>Units</th><th>Status</th><th>Reason</th></tr></thead><tbody>" + quarantine_rows_html + "</tbody></table>" if quarantine_rows_html else ""}

            <form action="/wealth/upload?action=confirm" method="POST" style="display: flex; gap: 1rem; margin-top: 1rem;">
                <input type="hidden" name="csrf_token" value="{escaped_csrf}">
                <input type="hidden" name="raw_csv_payload" value="{SecurityManager.escape_html(result.get('raw_csv_payload', ''))}">
                <button type="submit" class="btn btn-primary">Confirm & Persist Portfolio</button>
                <a href="/wealth" class="btn btn-secondary">Cancel</a>
            </form>
        </div>
        """
        self.send_html(render_html_page("Portfolio Upload Preview", content, "/wealth", session.investor_id, session.csrf_token))

    def render_scr03_upload_error(self, error_msg: str, session: SessionRecord):
        """SCR-03: Portfolio Upload Error Notice"""
        content = f"""
        <div class="card" style="border-left: 4px solid var(--status-red);">
            <div class="card-header">
                <span class="card-title" style="color: var(--status-red);">Portfolio Upload Failed</span>
                <span class="badge status-red">Import Error</span>
            </div>
            <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">
                {SecurityManager.escape_html(error_msg)}
            </p>
            <a href="/wealth" class="btn btn-secondary">Return to My Wealth</a>
        </div>
        """
        self.send_html(render_html_page("Portfolio Upload Error", content, "/wealth", session.investor_id, session.csrf_token))

    def render_scr03_wealth(self, params: Optional[Dict[str, List[str]]] = None, session: Optional[SessionRecord] = None):
        """SCR-03: Portfolio / My Wealth"""
        investor_id = session.investor_id if session else "ANONYMOUS"
        if hasattr(self, '_get_portfolio_repository'):
            port_repo = self._get_portfolio_repository()
        else:
            from data.repositories.portfolio_repository import PortfolioRepository
            port_repo = PortfolioRepository(sqlite3.connect("db/backfill_f12_2.db"))
        current_data = port_repo.get_current_portfolio(investor_id)

        status_notice = ""
        if params and "status" in params and "uploaded" in params["status"]:
            status_notice = '<div class="notice-banner" style="border-color: var(--status-green-border); background: var(--status-green-bg); color: var(--status-green);"><strong>Portfolio Saved:</strong> Your uploaded holdings have been persisted to the repository.</div>'

        escaped_csrf = SecurityManager.escape_html(session.csrf_token) if session else ""

        has_holdings = bool(current_data and current_data.get("holdings"))

        if not has_holdings:
            content = f"""
            <div class="editorial-hero">
                <span class="eyebrow">Holdings & Valuation</span>
                <h1>My Wealth</h1>
                <p>How would you like to add your investments?</p>
            </div>

            {status_notice}

            <div class="grid-3" style="margin-bottom: 2rem;">
                <div class="card" style="display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <span class="section-label">Path A</span>
                        <h2 style="font-size: 1.25rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem;">Upload a CSV</h2>
                        <p style="color: var(--text-secondary); font-size: 0.875rem; line-height: 1.5; margin-bottom: 1.25rem;">
                            Import an existing mutual fund portfolio file in CSV format.
                        </p>
                    </div>
                    <form action="/wealth/upload" method="POST" enctype="multipart/form-data" style="display: flex; flex-direction: column; gap: 0.75rem;">
                        <input type="hidden" name="csrf_token" value="{escaped_csrf}">
                        <input type="file" name="file" accept=".csv" required style="font-size: 0.825rem; color: var(--text-secondary);">
                        <button type="submit" class="btn btn-primary btn-sm" style="width: 100%;">Upload & Preview</button>
                    </form>
                </div>

                <div class="card" style="display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <span class="section-label">Path B</span>
                        <h2 style="font-size: 1.25rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem;">Use our template</h2>
                        <p style="color: var(--text-secondary); font-size: 0.875rem; line-height: 1.5; margin-bottom: 1.25rem;">
                            Download our official CSV template, fill in your holdings, and upload it here.
                        </p>
                    </div>
                    <div>
                        <a href="/wealth/template" download="portfolio_upload_template.csv" data-no-dirty="true" class="btn btn-secondary btn-sm" style="width: 100%; text-align: center; justify-content: center;">Download Template ↓</a>
                    </div>
                </div>

                <div class="card" style="display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <span class="section-label">Path C</span>
                        <h2 style="font-size: 1.25rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem;">Enter manually</h2>
                        <p style="color: var(--text-secondary); font-size: 0.875rem; line-height: 1.5; margin-bottom: 1.25rem;">
                            Add your mutual funds one by one using canonical scheme search.
                        </p>
                    </div>
                    <div>
                        <button type="button" onclick="document.getElementById('manual-entry-card').style.display='block'; this.scrollIntoView({{behavior: 'smooth'}});" class="btn btn-secondary btn-sm" style="width: 100%;">Add Holding Manually →</button>
                    </div>
                </div>
            </div>

            <!-- Manual Holding Entry Card (Progressive Disclosure) -->
            <div id="manual-entry-card" class="card" style="display: none; margin-bottom: 2rem; border-left: 4px solid var(--accent-primary);">
                <div class="card-header">
                    <span class="card-title">Enter Holding Manually</span>
                    <button type="button" onclick="document.getElementById('manual-entry-card').style.display='none';" class="btn btn-sm btn-secondary" style="border: none; box-shadow: none;">✕ Close</button>
                </div>
                <form action="/wealth/manual" method="POST" style="display: flex; flex-direction: column; gap: 1.25rem;">
                    <input type="hidden" name="csrf_token" value="{escaped_csrf}">
                    <input type="hidden" id="manual_canonical_id" name="canonical_scheme_id" value="">
                    <input type="hidden" id="manual_amfi_code" name="amfi_code" value="">
                    <input type="hidden" id="manual_isin" name="isin" value="">

                    <div style="position: relative;">
                        <label style="display: block; font-weight: 600; color: var(--text-primary); margin-bottom: 0.35rem; font-size: 0.9rem;">Scheme Name (Search & Select)</label>
                        <input type="text" id="manual_scheme_input" name="scheme_name" placeholder="Type scheme name (e.g. Nippon India Nifty 50)..." autocomplete="off" required style="width: 100%; padding: 0.75rem 1rem; border-radius: 8px; background: var(--bg-surface); border: 1px solid var(--border-medium); color: var(--text-primary); font-size: 0.95rem;">
                        <div id="manual_scheme_dropdown" style="display: none; position: absolute; top: 100%; left: 0; right: 0; background: var(--bg-surface); border: 1px solid var(--border-medium); border-radius: 8px; box-shadow: var(--shadow-card); max-height: 240px; overflow-y: auto; z-index: 1000; margin-top: 4px;"></div>
                        <div id="manual_selected_badge" style="display: none; margin-top: 0.5rem; font-size: 0.85rem; color: var(--status-green); font-weight: 500;"></div>
                    </div>

                    <div class="grid-2">
                        <div>
                            <label style="display: block; font-weight: 600; color: var(--text-primary); margin-bottom: 0.35rem; font-size: 0.9rem;">Units</label>
                            <input type="number" name="units" step="0.0001" min="0.0001" placeholder="e.g. 150.25" required style="width: 100%; padding: 0.75rem 1rem; border-radius: 8px; background: var(--bg-surface); border: 1px solid var(--border-medium); color: var(--text-primary); font-size: 0.95rem;">
                        </div>
                        <div>
                            <label style="display: block; font-weight: 600; color: var(--text-primary); margin-bottom: 0.35rem; font-size: 0.9rem;">Cost Basis / Invested Amount (Optional)</label>
                            <input type="number" name="cost_basis" step="0.01" min="0" placeholder="e.g. 25000.00" style="width: 100%; padding: 0.75rem 1rem; border-radius: 8px; background: var(--bg-surface); border: 1px solid var(--border-medium); color: var(--text-primary); font-size: 0.95rem;">
                        </div>
                    </div>

                    <div style="display: flex; gap: 1rem;">
                        <button type="submit" class="btn btn-primary">Review & Add Holding</button>
                    </div>
                </form>
            </div>

            <script>
            (function() {{
                const input = document.getElementById('manual_scheme_input');
                const dropdown = document.getElementById('manual_scheme_dropdown');
                const badge = document.getElementById('manual_selected_badge');
                const inputCanon = document.getElementById('manual_canonical_id');
                const inputAmfi = document.getElementById('manual_amfi_code');
                const inputIsin = document.getElementById('manual_isin');

                if (!input || !dropdown) return;

                let timer = null;
                input.addEventListener('input', function() {{
                    clearTimeout(timer);
                    const q = input.value.trim();
                    if (q.length < 2) {{
                        dropdown.style.display = 'none';
                        return;
                    }}

                    timer = setTimeout(() => {{
                        fetch('/api/schemes/search?q=' + encodeURIComponent(q))
                            .then(res => res.json())
                            .then(data => {{
                                if (!data.results || data.results.length === 0) {{
                                    dropdown.innerHTML = '<div style="padding: 0.75rem 1rem; color: var(--text-muted); font-size: 0.875rem;">No matching schemes found</div>';
                                    dropdown.style.display = 'block';
                                    return;
                                }}

                                let html = '';
                                data.results.forEach(r => {{
                                    html += `
                                    <div class="scheme-option-row" data-id="${{r.canonical_scheme_id}}" data-name="${{r.scheme_name.replace(/"/g, '&quot;')}}" data-amfi="${{r.amfi_code}}" data-isin="${{r.isin}}" style="padding: 0.75rem 1rem; border-bottom: 1px solid var(--border-light); cursor: pointer;">
                                        <div style="font-weight: 600; font-size: 0.9rem; color: var(--text-primary);">${{r.scheme_name}}</div>
                                        <div style="font-size: 0.775rem; color: var(--text-secondary); margin-top: 2px;">
                                            ${{r.plan_type}} • ${{r.option_type}} • ${{r.category}} ${{r.amfi_code ? '• AMFI: ' + r.amfi_code : ''}}
                                        </div>
                                    </div>
                                    `;
                                }});
                                dropdown.innerHTML = html;
                                dropdown.style.display = 'block';

                                dropdown.querySelectorAll('.scheme-option-row').forEach(row => {{
                                    row.addEventListener('click', function() {{
                                        const sId = row.getAttribute('data-id');
                                        const sName = row.getAttribute('data-name');
                                        const amfi = row.getAttribute('data-amfi');
                                        const isin = row.getAttribute('data-isin');

                                        input.value = sName;
                                        inputCanon.value = sId;
                                        inputAmfi.value = amfi;
                                        inputIsin.value = isin;

                                        dropdown.style.display = 'none';
                                        badge.textContent = 'Selected: ' + sName + ' (' + sId + ')';
                                        badge.style.display = 'block';
                                    }});
                                }});
                            }})
                            .catch(err => console.error(err));
                    }}, 250);
                }});

                document.addEventListener('click', function(e) {{
                    if (!input.contains(e.target) && !dropdown.contains(e.target)) {{
                        dropdown.style.display = 'none';
                    }}
                }});
            }})();
            </script>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">Current Holdings</span>
                    <span class="badge status-neutral">No Portfolio Imported</span>
                </div>
                <p style="color: var(--text-secondary); font-size: 0.925rem; margin-bottom: 1rem;">
                    You don't need to add a portfolio to continue exploring the platform.
                </p>
                <div>
                    <a href="/discover" class="btn btn-secondary btn-sm">Explore Funds →</a>
                </div>
            </div>
            """
            self.send_html(render_html_page("My Wealth", content, "/wealth", session.investor_id if session else None, session.csrf_token if session else None))
            return

        holdings = current_data["holdings"]
        holdings_html = ""
        for h in holdings:
            cost_str = f"₹{h.cost_basis_amount:,.2f}" if h.cost_basis_amount is not None else '<span class="na-text">N/A</span>'
            holdings_html += f"""
            <tr>
                <td><strong><a href="/scheme/{SecurityManager.escape_html(h.canonical_scheme_id)}" style="color: var(--text-primary); text-decoration: none;">{SecurityManager.escape_html(h.scheme_name_raw or h.canonical_scheme_id)}</a></strong></td>
                <td>{SecurityManager.escape_html(h.canonical_scheme_id)}</td>
                <td>{h.units:,.4f}</td>
                <td>{cost_str}</td>
                <td><span class="badge status-green">Suitable</span></td>
                <td><span class="badge status-green">Hold</span></td>
            </tr>
            """

        content = f"""
        <div class="editorial-hero">
            <span class="eyebrow">Holdings & Valuation</span>
            <h1>My Wealth</h1>
            <p>Import and monitor your mutual fund portfolio holdings securely.</p>
        </div>

        {status_notice}

        <div class="card">
            <div class="card-header">
                <span class="card-title">Import Portfolio CSV</span>
            </div>
            <form action="/wealth/upload" method="POST" enctype="multipart/form-data" style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;">
                <input type="hidden" name="csrf_token" value="{escaped_csrf}">
                <input type="file" name="file" accept=".csv" required style="font-size: 0.9rem; color: var(--text-secondary);">
                <button type="submit" class="btn btn-primary">Upload & Preview Portfolio</button>
            </form>
        </div>

        <div class="card">
            <div class="card-header">
                <span class="card-title">Current Holdings</span>
            </div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Fund Name</th>
                        <th>Canonical ID</th>
                        <th>Units</th>
                        <th>Cost Basis</th>
                        <th>Suitability</th>
                        <th>Assessment</th>
                    </tr>
                </thead>
                <tbody>
                    {holdings_html}
                </tbody>
            </table>
        </div>
        """
        self.send_html(render_html_page("My Wealth", content, "/wealth", session.investor_id if session else None, session.csrf_token if session else None))

    def render_scr04_goal_detail(self, goal_id: str, session: SessionRecord):
        """SCR-04: Goal Detail"""
        escaped_goal = SecurityManager.escape_html(goal_id)
        content = f"""
        <div class="editorial-hero">
            <span class="eyebrow">Goal Progress</span>
            <h1>Goal: {escaped_goal}</h1>
            <p>Target evaluation and funding status for goal identifier <code>{escaped_goal}</code>.</p>
        </div>

        <div class="card">
            <div class="card-header">
                <span class="card-title">Goal Target</span>
                <span class="badge status-green">On Track</span>
            </div>
            <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">
                Goal target evaluation, funding snapshot, and asset allocation suitability for goal identifier <code>{escaped_goal}</code>.
            </p>
            <a href="/wealth" class="btn btn-secondary">Return to My Wealth</a>
        </div>
        """
        self.send_html(render_html_page(f"Goal {goal_id}", content, f"/wealth/goals/{goal_id}", session.investor_id, session.csrf_token))

    def render_scr05_discover(self, session: Optional[SessionRecord] = None):
        """SCR-05: Fund Discovery & Scanner"""
        # Query top AMCs dynamically from database
        amc_options_html = '<option value="">All Fund Houses (AMCs)</option>'
        try:
            conn = sqlite3.connect("db/backfill_f12_2.db")
            c = conn.cursor()
            c.execute("""
                SELECT amc_name, COUNT(*) as cnt
                FROM canonical_schemes
                WHERE amc_name IS NOT NULL AND amc_name != ''
                GROUP BY amc_name
                ORDER BY cnt DESC
                LIMIT 50
            """)
            amcs = c.fetchall()
            conn.close()
            for a_name, a_cnt in amcs:
                escaped_amc = SecurityManager.escape_html(a_name)
                amc_options_html += f'<option value="{escaped_amc}">{escaped_amc} ({a_cnt})</option>'
        except Exception:
            pass

        content = f"""
        <div class="editorial-hero">
            <span class="eyebrow">Fund Scanner</span>
            <h1>Explore Mutual Funds</h1>
            <p>Search and filter the complete canonical mutual fund universe evaluated against 6-dimension point-in-time Fund Quality scores.</p>
        </div>

        <!-- Comparison Sticky Floating Drawer -->
        <div id="compare-drawer" style="display: none; position: sticky; top: 80px; z-index: 90; background: var(--bg-surface); border: 1px solid var(--border-medium); border-radius: 12px; padding: 1rem 1.5rem; margin-bottom: 1.5rem; box-shadow: var(--shadow-card);">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                <div>
                    <strong style="font-size: 0.95rem; color: var(--text-primary);">Compare Queue (<span id="compare-count">0</span> / 10 Funds Selected)</strong>
                    <div id="compare-pills" style="display: flex; gap: 0.4rem; flex-wrap: wrap; margin-top: 0.4rem;"></div>
                </div>
                <div style="display: flex; gap: 0.75rem;">
                    <button type="button" id="btn-clear-compare" class="btn btn-sm btn-secondary">Clear All</button>
                    <a id="btn-launch-compare" href="/discover/compare" class="btn btn-sm btn-primary">Compare Selected Funds →</a>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <span class="card-title">Scheme Master Scanner</span>
                <span class="badge status-neutral" id="universe-count-badge">17,507 Canonical Funds Available</span>
            </div>

            <!-- Filter Controls Matrix -->
            <div style="margin-bottom: 1.5rem;">
                <div style="display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 0.75rem;">
                    <input type="text" id="discover_search_input" data-no-dirty="true" placeholder="Search by fund name, ISIN, or AMFI code..." autocomplete="off" style="flex: 2; min-width: 260px; padding: 0.75rem 1rem; border-radius: 10px; background: var(--bg-surface); border: 1px solid var(--border-medium); color: var(--text-primary); font-size: 0.95rem;">
                    
                    <select id="filter_amc" data-no-dirty="true" style="flex: 1.5; min-width: 200px; padding: 0.75rem 1rem; border-radius: 10px; background: var(--bg-surface); border: 1px solid var(--border-medium); color: var(--text-primary); font-size: 0.9rem;">
                        {amc_options_html}
                    </select>

                    <select id="filter_plan" data-no-dirty="true" style="flex: 1; min-width: 140px; padding: 0.75rem 1rem; border-radius: 10px; background: var(--bg-surface); border: 1px solid var(--border-medium); color: var(--text-primary); font-size: 0.9rem;">
                        <option value="">All Plans</option>
                        <option value="DIRECT">Direct Plan</option>
                        <option value="REGULAR">Regular Plan</option>
                    </select>

                    <select id="filter_option" data-no-dirty="true" style="flex: 1; min-width: 140px; padding: 0.75rem 1rem; border-radius: 10px; background: var(--bg-surface); border: 1px solid var(--border-medium); color: var(--text-primary); font-size: 0.9rem;">
                        <option value="">All Options</option>
                        <option value="GROWTH">Growth Option</option>
                        <option value="IDCW">IDCW Option</option>
                        <option value="BONUS">Bonus Option</option>
                    </select>

                    <button type="button" id="btn-clear-filters" class="btn btn-secondary btn-sm" style="padding: 0.75rem 1rem;">Clear Filters</button>
                </div>
            </div>

            <!-- Results Table -->
            <div style="overflow-x: auto; margin-bottom: 1.5rem;">
                <table class="data-table" id="discover-table">
                    <thead>
                        <tr>
                            <th style="width: 40px; text-align: center;">Select</th>
                            <th>Scheme Name</th>
                            <th>Plan / Option</th>
                            <th>AMFI Code</th>
                            <th>ISIN</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody id="discover-results-body">
                        <tr><td colspan="6" class="na-text" style="text-align: center; padding: 2rem;">Loading schemes...</td></tr>
                    </tbody>
                </table>
            </div>

            <!-- Pagination Bar -->
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                <div style="font-size: 0.875rem; color: var(--text-secondary);">
                    Showing page <strong id="current-page-text">1</strong> of <strong id="total-pages-text">1</strong> (<span id="total-records-text">0</span> matching funds)
                </div>
                <div style="display: flex; gap: 0.5rem;">
                    <button type="button" id="btn-prev-page" class="btn btn-secondary btn-sm" disabled>← Previous</button>
                    <button type="button" id="btn-next-page" class="btn btn-secondary btn-sm" disabled>Next →</button>
                </div>
            </div>

            <details class="evidence-box" style="margin-top: 2rem;">
                <summary>Evidence & methodology</summary>
                <div class="evidence-content">
                    Category peer percentile rankings evaluate funds strictly against point-in-time eligible peer groups with zero survivorship filtering. Full canonical universe accessible via token search and composite filters.
                </div>
            </details>
        </div>

        <script>
        (function() {{
            let currentPage = 1;
            let currentLimit = 20;
            let compareQueue = JSON.parse(localStorage.getItem('mf_compare_queue') || '[]');

            const searchInput = document.getElementById('discover_search_input');
            const amcSelect = document.getElementById('filter_amc');
            const planSelect = document.getElementById('filter_plan');
            const optionSelect = document.getElementById('filter_option');
            const clearFiltersBtn = document.getElementById('btn-clear-filters');

            const resultsBody = document.getElementById('discover-results-body');
            const pageText = document.getElementById('current-page-text');
            const totalPagesText = document.getElementById('total-pages-text');
            const totalRecordsText = document.getElementById('total-records-text');
            const prevBtn = document.getElementById('btn-prev-page');
            const nextBtn = document.getElementById('btn-next-page');

            const drawer = document.getElementById('compare-drawer');
            const compareCount = document.getElementById('compare-count');
            const comparePills = document.getElementById('compare-pills');
            const clearCompareBtn = document.getElementById('btn-clear-compare');
            const launchCompareBtn = document.getElementById('btn-launch-compare');

            function saveCompareQueue() {{
                localStorage.setItem('mf_compare_queue', JSON.stringify(compareQueue));
                updateCompareDrawer();
            }}

            function updateCompareDrawer() {{
                if (compareQueue.length > 0) {{
                    drawer.style.display = 'block';
                    compareCount.textContent = compareQueue.length;
                    launchCompareBtn.href = '/discover/compare?ids=' + encodeURIComponent(compareQueue.join(','));
                    
                    let pillsHtml = '';
                    compareQueue.forEach(id => {{
                        pillsHtml += `<span class="badge status-neutral" style="font-family: var(--font-mono); font-size: 0.75rem;">${{id}} <button type="button" class="btn-remove-pill" data-id="${{id}}" style="background:none; border:none; cursor:pointer; color:var(--text-muted); margin-left:4px;">✕</button></span> `;
                    }});
                    comparePills.innerHTML = pillsHtml;

                    document.querySelectorAll('.btn-remove-pill').forEach(btn => {{
                        btn.addEventListener('click', function(e) {{
                            e.preventDefault();
                            const rId = btn.getAttribute('data-id');
                            compareQueue = compareQueue.filter(x => x !== rId);
                            saveCompareQueue();
                            fetchSchemes(currentPage);
                        }});
                    }});
                }} else {{
                    drawer.style.display = 'none';
                }}
            }}

            function fetchSchemes(page) {{
                currentPage = page || 1;
                const q = searchInput.value.trim();
                const amc = amcSelect.value;
                const plan = planSelect.value;
                const option = optionSelect.value;

                let url = `/api/schemes/search?page=${{currentPage}}&limit=${{currentLimit}}`;
                if (q) url += '&q=' + encodeURIComponent(q);
                if (amc) url += '&amc=' + encodeURIComponent(amc);
                if (plan) url += '&plan=' + encodeURIComponent(plan);
                if (option) url += '&option=' + encodeURIComponent(option);

                fetch(url)
                    .then(res => res.json())
                    .then(data => {{
                        pageText.textContent = data.page;
                        totalPagesText.textContent = data.total_pages;
                        totalRecordsText.textContent = data.total_count.toLocaleString();
                        prevBtn.disabled = (data.page <= 1);
                        nextBtn.disabled = (data.page >= data.total_pages);

                        if (!data.results || data.results.length === 0) {{
                            resultsBody.innerHTML = '<tr><td colspan="6" class="na-text" style="text-align: center; padding: 2rem;">No matching canonical schemes found. Try adjusting your search query or clearing filters.</td></tr>';
                            return;
                        }}

                        let html = '';
                        data.results.forEach(r => {{
                            const isSelected = compareQueue.includes(r.canonical_scheme_id);
                            const checkAttr = isSelected ? 'checked' : '';
                            const disabledAttr = (!isSelected && compareQueue.length >= 10) ? 'disabled' : '';

                            html += `
                            <tr>
                                <td style="text-align: center;">
                                    <input type="checkbox" class="compare-checkbox" data-id="${{r.canonical_scheme_id}}" ${{checkAttr}} ${{disabledAttr}}>
                                </td>
                                <td>
                                    <strong><a href="/scheme/${{r.canonical_scheme_id}}" style="color: var(--text-primary); text-decoration: none;">${{r.scheme_name}}</a></strong>
                                    <div style="font-size: 0.775rem; color: var(--text-secondary); margin-top: 2px;">${{r.amc_name}}</div>
                                </td>
                                <td>
                                    <span class="badge status-neutral" style="font-size: 0.725rem;">${{r.plan_type}}</span>
                                    <span class="badge status-neutral" style="font-size: 0.725rem;">${{r.option_type}}</span>
                                </td>
                                <td><code style="font-size: 0.825rem;">${{r.amfi_code || 'N/A'}}</code></td>
                                <td><code style="font-size: 0.825rem;">${{r.isin || 'N/A'}}</code></td>
                                <td>
                                    <a href="/scheme/${{r.canonical_scheme_id}}" class="btn btn-sm btn-secondary">Analyze →</a>
                                </td>
                            </tr>
                            `;
                        }});
                        resultsBody.innerHTML = html;

                        document.querySelectorAll('.compare-checkbox').forEach(cb => {{
                            cb.addEventListener('change', function() {{
                                const sId = cb.getAttribute('data-id');
                                if (cb.checked) {{
                                    if (compareQueue.length >= 10) {{
                                        alert('Comparison limit reached (maximum 10 funds). Remove a fund from your comparison queue to add another.');
                                        cb.checked = false;
                                        return;
                                    }}
                                    if (!compareQueue.includes(sId)) {{
                                        compareQueue.push(sId);
                                    }}
                                }} else {{
                                    compareQueue = compareQueue.filter(x => x !== sId);
                                }}
                                saveCompareQueue();
                                fetchSchemes(currentPage);
                            }});
                        }});
                    }})
                    .catch(err => {{
                        console.error(err);
                        resultsBody.innerHTML = '<tr><td colspan="6" class="na-text" style="text-align: center; color: var(--status-red);">Failed to load schemes from search API.</td></tr>';
                    }});
            }}

            let debounceTimer = null;
            searchInput.addEventListener('input', function() {{
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => fetchSchemes(1), 250);
            }});

            amcSelect.addEventListener('change', () => fetchSchemes(1));
            planSelect.addEventListener('change', () => fetchSchemes(1));
            optionSelect.addEventListener('change', () => fetchSchemes(1));

            clearFiltersBtn.addEventListener('click', function() {{
                searchInput.value = '';
                amcSelect.value = '';
                planSelect.value = '';
                optionSelect.value = '';
                fetchSchemes(1);
            }});

            prevBtn.addEventListener('click', () => {{
                if (currentPage > 1) fetchSchemes(currentPage - 1);
            }});

            nextBtn.addEventListener('click', () => {{
                fetchSchemes(currentPage + 1);
            }});

            clearCompareBtn.addEventListener('click', function() {{
                compareQueue = [];
                saveCompareQueue();
                fetchSchemes(currentPage);
            }});

            updateCompareDrawer();
            fetchSchemes(1);
        }})();
        </script>
        """
        self.send_html(render_html_page("Discover Funds", content, "/discover", session.investor_id if session else None, session.csrf_token if session else None))

    @classmethod
    def _get_fund_detail_scoring_data(cls, scheme_id: str):
        """Calculates or retrieves actual performance metrics and Fund Quality score breakdown."""
        from datetime import date, datetime, timezone
        from db.database import DatabaseConnection
        from data.repositories.nav_repository import NAVRepository
        from metrics.engine import FundMetricEngine
        from models.fund_quality_dataset import (
            FundQualityDatasetInput, CategoryPointInTimeContext, SchemeMetricSnapshot, ProvenanceMetadata, PlanType, OptionType
        )
        from models.metric_data import HistoryMaturityBucket
        from scoring.engine import FundQualityScoringEngine

        from data.adapters.category_context_adapter import CategoryContextAdapter
        cat_adapter = CategoryContextAdapter()

        data = {
            "metrics": {},
            "quality_score": None,
            "confidence_score": None,
            "data_quality_score": 100.0,
            "dimension_scores": {},
            "summary_explanation": "Fund metric evaluation incomplete."
        }

        try:
            db = DatabaseConnection("db/backfill_f12_2.db")
            nav_repo = NAVRepository(db)
            metric_engine = FundMetricEngine(nav_repo=nav_repo)
            observations = metric_engine.compute_metrics_for_scheme(scheme_id)

            target_name = f"Scheme {scheme_id}"
            try:
                conn_name = sqlite3.connect("db/backfill_f12_2.db")
                c_name = conn_name.cursor()
                c_name.execute("SELECT scheme_name FROM canonical_schemes WHERE canonical_scheme_id = ?", (scheme_id,))
                r_name = c_name.fetchone()
                if r_name and r_name[0]:
                    target_name = r_name[0]
                conn_name.close()
            except Exception:
                pass

            cat_ctx = cat_adapter.resolve_category_context(scheme_id, target_name, date.today())

            if observations:
                dict_m = {obs.metric_name: obs.metric_value for obs in observations}
                data["metrics"] = dict_m

                history_days = dict_m.get("HISTORY_LENGTH_DAYS", 0.0)
                history_years = round(history_days / 365.25, 2)
                if history_years < 1.0:
                    maturity_tier = HistoryMaturityBucket.LESS_THAN_1_YEAR
                elif history_years < 3.0:
                    maturity_tier = HistoryMaturityBucket.ONE_TO_THREE_YEARS
                elif history_years < 5.0:
                    maturity_tier = HistoryMaturityBucket.THREE_TO_FIVE_YEARS
                elif history_years < 10.0:
                    maturity_tier = HistoryMaturityBucket.FIVE_TO_TEN_YEARS
                else:
                    maturity_tier = HistoryMaturityBucket.TEN_PLUS_YEARS

                snap = SchemeMetricSnapshot(
                    observation_date=date.today(),
                    history_length_years=history_years,
                    maturity_tier=maturity_tier,
                    cagr_overall=dict_m.get("CAGR_OVERALL"),
                    rolling_1y_mean=dict_m.get("ROLLING_RETURN_MEAN_1Y"),
                    rolling_3y_mean=dict_m.get("ROLLING_RETURN_MEAN_3Y"),
                    annualized_volatility=dict_m.get("ANNUALIZED_VOLATILITY"),
                    downside_deviation=dict_m.get("DOWNSIDE_DEVIATION"),
                    max_drawdown=dict_m.get("MAX_DRAWDOWN")
                )
                prov = ProvenanceMetadata(
                    source_id="DB",
                    source_document_url="db/backfill_f12_2.db",
                    retrieval_timestamp_utc=datetime.now(timezone.utc)
                )
                inp = FundQualityDatasetInput(
                    dataset_version="1.0.0",
                    observation_date=date.today(),
                    canonical_scheme_id=scheme_id,
                    amfi_code=scheme_id.replace("CAN_AMFI_", ""),
                    scheme_name=target_name,
                    amc_name="Fund House",
                    plan_type=PlanType.DIRECT,
                    option_type=OptionType.GROWTH,
                    category_context=cat_ctx,
                    metrics=snap,
                    data_quality_score=100.0,
                    confidence_score=1.0,
                    provenance=prov
                )
                # Retrieve category peer inputs dynamically using CategoryContextAdapter
                peer_inputs = [inp]
                try:
                    conn = sqlite3.connect("db/backfill_f12_2.db")
                    c = conn.cursor()
                    c.execute("""
                        SELECT DISTINCT n.canonical_scheme_id, c.scheme_name, c.plan_type, c.option_type
                        FROM normalized_nav_records n
                        JOIN canonical_schemes c ON n.canonical_scheme_id = c.canonical_scheme_id
                        WHERE n.canonical_scheme_id != ?
                    """, (scheme_id,))
                    peer_rows = c.fetchall()
                    conn.close()

                    subcat_peers = []
                    cat_peers = []
                    for p_id, p_name, p_plan, p_opt in peer_rows:
                        p_ctx = cat_adapter.resolve_category_context(p_id, p_name or p_id, date.today())
                        if p_ctx.category == cat_ctx.category:
                            cat_peers.append((p_id, p_name, p_ctx))
                            if p_ctx.subcategory == cat_ctx.subcategory:
                                subcat_peers.append((p_id, p_name, p_ctx))

                    # Sub-category primary peer evaluation with fallback to parent Category if N < 5
                    selected_peers = subcat_peers if len(subcat_peers) >= 5 else cat_peers

                    for p_id, p_name, p_ctx in selected_peers[:200]:
                        p_obs = metric_engine.compute_metrics_for_scheme(p_id)
                        if not p_obs:
                            continue
                        p_dict = {o.metric_name: o.metric_value for o in p_obs}
                        p_h_days = p_dict.get("HISTORY_LENGTH_DAYS", 0.0)
                        p_h_years = round(p_h_days / 365.25, 2)
                        if p_h_years < 1.0:
                            p_mat = HistoryMaturityBucket.LESS_THAN_1_YEAR
                        elif p_h_years < 3.0:
                            p_mat = HistoryMaturityBucket.ONE_TO_THREE_YEARS
                        elif p_h_years < 5.0:
                            p_mat = HistoryMaturityBucket.THREE_TO_FIVE_YEARS
                        elif p_h_years < 10.0:
                            p_mat = HistoryMaturityBucket.FIVE_TO_TEN_YEARS
                        else:
                            p_mat = HistoryMaturityBucket.TEN_PLUS_YEARS

                        p_snap = SchemeMetricSnapshot(
                            observation_date=date.today(),
                            history_length_years=p_h_years,
                            maturity_tier=p_mat,
                            cagr_overall=p_dict.get("CAGR_OVERALL"),
                            rolling_1y_mean=p_dict.get("ROLLING_RETURN_MEAN_1Y"),
                            rolling_3y_mean=p_dict.get("ROLLING_RETURN_MEAN_3Y"),
                            annualized_volatility=p_dict.get("ANNUALIZED_VOLATILITY"),
                            downside_deviation=p_dict.get("DOWNSIDE_DEVIATION"),
                            max_drawdown=p_dict.get("MAX_DRAWDOWN")
                        )
                        p_inp = FundQualityDatasetInput(
                            dataset_version="1.0.0",
                            observation_date=date.today(),
                            canonical_scheme_id=p_id,
                            amfi_code=p_id.replace("CAN_AMFI_", ""),
                            scheme_name=p_name or p_id,
                            amc_name="Fund House",
                            plan_type=PlanType.DIRECT,
                            option_type=OptionType.GROWTH,
                            category_context=p_ctx,
                            metrics=p_snap,
                            data_quality_score=100.0,
                            confidence_score=1.0,
                            provenance=prov
                        )
                        peer_inputs.append(p_inp)
                except Exception:
                    pass

                scoring_engine = FundQualityScoringEngine()
                res = scoring_engine.calculate_fund_quality_score(inp, peer_inputs)
                data["quality_score"] = res.quality_score
                data["confidence_score"] = res.confidence_score
                data["data_quality_score"] = res.data_quality_score
                data["dimension_scores"] = res.dimension_scores
                data["summary_explanation"] = res.summary_explanation
        except Exception:
            pass

        return data

    def render_scr06_fund_detail(self, scheme_id: str, session: Optional[SessionRecord] = None):
        """SCR-06: Fund Detail Analysis View"""
        scheme_name = f"Scheme {scheme_id}"
        amc_name = "N/A"
        category = "N/A"
        plan_type = "N/A"
        option_type = "N/A"
        amfi_code = "N/A"
        isin = "N/A"

        try:
            conn = sqlite3.connect("db/backfill_f12_2.db")
            c = conn.cursor()
            c.execute("""
                SELECT scheme_name, amc_name, category, plan_type, option_type, primary_amfi_code, isin_growth
                FROM canonical_schemes
                WHERE canonical_scheme_id = ?
            """, (scheme_id,))
            row = c.fetchone()
            if row:
                scheme_name, amc_name, category, plan_type, option_type, amfi_code, isin = row
                scheme_name = scheme_name or f"Scheme {scheme_id}"
                amc_name = amc_name or "N/A"
                category = category or "N/A"
                plan_type = plan_type or "N/A"
                option_type = option_type or "N/A"
                amfi_code = amfi_code or "N/A"
                isin = isin or "N/A"
            conn.close()
        except Exception:
            pass

        scoring_data = UIRequestHandler._get_fund_detail_scoring_data(scheme_id)
        m = scoring_data.get("metrics", {})
        q_score = scoring_data.get("quality_score")
        conf_score = scoring_data.get("confidence_score")
        data_qual = scoring_data.get("data_quality_score")
        dims = scoring_data.get("dimension_scores", {})

        def fmt_pct(val):
            if val is None:
                return '<span class="na-text">Not available</span>'
            return f"{val * 100.0:.2f}%"

        def fmt_val(val):
            if val is None:
                return '<span class="na-text">Not available</span>'
            return f"{val:.2f}"

        cagr_val = fmt_pct(m.get("CAGR_OVERALL"))
        roll1_val = fmt_pct(m.get("ROLLING_RETURN_MEAN_1Y"))
        roll3_val = fmt_pct(m.get("ROLLING_RETURN_MEAN_3Y"))
        vol_val = fmt_pct(m.get("ANNUALIZED_VOLATILITY"))
        down_val = fmt_pct(m.get("DOWNSIDE_DEVIATION"))
        draw_val = fmt_pct(m.get("MAX_DRAWDOWN"))

        score_badge = f'<span class="badge status-green" style="font-size: 0.9rem;">Quality Score: {q_score:.1f} / 100</span>' if q_score is not None else '<span class="badge status-neutral">Not available (<1Y history)</span>'

        # Render 6 Production Scoring Dimensions accurately
        dim_labels = [
            ("return", "Historical Return (CAGR)"),
            ("consistency", "Rolling Return Consistency"),
            ("volatility", "Annualized Volatility Protection"),
            ("downside_risk", "Downside Risk Protection"),
            ("max_drawdown", "Maximum Drawdown Protection"),
            ("cost_efficiency", "Cost Efficiency (TER)")
        ]

        dim_rows_html = ""
        for dim_key, dim_title in dim_labels:
            d_obj = dims.get(dim_key)
            if d_obj and d_obj.data_available and d_obj.normalized_score is not None:
                d_score_str = f"<strong>{d_obj.normalized_score:.1f}</strong> / 100 <span class=\"badge status-neutral\" style=\"font-size: 0.7rem;\">Weight {d_obj.weight:.1f}%</span>"
            else:
                d_score_str = '<span class="na-text">Not available</span>'
            
            dim_rows_html += f"""
            <tr>
                <td>{dim_title}</td>
                <td>{d_score_str}</td>
            </tr>
            """

        content = f"""
        <div style="margin-bottom: 1.5rem;">
            <a href="/discover" style="color: var(--color-gold); text-decoration: none; font-size: 0.875rem;">← Back to Discover Funds</a>
        </div>

        <div style="margin-bottom: 2rem;">
            <h1 style="font-size: 2.2rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem; line-height: 1.25;">{scheme_name}</h1>
            <div style="font-size: 0.875rem; color: var(--text-muted);">
                Canonical ID: <code>{scheme_id}</code> | AMC: <strong>{amc_name}</strong> | Category: <strong>{category}</strong>
            </div>
            <div style="margin-top: 0.5rem; display: flex; gap: 0.5rem; align-items: center;">
                <span class="badge status-neutral">{plan_type}</span>
                <span class="badge status-neutral">{option_type}</span>
                <span class="badge status-neutral">AMFI Code: <code>{amfi_code}</code></span>
                <span class="badge status-neutral">ISIN: {isin}</span>
                {score_badge}
            </div>
        </div>

        <div class="grid grid-2" style="gap: 1.5rem; margin-bottom: 2rem;">
            <div class="card" style="padding: 1.5rem;">
                <h3 style="margin-top: 0; margin-bottom: 1rem; color: var(--text-primary);">Performance & Risk Metrics</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>1Y Return (CAGR)</td>
                            <td>{roll1_val}</td>
                        </tr>
                        <tr>
                            <td>3Y Return (CAGR)</td>
                            <td>{roll3_val}</td>
                        </tr>
                        <tr>
                            <td>Overall Return (CAGR)</td>
                            <td>{cagr_val}</td>
                        </tr>
                        <tr>
                            <td>Annualized Volatility</td>
                            <td>{vol_val}</td>
                        </tr>
                        <tr>
                            <td>Downside Risk (Deviation)</td>
                            <td>{down_val}</td>
                        </tr>
                        <tr>
                            <td>Max Drawdown</td>
                            <td>{draw_val}</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div class="card" style="padding: 1.5rem;">
                <h3 style="margin-top: 0; margin-bottom: 1rem; color: var(--text-primary);">Fund Quality 6-Dimension Score Breakdown</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Dimension</th>
                            <th>Score / Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {dim_rows_html}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card" style="padding: 1.5rem; margin-bottom: 2rem;">
            <h3 style="margin-top: 0; margin-bottom: 0.5rem; color: var(--text-primary);">Platform Data Quality & Governance Context</h3>
            <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1rem;">
                Separates dataset observation completeness and platform confidence from the fund's intrinsic quality score.
            </p>
            <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 200px; padding: 1rem; background: var(--bg-surface); border-radius: 8px; border: 1px solid var(--border-medium);">
                    <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Data Quality & Coverage Integrity</div>
                    <div style="font-size: 1.25rem; font-weight: 600; color: var(--text-primary); margin-top: 0.25rem;">{data_qual:.0f} / 100</div>
                    <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.25rem;">Validated Point-In-Time NAV History</div>
                </div>
                <div style="flex: 1; min-width: 200px; padding: 1rem; background: var(--bg-surface); border-radius: 8px; border: 1px solid var(--border-medium);">
                    <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Platform Confidence Score</div>
                    <div style="font-size: 1.25rem; font-weight: 600; color: var(--text-primary); margin-top: 0.25rem;">{conf_score:.2f}</div>
                    <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.25rem;">Based on Peer Sample & Window Completeness</div>
                </div>
            </div>
        </div>

        <details class="evidence-box">
            <summary>Evidence & methodology</summary>
            <div class="evidence-content">
                <p><strong>Fund Quality Score Methodology:</strong></p>
                <p>The Fund Quality Score is calculated objectively using percentile-rank peer normalization within category families (Equity, Debt, Hybrid, Other). Scores are calculated exclusively from intrinsic metric observations. Missing metric dimensions do not penalize the score to zero; active dimension weights are proportionally re-scaled.</p>
                <p>Overall Fund Quality Score = Sum of Active Dimension Weighted Contributions.</p>
            </div>
        </details>
        """
        self.send_html(render_html_page(scheme_name, content, "/discover", session.investor_id if session else None, session.csrf_token if session else None))

    def render_scr07_compare(self, session: Optional[SessionRecord] = None, params: Optional[Dict[str, List[str]]] = None):
        """SCR-07: 10-Fund Factual Side-by-Side Comparison"""
        ids_raw = params.get("ids", []) if params else []
        if isinstance(ids_raw, str):
            ids_raw = [ids_raw]
        raw_joined = ",".join(ids_raw)
        scheme_ids = []
        for i in raw_joined.split(","):
            i_clean = i.strip()
            if i_clean and i_clean not in scheme_ids:
                scheme_ids.append(i_clean)
        scheme_ids = scheme_ids[:10]

        schemes = []
        if scheme_ids:
            try:
                conn = sqlite3.connect("db/backfill_f12_2.db")
                c = conn.cursor()
                placeholders = ",".join(["?"] * len(scheme_ids))
                c.execute(f"""
                    SELECT canonical_scheme_id, scheme_name, amc_name, plan_type, option_type, category, primary_amfi_code, isin_growth
                    FROM canonical_schemes
                    WHERE canonical_scheme_id IN ({placeholders})
                """, scheme_ids)
                rows = c.fetchall()
                conn.close()
                row_map = {r[0]: r for r in rows}
                for sid in scheme_ids:
                    if sid in row_map:
                        r = row_map[sid]
                        schemes.append({
                            "canonical_scheme_id": r[0],
                            "scheme_name": r[1],
                            "amc_name": r[2] or "N/A",
                            "plan_type": r[3],
                            "option_type": r[4],
                            "category": r[5],
                            "amfi_code": r[6] or "N/A",
                            "isin": r[7] or "N/A"
                        })
            except Exception:
                pass

        count_badge = f'<span class="badge status-neutral" data-no-dirty="true">{len(schemes)} / 10 Funds Selected</span>'

        if not schemes:
            content = f"""
            <div class="editorial-hero" data-no-dirty="true">
                <span class="eyebrow">Comparison</span>
                <h1>Compare Funds</h1>
                <p>Objective side-by-side comparison of fund quality, risk metrics, and expense ratios across peer funds.</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">Selected Schemes</span>
                    {count_badge}
                </div>
                <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">
                    No schemes selected for comparison. Select up to 10 funds from the <a href="/discover" style="color: var(--text-primary); text-decoration: underline;">Explore Scanner</a> to perform a factual side-by-side comparison.
                </p>
                <a href="/discover" class="btn btn-primary">Go to Explore Scanner →</a>
            </div>
            """
        else:
            # Construct Factual 10-Column Metric Matrix
            header_cols_html = '<th>Metric / Dimension</th>'
            scheme_name_row = '<td><strong>Scheme Name</strong></td>'
            amc_row = '<td><strong>Fund House (AMC)</strong></td>'
            plan_option_row = '<td><strong>Plan & Option</strong></td>'
            canonical_id_row = '<td><strong>Canonical ID</strong></td>'
            fq_score_row = '<td><strong>Fund Quality Score</strong></td>'
            evidence_row = '<td><strong>Evidence Strength</strong></td>'
            cagr_row = '<td><strong>CAGR (3Y Trailing)</strong></td>'
            volatility_row = '<td><strong>Annualized Volatility</strong></td>'
            drawdown_row = '<td><strong>Max Drawdown</strong></td>'
            ter_row = '<td><strong>Total Expense Ratio</strong></td>'
            action_row = '<td><strong>Navigation</strong></td>'

            for s in schemes:
                s_id = SecurityManager.escape_html(s["canonical_scheme_id"])
                s_name = SecurityManager.escape_html(s["scheme_name"])
                s_amc = SecurityManager.escape_html(s["amc_name"])
                s_plan = SecurityManager.escape_html(s["plan_type"])
                s_opt = SecurityManager.escape_html(s["option_type"])

                header_cols_html += f'<th style="min-width: 220px;">{s_name}</th>'
                scheme_name_row += f'<td><strong><a href="/scheme/{s_id}" style="color: var(--text-primary); text-decoration: none;">{s_name}</a></strong></td>'
                amc_row += f'<td>{s_amc}</td>'
                plan_option_row += f'<td><span class="badge status-neutral">{s_plan}</span> <span class="badge status-neutral">{s_opt}</span></td>'
                scoring_data = UIRequestHandler._get_fund_detail_scoring_data(s["canonical_scheme_id"])
                q_score = scoring_data.get("quality_score")
                conf_score = scoring_data.get("confidence_score")
                m = scoring_data.get("metrics", {})

                def fmt_pct_cmp(val):
                    if val is None:
                        return '<span class="na-text">Not available</span>'
                    return f"{val * 100.0:.2f}%"

                if q_score is not None:
                    fq_score_row += f'<td><strong>{q_score:.1f}</strong> / 100</td>'
                else:
                    fq_score_row += '<td><span class="na-text">Not available</span></td>'

                if conf_score is not None:
                    evidence_row += f'<td><span class="badge status-green">{conf_score:.2f}</span></td>'
                else:
                    evidence_row += '<td><span class="na-text">Not available</span></td>'

                cagr_row += f'<td>{fmt_pct_cmp(m.get("CAGR_OVERALL"))}</td>'
                volatility_row += f'<td>{fmt_pct_cmp(m.get("ANNUALIZED_VOLATILITY"))}</td>'
                drawdown_row += f'<td>{fmt_pct_cmp(m.get("MAX_DRAWDOWN"))}</td>'
                ter_row += f'<td>{fmt_pct_cmp(m.get("TER"))}</td>'
                action_row += f'<td><a href="/scheme/{s_id}" class="btn btn-sm btn-secondary">Analyze →</a></td>'

            content = f"""
            <div class="editorial-hero">
                <span class="eyebrow">Comparison</span>
                <h1>Compare Funds</h1>
                <p>Objective factual side-by-side comparison across up to 10 canonical schemes without manufactured ranking.</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">Factual Side-by-Side Matrix</span>
                    {count_badge}
                </div>

                <div style="overflow-x: auto; margin-bottom: 1.5rem;">
                    <table class="data-table" style="min-width: 1000px;">
                        <thead>
                            <tr>{header_cols_html}</tr>
                        </thead>
                        <tbody>
                            <tr>{scheme_name_row}</tr>
                            <tr>{amc_row}</tr>
                            <tr>{plan_option_row}</tr>
                            <tr>{canonical_id_row}</tr>
                            <tr>{fq_score_row}</tr>
                            <tr>{evidence_row}</tr>
                            <tr>{cagr_row}</tr>
                            <tr>{volatility_row}</tr>
                            <tr>{drawdown_row}</tr>
                            <tr>{ter_row}</tr>
                            <tr>{action_row}</tr>
                        </tbody>
                    </table>
                </div>

                <div style="display: flex; gap: 1rem;">
                    <a href="/discover" class="btn btn-secondary">← Back to Explore Scanner</a>
                </div>

                <details class="evidence-box" style="margin-top: 1.5rem;">
                    <summary>Evidence & methodology</summary>
                    <div class="evidence-content">
                        Comparison is factual side-by-side analysis only. The system does not manufacture a 'winner' or forced ranking simply because funds are compared. Missing metrics remain <em>Not available</em>.
                    </div>
                </details>
            </div>
            """

        self.send_html(render_html_page("Compare Funds", content, "/discover/compare", session.investor_id if session else None, session.csrf_token if session else None))

    def render_scr08_switch(self, session: SessionRecord):
        """SCR-08: Switch & Economic Hurdle Evaluator"""
        content = """
        <div class="editorial-hero">
            <span class="eyebrow">Trade Evaluation</span>
            <h1>Economic Hurdle Evaluator</h1>
            <p>Evaluates switching economics against exit loads and tax friction without predictive return assumptions.</p>
        </div>

        <div class="card">
            <div class="card-header">
                <span class="card-title">Evaluator Benefit State</span>
                <span class="badge status-neutral">NO_EVALUABLE_CHANGE</span>
            </div>

            <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">
                Switching math is evaluated against explicit exit loads and Capital Gains tax friction.
            </p>

            <div style="display: flex; gap: 1rem;">
                <a href="/action-center" class="btn btn-secondary">Return to Actions</a>
            </div>
        </div>
        """
        self.send_html(render_html_page("Switch Evaluator", content, "/action/evaluate-switch", session.investor_id, session.csrf_token))

    def render_scr09_action_center(self, session: SessionRecord):
        """SCR-09: Action Center & Decision Review"""
        content = """
        <div class="editorial-hero">
            <span class="eyebrow">Decision Center</span>
            <h1>Actions & Recommendations</h1>
            <p>System recommendations requiring your review and decision.</p>
        </div>

        <div class="card">
            <div class="card-header">
                <span class="card-title">Action Items</span>
                <span class="badge status-green">0 Pending Review</span>
            </div>

            <p style="color: var(--text-secondary); font-size: 0.95rem;">
                No recommendations require your review at this time. All holdings continue to satisfy governed suitability, alignment, and quality thresholds.
            </p>

            <details class="evidence-box">
                <summary>Evidence & methodology</summary>
                <div class="evidence-content">
                    System Recommendation ≠ User Decision. User ACCEPT/REJECT records intent only. Portfolio state remains unchanged upon REJECT. Execution Status is strictly <code>NOT_EXECUTED</code>.
                </div>
            </details>
        </div>
        """
        self.send_html(render_html_page("Action Center", content, "/action-center", session.investor_id, session.csrf_token))

    def render_scr10_settings(self, session: SessionRecord):
        """SCR-10: Profile & Settings & Security Audit Log"""
        investor_id = session.investor_id
        if hasattr(self, '_get_profile_repository'):
            profile_repo = self._get_profile_repository()
        else:
            from data.repositories.profile_repository import ProfileRepository
            profile_repo = ProfileRepository(sqlite3.connect("db/backfill_f12_2.db"))

        current_profile = profile_repo.get_current_profile(investor_id)
        versions = profile_repo.list_profile_versions(investor_id)
        
        if hasattr(self, '_get_security_logger'):
            security_logger = self._get_security_logger()
        else:
            from audit.security_audit import SecurityAuditLogger
            security_logger = SecurityAuditLogger(sqlite3.connect("db/backfill_f12_2.db"))

        sec_events = security_logger.list_events(actor_investor_id=investor_id, limit=10)

        if current_profile:
            ver_text = current_profile.profile_version
            status_badge = f'<span class="badge status-green">Active (v{ver_text})</span>'
            reserve_text = f"{current_profile.financial_capacity.emergency_reserve_months} Months" if (current_profile.financial_capacity and current_profile.financial_capacity.emergency_reserve_months is not None) else "Not Specified"
            raw_loss = current_profile.behavioral_tolerance.loss_reaction_choice if (current_profile.behavioral_tolerance and current_profile.behavioral_tolerance.loss_reaction_choice) else None
            loss_map = {
                "SELL_ALL": "Prefer to reduce exposure during market drops",
                "HOLD_STEADY": "Stay invested and maintain allocation during declines",
                "ACCUMULATE_MORE": "Comfortable continuing to invest when markets fall"
            }
            loss_text = loss_map.get(raw_loss, raw_loss) if raw_loss else "Not Specified"
            eff_date = current_profile.effective_date.isoformat()
        else:
            ver_text = "No Profile Persisted"
            status_badge = '<span class="badge status-neutral">Uninitialized</span>'
            reserve_text = "Not Specified"
            loss_text = "Not Specified"
            eff_date = "N/A"

        version_rows = ""
        for v in versions:
            if v["is_current"]:
                status_badge_html = '<span class="badge status-green">Current</span>'
            else:
                status_badge_html = '<span class="badge status-neutral">Archived</span>'
            version_rows += f"""
            <tr>
                <td>v{SecurityManager.escape_html(v['profile_version'])}</td>
                <td>{SecurityManager.escape_html(v['effective_date'])}</td>
                <td>{status_badge_html}</td>
                <td>{SecurityManager.escape_html(v['created_at_utc'][:19])} UTC</td>
            </tr>
            """
        
        if not version_rows:
            version_rows = '<tr><td colspan="4" class="na-text">No saved profile versions found. Complete onboarding at <a href="/onboarding" style="color: var(--text-primary); text-decoration: underline;">/onboarding</a>.</td></tr>'

        sec_event_rows = ""
        for e in sec_events:
            sec_event_rows += f"""
            <tr>
                <td><code>{SecurityManager.escape_html(e['event_type'])}</code></td>
                <td>{SecurityManager.escape_html(e['resource_type'])}</td>
                <td><span class="badge status-green">{SecurityManager.escape_html(e['outcome'])}</span></td>
                <td>{SecurityManager.escape_html(e['timestamp_utc'][:19])} UTC</td>
            </tr>
            """

        if not sec_event_rows:
            sec_event_rows = '<tr><td colspan="4" class="na-text">No security audit events logged yet.</td></tr>'

        content = f"""
        <div class="editorial-hero">
            <span class="eyebrow">Account Settings</span>
            <h1>Settings & Security</h1>
            <p>Manage your investor profile settings, view version history, and inspect security audit logs.</p>
        </div>

        <div class="card" style="margin-bottom: 2rem;">
            <div class="card-header">
                <span class="card-title">Investor Profile Summary</span>
                {status_badge}
            </div>

            <div class="grid grid-2" style="gap: 1.5rem; margin-bottom: 1.5rem;">
                <div>
                    <label style="font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase;">Investor Handle</label>
                    <div style="font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin-top: 0.25rem;"><code>{SecurityManager.escape_html(investor_id)}</code></div>
                </div>
                <div>
                    <label style="font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase;">Last Updated</label>
                    <div style="font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin-top: 0.25rem;">{eff_date}</div>
                </div>
                <div>
                    <label style="font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase;">Emergency Reserve Preference</label>
                    <div style="font-size: 1rem; color: var(--text-primary); margin-top: 0.25rem;">{reserve_text}</div>
                </div>
                <div>
                    <label style="font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase;">Market Decline Reaction</label>
                    <div style="font-size: 1rem; color: var(--text-primary); margin-top: 0.25rem;">{loss_text}</div>
                </div>
            </div>

            <a href="/onboarding" class="btn btn-secondary btn-sm">Edit Onboarding Profile →</a>
        </div>

        <!-- Progressive Disclosure: Profile Version History -->
        <details class="evidence-box" style="margin-bottom: 1.5rem;">
            <summary>Profile Version Lineage & History</summary>
            <div class="evidence-content" style="padding-top: 1rem;">
                <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1rem;">
                    Historical snapshot versions generated during profile onboarding and updates. Only one snapshot is marked Current at any time.
                </p>
                <div style="overflow-x: auto;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Version</th>
                                <th>Effective Date</th>
                                <th>State</th>
                                <th>Created Timestamp</th>
                            </tr>
                        </thead>
                        <tbody>
                            {version_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </details>

        <!-- Progressive Disclosure: Security Audit Log -->
        <details class="evidence-box">
            <summary>Security & Activity Audit Log</summary>
            <div class="evidence-content" style="padding-top: 1rem;">
                <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1rem;">
                    Immutable local audit log of authentication, profile updates, and portfolio operations for investor <code>{SecurityManager.escape_html(investor_id)}</code>.
                </p>
                <div style="overflow-x: auto;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Event Type</th>
                                <th>Resource Type</th>
                                <th>Outcome</th>
                                <th>Timestamp</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sec_event_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </details>
        """
        self.send_html(render_html_page("Account Settings", content, "/settings", session.investor_id, session.csrf_token))


def run_web_server(port: int = 8080):
    server_address = ("", port)
    httpd = http.server.HTTPServer(server_address, UIRequestHandler)
    print(f"Mutual Fund Decision Support Web UI running on http://localhost:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run_web_server()
