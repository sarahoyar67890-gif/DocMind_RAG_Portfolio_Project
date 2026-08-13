"""
style.py — DocMind visual identity (premium dark theme).

Design tokens:

Color
  --bg            #06070B   near-black charcoal base
  --bg-elev       #0B0D14   slightly raised background band
  --surface       glass card fill (translucent white over dark)
  --surface-solid #12141C   solid dark card fallback
  --surface-2     #0D0F17   recessed panels (upload well)
  --ink           #F2F3F6   primary text
  --ink-muted     #9AA1B2   secondary text
  --ink-faint     #676E7D   tertiary / placeholder text
  --border        translucent hairline borders
  --accent        #8B7CFF   violet — primary AI accent
  --accent-2      #4FD1E8   cyan — secondary accent, used in gradients
  --accent-deep   #6C5CE8
  --gold          #F2B84B   citation / source accent
  --green         #34D399   grounded / success
  --red           #FB7185   ungrounded / error

Type
  Display : "Sora"          — headline / UI display, geometric & modern
  Body    : "Inter"         — UI text, paragraphs
  Mono    : "JetBrains Mono"— citations, technical readouts, page numbers

Signature element: the "highlight sweep" — abstracted document lines with an
animated gradient highlighter bar inside a glassmorphism panel, echoing the
product's core value (grounded answers, visibly tied to a passage). A soft
twin-tone glow (violet + cyan) sits behind the hero panel and pulses gently.
"""

FONT_IMPORT = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
"""

CSS = """
<style>
:root {
  --bg: #06070B;
  --bg-elev: #0B0D14;
  --surface: rgba(255,255,255,0.045);
  --surface-hover: rgba(255,255,255,0.07);
  --surface-solid: #12141C;
  --surface-2: #0D0F17;
  --ink: #F2F3F6;
  --ink-muted: #9AA1B2;
  --ink-faint: #676E7D;
  --border: rgba(255,255,255,0.09);
  --border-strong: rgba(255,255,255,0.18);
  --accent: #8B7CFF;
  --accent-2: #4FD1E8;
  --accent-deep: #6C5CE8;
  --accent-soft: rgba(139,124,255,0.12);
  --accent-gradient: linear-gradient(135deg, #8B7CFF 0%, #6C5CE8 55%, #4FD1E8 100%);
  --gold: #F2B84B;
  --gold-soft: rgba(242,184,75,0.09);
  --gold-border: rgba(242,184,75,0.30);
  --gold-ink: #F7CC77;
  --green: #34D399;
  --green-soft: rgba(52,211,153,0.12);
  --green-border: rgba(52,211,153,0.30);
  --red: #FB7185;
  --red-soft: rgba(251,113,133,0.12);
  --red-border: rgba(251,113,133,0.32);
  --radius-xl: 26px;
  --radius-lg: 20px;
  --radius-md: 14px;
  --radius-sm: 10px;
  --shadow-card: 0 20px 50px -24px rgba(0,0,0,0.65);
  --shadow-glow-accent: 0 0 0 1px rgba(139,124,255,0.18), 0 12px 36px -14px rgba(139,124,255,0.35);
}

* { box-sizing: border-box; }

html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  color: var(--ink);
}

.stApp {
  background:
    radial-gradient(1100px 620px at 12% -8%, rgba(139,124,255,0.16), transparent 60%),
    radial-gradient(900px 560px at 108% 8%, rgba(79,209,232,0.11), transparent 55%),
    radial-gradient(1200px 800px at 50% 115%, rgba(108,92,232,0.10), transparent 60%),
    var(--bg);
  overflow-x: hidden;
}
body { overflow-x: hidden; }

#MainMenu, header[data-testid="stHeader"], footer, [data-testid="stToolbar"] { visibility: hidden; height: 0; }
.block-container {
  padding-top: 2.25rem;
  padding-bottom: 4rem;
  max-width: 1120px;
}
@media (max-width: 640px) {
  .block-container { padding-left: 1.1rem; padding-right: 1.1rem; padding-top: 1.5rem; }
}

h1, h2, h3, h4 {
  font-family: 'Sora', sans-serif;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--ink);
}
h3 { font-size: 1.35rem; margin-bottom: 0.2rem; }
p, span, div, label, li { color: var(--ink); }
.dm-muted { color: var(--ink-muted) !important; }
.mono { font-family: 'JetBrains Mono', monospace; }

