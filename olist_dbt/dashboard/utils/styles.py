"""
Shared styling and reusable HTML components.

WHY THIS FILE EXISTS:
    Your pages have repeated HTML patterns — context boxes, analysis sidepanels,
    section headers. Each one uses slightly different padding, font sizes, and 
    structure. This creates two problems:
    
    1. INCONSISTENCY: The analysis panel in "Operational Failures" uses 
       "Analysis Overview → Key Insight" but "Quality Issues" uses 
       "Analysis Overview → Investigability → Recovery Priority → Next Steps".
       Viewers unconsciously notice these structural shifts.
    
    2. MAINTENANCE BURDEN: To change the accent color of all context boxes, 
       you'd need to edit every page file. With this module, it's one change.

DESIGN SYSTEM:
    We define a consistent semantic color palette:
    - Red (#DC2626)    → Failure, loss, critical problems
    - Amber (#F59E0B)  → Warning, at-risk, needs attention  
    - Blue (#2563EB)   → Informational, operational, neutral analysis
    - Green (#059669)  → Success, growth, positive outcomes
    - Gray (#64748B)   → Unknown, silent churn, no data
    
    These meanings stay consistent ACROSS ALL PAGES.
"""
import streamlit as st


# ============================================================
# COLOR SYSTEM — Semantic meanings, consistent everywhere
# ============================================================
COLORS = {
    # Primary semantic colors
    "failure":      "#DC2626",  # Red — acquisition failures, critical issues
    "failure_bg":   "#FEF2F2",
    "failure_text": "#991B1B",

    "warning":      "#F59E0B",  # Amber — at-risk, quality issues
    "warning_bg":   "#FEF3C7",
    "warning_text":  "#92400E",

    "info":         "#2563EB",  # Blue — informational, operational
    "info_bg":      "#EFF6FF",
    "info_text":    "#1E40AF",

    "success":      "#059669",  # Green — growth, active, positive
    "success_bg":   "#F0FDF4",
    "success_text": "#065F46",

    "neutral":      "#64748B",  # Gray — unknown, silent churn
    "neutral_bg":   "#F8FAFC",
    "neutral_text": "#475569",

    # Page-specific: Customer segments (used in overview sunburst + page routing)
    "seg_failed":       "#DC2626",
    "seg_at_risk":      "#8B5CF6",  # Purple — distinct from red/amber
    "seg_at_risk_bg":   "#FDF4FF",
    "seg_at_risk_text": "#6B21A8",
    "seg_active":       "#059669",

    # Accountability colors (identifiable issues page)
    "seller":       "#DC2626",  # Red — seller accountability
    "logistics":    "#1D4ED8",  # Deep blue — logistics accountability
    "economic":     "#2563EB",  # Blue — economic barriers
}


# ============================================================
# GLOBAL CSS — Applied once in streamlit_app.py
# ============================================================
GLOBAL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 0rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    .stApp {
        background-color: #F8F9FA;
    }

    /* Metric cards with blue accent */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border-left: 4px solid #2563EB;
    } 
            
    div[data-testid="stMetric"] label {
        color: #6B7280;
        font-size: 0.875rem;
        font-weight: 500;
    }
            
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.875rem;
        font-weight: 700;
        color: #111827;
    }

    /* Tab styling for consistency */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        font-weight: 500;
    }
</style>
"""


# ============================================================
# REUSABLE COMPONENTS — Standardized HTML patterns
# ============================================================

def context_box(message: str, variant: str = "info") -> str:
    """
    Page-level context box that frames the analytical question.
    
    This is the first thing viewers see on each page. It answers:
    "What am I looking at and why should I care?"
    
    Args:
        message: HTML string with the context content
        variant: "info" (blue), "failure" (red), "warning" (amber), "success" (green)
    
    Usage:
        st.markdown(context_box("Your message here", variant="failure"), unsafe_allow_html=True)
    """
    bg = COLORS.get(f"{variant}_bg", COLORS["info_bg"])
    border = COLORS.get(variant, COLORS["info"])
    text = COLORS.get(f"{variant}_text", COLORS["info_text"])

    return f"""<div style="background-color:{bg}; padding:16px; border-radius:8px; margin-bottom:24px; border-left:4px solid {border};">