::selection { background: rgba(139,124,255,0.35); color: #fff; }

/* scrollbar */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.14); border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.24); }

/* ---------- shared building blocks ---------- */
.eyebrow {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem; letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--accent-2); font-weight: 500;
  display: inline-flex; align-items: center; gap: 0.45rem;
}
.eyebrow::before {
  content: ""; width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent-gradient);
  box-shadow: 0 0 10px 1px rgba(139,124,255,0.7);
  display: inline-block;
}
.section-head { margin-bottom: 1.15rem; }
.section-head h3 { margin-top: 0.35rem; }

.hairline {
  border: none; height: 1px; margin: 2.75rem 0;
  background: linear-gradient(90deg, transparent, var(--border) 20%, var(--border) 80%, transparent);
}

.fade-in { animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) both; }
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ---------- top brand row ---------- */
.dm-brand { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 2.2rem; }
.dm-brand-mark {
  width: 30px; height: 30px; border-radius: 9px;
  background: var(--accent-gradient);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 6px 18px -4px rgba(139,124,255,0.6);
  flex-shrink: 0;
}
.dm-brand-mark svg { width: 16px; height: 16px; }
.dm-brand-name {
  font-family: 'Sora', sans-serif; font-weight: 700; font-size: 1rem; letter-spacing: -0.01em; color: var(--ink);
}
.dm-brand-tag {
  font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: var(--ink-faint);
  border-left: 1px solid var(--border); padding-left: 0.6rem; margin-left: 0.1rem;
}

/* ---------- hero ---------- */
.dm-hero { display: grid; grid-template-columns: 1.08fr 0.92fr; gap: 2.75rem; align-items: center; padding: 0.5rem 0 1.25rem 0; }
@media (max-width: 900px) { .dm-hero { grid-template-columns: 1fr; gap: 2.25rem; } }
.dm-hero h1 {
  font-size: 2.9rem; line-height: 1.08; margin: 0.75rem 0 1rem 0;
  background: linear-gradient(180deg, #FFFFFF 0%, #C9CCDA 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
@media (max-width: 640px) { .dm-hero h1 { font-size: 2.1rem; } }
.dm-hero .dm-sub { font-size: 1.04rem; color: var(--ink-muted); max-width: 48ch; line-height: 1.6; margin-bottom: 0; }
.dm-note {
  margin-top: 1.5rem; font-size: 0.85rem; color: var(--ink-muted);
  border-left: 2px solid var(--accent); padding: 0.15rem 0 0.15rem 0.9rem; max-width: 46ch; line-height: 1.55;
}

/* signature highlight-sweep panel */
.doc-panel-wrap { position: relative; }
.doc-panel-wrap::before {
  content: ""; position: absolute; inset: -30px;
  background: radial-gradient(circle at 30% 20%, rgba(139,124,255,0.35), transparent 55%),
              radial-gradient(circle at 80% 80%, rgba(79,209,232,0.28), transparent 55%);
  filter: blur(38px);
  opacity: 0.85;
  z-index: 0;
  animation: glowPulse 6s ease-in-out infinite;
}
@keyframes glowPulse {
  0%, 100% { opacity: 0.65; transform: scale(1); }
  50% { opacity: 0.95; transform: scale(1.04); }
}
.doc-panel {
  position: relative; z-index: 1;
  aspect-ratio: 4 / 3.6;
  background: linear-gradient(155deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-card);
  padding: 34px 30px;
}
.doc-line { height: 9px; border-radius: 5px; background: rgba(255,255,255,0.09); margin-bottom: 13px; position: relative; }
.doc-line.w1 { width: 92%; } .doc-line.w2 { width: 78%; } .doc-line.w3 { width: 85%; }
.doc-line.w4 { width: 60%; } .doc-line.w5 { width: 88%; } .doc-line.w6 { width: 70%; }
.doc-highlight {
  position: absolute; left: -6px; right: -6px; top: -3px; bottom: -3px;
  border-radius: 6px; background: var(--accent-gradient); opacity: 0;
  box-shadow: 0 0 16px 1px rgba(139,124,255,0.55);
  animation: sweep-highlight 4.8s ease-in-out infinite;
}
.doc-line.w2 .doc-highlight { animation-delay: 0.9s; }
.doc-line.w5 .doc-highlight { animation-delay: 2.1s; }
@keyframes sweep-highlight {
  0%, 100% { opacity: 0; }
  6%, 22% { opacity: 0.9; }
  30% { opacity: 0; }
}
.doc-citation-pin {
  position: absolute; top: 26px; right: 26px;
  font-family: 'JetBrains Mono', monospace; font-size: 0.68rem;
  background: var(--gold-soft); color: var(--gold-ink);
  border: 1px solid var(--gold-border); border-radius: 999px; padding: 0.28rem 0.7rem;
  font-weight: 600;
}
.doc-footer-tag {
  position: absolute; bottom: 28px; left: 30px; right: 30px;
  font-family: 'JetBrains Mono', monospace; font-size: 0.66rem; letter-spacing: 0.05em;
  color: var(--ink-faint); text-transform: uppercase;
  display: flex; flex-wrap: wrap; gap: 0.3rem 0.5rem;
}
.doc-footer-tag b { color: var(--accent-2); font-weight: 600; }

/* ---------- alerts ---------- */
.dm-alert {
  display: flex; gap: 0.85rem; align-items: flex-start;
  border-radius: var(--radius-lg); padding: 1.1rem 1.3rem;
  border: 1px solid var(--border); background: var(--surface);
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
}
.dm-alert-icon { flex-shrink: 0; width: 34px; height: 34px; border-radius: 10px; display: flex; align-items: center; justify-content: center; }
.dm-alert-icon svg { width: 18px; height: 18px; }
.dm-alert-body { min-width: 0; }
.dm-alert .eyebrow { margin-bottom: 0.3rem; }
.dm-alert p { margin: 0.3rem 0 0 0; font-size: 0.92rem; line-height: 1.55; color: var(--ink-muted); overflow-wrap: break-word; }
.dm-alert code {
  background: rgba(255,255,255,0.08); padding: 0.1rem 0.4rem; border-radius: 5px;
  font-family: 'JetBrains Mono', monospace; font-size: 0.84em; color: var(--ink);
}
.dm-alert-warning { border-color: var(--gold-border); }
.dm-alert-warning .dm-alert-icon { background: var(--gold-soft); color: var(--gold-ink); }
.dm-alert-warning .eyebrow { color: var(--gold-ink); }
.dm-alert-warning .eyebrow::before { background: var(--gold); box-shadow: 0 0 10px 1px rgba(242,184,75,0.6); }
.dm-alert-error { border-color: var(--red-border); }
.dm-alert-error .dm-alert-icon { background: var(--red-soft); color: var(--red); }
.dm-alert-error .eyebrow { color: var(--red); }
.dm-alert-error .eyebrow::before { background: var(--red); box-shadow: 0 0 10px 1px rgba(251,113,133,0.6); }

/* ---------- cards ---------- */
.dm-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1.7rem 1.9rem;
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  box-shadow: var(--shadow-card);
  transition: border-color 0.2s ease, transform 0.2s ease;
}
.dm-card-tight { padding: 1.25rem 1.45rem; }
.dm-card-accent { background: linear-gradient(155deg, rgba(139,124,255,0.10), rgba(79,209,232,0.05)); border-color: rgba(139,124,255,0.28); }

/* ---------- process steps ---------- */
.step-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.15rem; margin-top: 1.1rem; }
@media (max-width: 900px) { .step-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 560px) { .step-grid { grid-template-columns: 1fr; } }
.step-card {
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md);
  padding: 1.3rem 1.35rem; transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}
.step-card:hover { transform: translateY(-3px); border-color: var(--border-strong); background: var(--surface-hover); }
.step-num {
  font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.02em;
  width: 30px; height: 30px; border-radius: 9px;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--accent-soft); color: var(--accent-2);
  border: 1px solid rgba(139,124,255,0.28);
}
.step-title { font-family: 'Sora', sans-serif; font-size: 1.02rem; font-weight: 600; margin: 0.7rem 0 0.35rem 0; }
.step-desc { font-size: 0.87rem; color: var(--ink-muted); line-height: 1.55; margin: 0; overflow-wrap: break-word; }

/* ---------- upload hint ---------- */
.upload-hint {
  display: flex; align-items: center; gap: 1rem;
  border: 1px dashed var(--border-strong); border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  border-bottom: none; background: var(--surface-2);
  padding: 1.4rem 1.5rem 1.1rem 1.5rem;
}
.upload-hint-icon {
  flex-shrink: 0; width: 42px; height: 42px; border-radius: 12px;
  background: var(--accent-gradient); display: flex; align-items: center; justify-content: center;
  box-shadow: 0 8px 22px -8px rgba(139,124,255,0.6);
}
.upload-hint-icon svg { width: 21px; height: 21px; color: white; }
.upload-hint-title { font-family: 'Sora', sans-serif; font-weight: 600; font-size: 0.98rem; margin: 0; }
.upload-hint-sub { font-size: 0.82rem; color: var(--ink-muted); margin: 0.2rem 0 0 0; }