<p style="margin:0; color:{text}; font-size:0.95rem; line-height:1.7;">
{message}
</p>
</div>"""


def analysis_sidepanel(
    context: str,
    finding: str,
    action: str,
    border_color: str = "#2563EB",
    extra_sections: str = ""
) -> str:
    """
    Standardized analysis panel (col2) that accompanies each chart.
    
    CONSISTENT STRUCTURE — every sidepanel follows the same anatomy:
        1. Context   → What you're looking at (data scope, definitions)
        2. Finding   → What the data shows (the insight)
        3. Action    → What to do about it (the recommendation)
        4. [Optional extra sections for page-specific needs]
    
    WHY STANDARDIZE:
        Your current panels have different structures:
        - Operational: "Analysis Overview → Key Insight"
        - Quality: "Analysis Overview → Investigability → Recovery Priority → Next Steps"
        - Promo: "Analysis Overview → Recommended Strategy → Key Insight"
        
        An employer scanning quickly will unconsciously feel this inconsistency.
        Same structure everywhere = professional, polished, trustworthy.
    
    Args:
        context: HTML string explaining what the viewer is looking at
        finding: HTML string with the key data insight
        action: HTML string with recommended next steps
        border_color: Left border accent color
        extra_sections: Additional HTML to insert before the action section
    """
    # CRITICAL: HTML must start at column 0 (no leading indentation).
    # Streamlit's markdown parser processes line-by-line. When HTML tags have
    # 4+ spaces of indentation AND there's an empty/whitespace-only line
    # (which happens when {extra_sections} is ""), the parser exits HTML block
    # mode and treats subsequent indented lines as literal text — causing the
    # raw <hr>, <h4>Action</h4>, <p> tags to display on screen.
    extra = extra_sections if extra_sections else ""
    return f"""<div style="background-color:#F8FAFC; padding:20px; border-radius:8px; border-left:4px solid {border_color}; margin-top:10px;">
<h4 style="margin:0 0 15px 0; color:#1E293B; font-size:1.1rem;">Context</h4>
<p style="margin:0 0 15px 0; font-size:0.9rem; color:#475569; line-height:1.6;">
{context}
</p>
<hr style="border:none; border-top:1px solid #E2E8F0; margin:15px 0;">
<h4 style="margin:0 0 12px 0; color:#1E293B; font-size:1rem;">Finding</h4>
<p style="margin:0 0 15px 0; font-size:0.9rem; color:#475569; line-height:1.6;">
{finding}
</p>
{extra}
<hr style="border:none; border-top:1px solid #E2E8F0; margin:15px 0;">
<h4 style="margin:0 0 10px 0; color:#1E293B; font-size:0.95rem;">Action</h4>
<p style="margin:0; font-size:0.85rem; color:#475569; line-height:1.5; background-color:#FEF3C7; padding:10px; border-radius:6px; border-left:3px solid #F59E0B;">
{action}
</p>
</div>"""


def progress_bar(label: str, value: float, count: int, color: str) -> str:
    """
    Reusable progress bar component used in sidepanels.
    
    Args:
        label: What this bar represents (e.g., "Seller Responsibility")
        value: Percentage value (0-100)
        count: Absolute number to show below the bar
        color: Bar fill color
    """
    # Lighten the color for the background track
    bg_color = color + "33"  # Add 20% opacity hex
    
    return f"""<div style="margin-bottom:15px;">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
<span style="font-size:0.85rem; color:#64748B;">{label}</span>
<span style="font-size:0.95rem; font-weight:700; color:{color};">{value:.1f}%</span>
</div>
<div style="background-color:#F1F5F9; border-radius:4px; height:8px; width:100%;">
<div style="background-color:{color}; border-radius:4px; height:8px; width:{value:.1f}%;"></div>
</div>
<p style="margin:5px 0 0 0; font-size:0.8rem; color:#64748B;">{count:,} orders</p>
</div>"""


def chart_instruction_box(instruction: str) -> str:
    """
    Interactive chart instruction box — tells the viewer how to interact.
    Used above sunburst, icicle, and other clickable charts.
    """
    return f"""<div style="background-color:#EFF6FF; padding:14px 18px; border-radius:8px; border-left:4px solid #2563EB; margin-bottom:16px; display:flex; align-items:center; gap:12px;">
<span style="font-size:1.3rem;">&#9757;</span>
<div>
<strong style="color:#1E40AF; font-size:1rem;">Interactive Chart</strong>
<p style="margin:4px 0 0 0; color:#1E40AF; font-size:0.88rem; line-height:1.5;">
{instruction}
</p>
</div>
</div>"""


def page_navigation_footer(next_page_title: str, next_page_description: str) -> str:
    """
    Footer CTA that bridges pages together into a story.
    
    WHY THIS EXISTS:
        Without explicit handoffs, each page feels like an isolated analysis.
        With navigation footers, the dashboard becomes a guided narrative:
        Overview → "X customers never got their orders → see why" → Failed Acquisition
        Failed Acquisition → "Y customers have fixable issues → see which" → Identifiable Issues
        
    This is the connective tissue that turns 4 separate pages into one cohesive story.
    """
    return f"""<div style="margin-top:40px; padding:16px 20px; border-radius:8px; background-color:#F8FAFC; border:1px solid #E2E8F0; display:flex; justify-content:space-between; align-items:center;">
<div>
<p style="margin:0 0 4px 0; font-size:0.8rem; color:#94A3B8; text-transform:uppercase; letter-spacing:0.05em;">Next Step</p>
<p style="margin:0; font-size:0.95rem; color:#1E293B; font-weight:600;">
{next_page_title}
</p>
<p style="margin:4px 0 0 0; font-size:0.85rem; color:#64748B;">
{next_page_description}
</p>
</div>
<span style="font-size:1.5rem; color:#2563EB;">&rarr;</span>
</div>"""