/* ---------- processing checklist ---------- */
.proc-item { display: flex; align-items: center; gap: 0.7rem; padding: 0.5rem 0; font-size: 0.92rem; overflow-wrap: break-word; }
.proc-check {
  width: 20px; height: 20px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
  font-size: 0.72rem; color: #06070B; background: var(--green); flex-shrink: 0; font-weight: 700;
}
.proc-detail { color: var(--ink-faint); font-size: 0.78rem; font-family: 'JetBrains Mono', monospace; margin-left: auto; padding-left: 0.6rem; white-space: nowrap; }

/* ---------- active document ---------- */
.doc-status-row { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 1rem; }
.doc-status-name {
  font-family: 'Sora', sans-serif; font-size: 1.18rem; font-weight: 600; margin-top: 0.45rem;
  overflow-wrap: break-word; word-break: break-word; max-width: 46ch;
}
.doc-status-icon {
  width: 40px; height: 40px; border-radius: 11px; background: var(--green-soft); border: 1px solid var(--green-border);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.doc-status-icon svg { width: 20px; height: 20px; color: var(--green); }

/* ---------- spec grid ---------- */
.spec-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.1rem; margin-top: 1.1rem; }
@media (max-width: 900px) { .spec-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 480px) { .spec-grid { grid-template-columns: 1fr; } }
.spec-item {
  border-left: 2px solid var(--accent); padding: 0.15rem 0 0.15rem 0.9rem;
  min-width: 0;
}
.spec-key { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink-faint); }
.spec-val { font-size: 0.96rem; font-weight: 500; margin-top: 0.2rem; overflow-wrap: break-word; }

/* ---------- chat / answer ---------- */
[data-testid="stChatMessage"] {
  background: var(--surface) !important; border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important; backdrop-filter: blur(14px);
  padding: 0.4rem 0.2rem !important; margin-bottom: 0.9rem;
}
[data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] {
  background: var(--accent-gradient) !important;
}
.answer-card { padding: 0.4rem 0.6rem 0.2rem 0.6rem; }
.grounded-badge {
  display: inline-flex; align-items: center; gap: 0.4rem;
  font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; letter-spacing: 0.06em;
  text-transform: uppercase; padding: 0.32rem 0.7rem; border-radius: 999px; font-weight: 600; margin-bottom: 1rem;
  border: 1px solid transparent;
}
.grounded-badge::before { content: ""; width: 6px; height: 6px; border-radius: 50%; }
.badge-grounded { background: var(--green-soft); color: var(--green); border-color: var(--green-border); }
.badge-grounded::before { background: var(--green); box-shadow: 0 0 8px 1px rgba(52,211,153,0.7); }
.badge-ungrounded { background: var(--red-soft); color: var(--red); border-color: var(--red-border); }
.badge-ungrounded::before { background: var(--red); box-shadow: 0 0 8px 1px rgba(251,113,133,0.7); }
.answer-text { font-size: 1rem; line-height: 1.68; overflow-wrap: break-word; color: var(--ink); }

/* ---------- source cards ---------- */
.source-card {
  background: var(--gold-soft); border: 1px solid var(--gold-border); border-radius: var(--radius-md);
  padding: 1.05rem 1.2rem; margin-bottom: 0.8rem;
}
.source-head { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 0.35rem 0.8rem; margin-bottom: 0.55rem; }
.source-page { font-family: 'JetBrains Mono', monospace; font-weight: 600; color: var(--gold-ink); font-size: 0.85rem; }
.source-sim { font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: var(--ink-muted); white-space: nowrap; }
.source-excerpt { font-size: 0.89rem; line-height: 1.55; color: var(--ink-muted); overflow-wrap: break-word; }

/* ---------- limitations ---------- */
.limits-card {
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg);
  padding: 1.7rem 1.9rem; backdrop-filter: blur(14px);
}
.limits-head { display: flex; align-items: center; gap: 0.7rem; margin-bottom: 0.9rem; }
.limits-head-icon {
  width: 34px; height: 34px; border-radius: 10px; background: var(--gold-soft); border: 1px solid var(--gold-border);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.limits-head-icon svg { width: 17px; height: 17px; color: var(--gold-ink); }
.limits-card h4 { margin: 0; color: var(--ink); font-size: 1.05rem; }
.limits-card ul { margin: 0; padding-left: 1.2rem; }
.limits-card li { margin-bottom: 0.55rem; line-height: 1.58; font-size: 0.92rem; color: var(--ink-muted); overflow-wrap: break-word; }
.limits-card li:last-child { margin-bottom: 0; }
.limits-card b { color: var(--ink); }

/* ---------- footer ---------- */
.dm-footer {
  margin-top: 3rem; padding-top: 1.8rem; border-top: 1px solid var(--border);
  display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.9rem;
}
.dm-footer-brand { display: flex; align-items: center; gap: 0.55rem; font-size: 0.85rem; color: var(--ink-muted); }
.dm-footer-brand svg { width: 15px; height: 15px; color: var(--accent-2); flex-shrink: 0; }
.dm-footer-pills { display: flex; flex-wrap: wrap; gap: 0.45rem; }
.dm-footer-pill {
  font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: var(--ink-muted);
  background: var(--surface); border: 1px solid var(--border); border-radius: 999px; padding: 0.28rem 0.65rem;
}

/* ---------- widget overrides ---------- */
[data-testid="stFileUploader"] {
  border: 1px dashed var(--border-strong);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  background: var(--surface-2);
  padding: 0.9rem;
  transition: border-color 0.2s ease, background 0.2s ease;
}
[data-testid="stFileUploader"]:hover { border-color: var(--accent); background: rgba(139,124,255,0.05); }
[data-testid="stFileUploaderDropzone"] { background: transparent !important; }
[data-testid="stFileUploader"] section { background: transparent !important; border: none !important; }
[data-testid="stFileUploader"] small, [data-testid="stFileUploader"] span { color: var(--ink-faint) !important; }
[data-testid="stFileUploader"] button {
  background: var(--surface-solid) !important; color: var(--ink) !important;
  border: 1px solid var(--border-strong) !important; border-radius: var(--radius-sm) !important;
}
[data-testid="stFileUploader"] button:hover { border-color: var(--accent) !important; color: var(--accent-2) !important; }

.stButton > button {
  background: var(--accent-gradient); color: #ffffff; border: none; border-radius: var(--radius-sm);
  padding: 0.6rem 1.5rem; font-family: 'Inter', sans-serif; font-weight: 600; font-size: 0.92rem;
  box-shadow: 0 8px 22px -10px rgba(139,124,255,0.55);
  transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
}
.stButton > button:hover { filter: brightness(1.08); transform: translateY(-1px); box-shadow: 0 12px 28px -10px rgba(139,124,255,0.7); }
.stButton > button:active { transform: translateY(0); }
.stButton > button:focus-visible { outline: 2px solid var(--accent-2); outline-offset: 2px; }
.stButton > button:disabled {
  background: var(--surface-solid); color: var(--ink-faint) !important; box-shadow: none;
  border: 1px solid var(--border);
}
.stButton > button p { color: inherit !important; font-weight: 600; }

[data-testid="stExpander"] {
  border: 1px solid var(--border) !important; border-radius: var(--radius-md) !important;
  background: var(--surface) !important; overflow: hidden;
}
[data-testid="stExpander"] summary { color: var(--ink) !important; font-weight: 500; }
[data-testid="stExpander"] summary:hover { color: var(--accent-2) !important; }

[data-testid="stChatInput"] {
  border: 1px solid var(--border-strong) !important; border-radius: var(--radius-lg) !important;
  background: var(--surface-solid) !important;
}
[data-testid="stChatInput"] textarea { font-family: 'Inter', sans-serif; color: var(--ink) !important; }
[data-testid="stChatInput"] textarea::placeholder { color: var(--ink-faint) !important; }

[data-testid="stAlert"] {
  background: var(--surface) !important; border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important; color: var(--ink) !important;
}
[data-testid="stAlertContentSuccess"], [data-testid="stAlertContentSuccess"] p { color: var(--green) !important; }
[data-testid="stAlertContentError"], [data-testid="stAlertContentError"] p { color: var(--red) !important; }

[data-testid="stSpinner"] p { color: var(--ink-muted) !important; }

code { color: var(--accent-2); }
</style>
"""


def inject(st) -> None:
    st.markdown(FONT_IMPORT, unsafe_allow_html=True)
    st.markdown(CSS, unsafe_allow_html=True)
