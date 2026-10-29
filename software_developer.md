# Developer Operational Guide & Architecture Blueprint
## Project: Kalphora Equity — SEBI RA Turnkey Platform
**Target Audience:** Software Engineering Team, Technical Leads, and System Architects  
**Client:** M Kalpesh (Kalphora Equity) | **Partner Agency:** Vintush Tech / KP RegTech  
**Commercials:** ₹95,000 INR (Fixed Scope) | 1st Year AMC: Complimentary  
**Timeline:** 4-Week Delivery Sprint (Baseline: Oct 10, 2026 ➔ Target Go-Live: Nov 7, 2026)  
**Client Survey Status:** Confirmed via Questionnaire CSV Submission (Oct 27, 2026)  

---

## 1. The Core Mandate: What This Software Must Do

Kalphora Equity is a solo-founder business run by **M Kalpesh** (CFA Level 1, NISM Research Analyst certified, 10+ years market experience). He is launching an independent stock research practice under **SEBI Research Analyst (RA)** regulations.

Our mission is to build a turnkey, dual-vertical platform:
1. **Public Regulatory Storefront:** Educates visitors, separates research advisory from course education, publishes statutory disclosures, captures leads, and displays a compliant performance track record.
2. **Secure Client Portal (`portal.kalphora.com`):** Serves 25–45 paying clients initially (scaling to 150), strictly paywalls premium research recommendations, dynamically watermarks report PDFs to prevent leaks, immutably logs all recommendations for SEBI audits, and automates Razorpay subscriptions.

---

## 2. "Must-Remember" Engineering Rules & Critical Traps

These are the non-negotiable architectural rules, regulatory traps, and technical gotchas that every developer on this project must keep in mind at all times:

### A. Django & Database Rules (Avoid Costly Rework)
* **Rule #1: Custom User Model BEFORE First Migration:**  
  Never run `python manage.py migrate` on default Django settings. Create the `accounts` app and configure `CustomUser(AbstractUser)` with `phone`, `pan_number`, and `kyc_status` first. Changing `AUTH_USER_MODEL` after initial tables exist corrupts foreign keys and requires dropping the database.
* **Rule #2: Clean Single-Root Layout (`config .`):**  
  Do not create nested project folders (e.g., `kalpesh/kalpesh`). Run `django-admin startproject config .` so `manage.py` lives cleanly in the root.
* **Rule #3: Never Store Premium Research PDFs in Public Folders:**  
  Research PDFs must **never** be placed in `STATIC_ROOT` or standard public `MEDIA_ROOT`. Nginx must be configured to block direct public HTTP access to `/secure_reports/`. All report downloads must be routed through an authenticated Django view that checks active subscription status before streaming bytes.
* **Rule #4: Decoupled App Design:**  
  Keep client-facing templates and views in `apps/` (`storefront`, `portal`, `billing`) and reusable compliance/security logic in `core_regtech/` (`compliance`, `security`). This maintains clean code boundaries for our IP.

---

### B. SEBI Regulatory & Legal Compliance Rules (Zero-Tolerance)
* **Rule #5: SEBI Regulation 25 Record-Keeping Mandate:**  
  Under Regulation 25 of SEBI (Research Analysts) Regulations, 2014, all stock recommendations must be retained for a **minimum of 5 years**. Once an analyst publishes a call, the system must create an immutable, timestamped snapshot containing:
  - Exact date and UTC timestamp of release
  - Recommended stock ticker and company name
  - Entry price range, target price, and stop-loss
  - Research rationale and risk disclosures
  - Subsequent updates or exit calls with timestamps  
  *Never allow an admin to silently edit or delete past published recommendations in the database.*
* **Rule #6: Guard the Public Performance Track Record:**  
  The client requested a public "Closed Calls" track record table to prove past performance. SEBI strictly regulates performance claims. You **must** ensure this section prominently displays the mandatory statutory disclaimer: *"Past performance is not indicative of future returns. Investments in securities market are subject to market risks."*
* **Rule #7: Regulatory Segregation of Advisory vs. Education:**  
  SEBI requires Research Analysts to maintain clear operational boundaries between fee-based stock research (advisory) and training/courses (education). Ensure navigation, messaging, and database models treat these as distinct modules.
* **Rule #8: Investor Charter & Grievance Redressal Matrix:**  
  Every page header and footer must feature persistent disclosures. Dedicated links to the **SEBI SCORES portal** and **SMART ODR platform** must be present on the public website and inside the client portal.

---

### C. Content Protection & Anti-Piracy Realities
* **Rule #9: Client-Side Tricks Are Not Security:**  
  Disabling right-click (`contextmenu`) or blocking `Ctrl+P` in the browser is merely a mild inconvenience; anyone with developer tools can bypass it.
* **Rule #10: Dynamic Watermarking is the Real Deterrent:**  
  Our primary anti-piracy weapon is dynamic, server-side watermarking. Every time a paying subscriber downloads or opens a report, Python must dynamically stamp a 45° semi-transparent watermark containing:
  ```
  CONFIDENTIAL - LICENSED TO: [CLIENT FULL NAME]
  PAN: [ABCDE****F] | ACCESS TIME: [UTC TIMESTAMP] | IP: [CLIENT IP]
  ```
  If the PDF is leaked to Telegram or WhatsApp, the subscriber’s legal PAN and identity are stamped across every page, providing an overwhelming psychological and legal deterrent.
* **Rule #11: No Expensive Third-Party DRM (Save Client Costs):**  
  The client was unsure about third-party DRM tools like MaiPDF ($30–$90/month). We use our native Python engine (ReportLab/PyPDF). It costs ₹0 recurring, runs on our server, and keeps client data confidential.

---

### D. Payments & Webhook Automation Gotchas
* **Rule #12: Never Trust Frontend Payment Redirects:**  
  Never activate a client’s subscription based on a browser JavaScript callback or redirect URL. Users can close browsers, network connections drop, and URLs can be spoofed.
* **Rule #13: Rely Exclusively on Cryptographic Webhooks:**  
  Subscription activation, expiry date updates, and invoice creation must happen **only** inside the server-to-server webhook endpoint (`/billing/webhook/razorpay/`), verified with the cryptographic HMAC-SHA256 signature secret.
* **Rule #14: Idempotency is Mandatory:**  
  Payment gateways retry webhooks multiple times. Your webhook handler must check if the payment ID has already been processed before extending dates or generating duplicate invoices.
* **Rule #15: Automated Access Expiry:**  
  When a quarterly (90-day) or annual (365-day) plan lapses, the system must automatically downgrade the user to "Free User" status without deleting their profile. They keep access to the Free Learning Hub but are prompted to renew.

---

### E. Intellectual Property (IP) & Handover Boundaries
* **Rule #16: Zero Obfuscation or Sneaky Locks:**  
  Do not use PyArmor, compiled `.pyc` files, or encrypted code. The client is paying for a turnkey platform and will receive the complete, clean source code repository.
* **Rule #17: Clean Handover to Year-2 Developers:**  
  Write standard, idiomatic Django following PEP 8. A replacement developer hired in Year 2 must be able to clone the repo, run migrations, and understand the code within hours.
* **Rule #18: The Dual-Licensing Boundary:**  
  - **Client Deliverables:** Kalpesh owns his brand ("Kalphora Equity"), logo, custom templates, client data, and research reports 100%.
  - **Agency Background IP:** Our reusable compliance engine, automated audit log mechanisms, and watermarking utilities in `core_regtech/` remain our proprietary framework, licensed to Kalpesh perpetually and royalty-free for Kalphora Equity. He cannot extract our engine and resell it as a SaaS product to other analysts.

---

### F. Client Expectations & Communication
* **Rule #19: Deliver the Staging Demo Early (Milestone 1):**  
  Kalpesh specifically requested: *"I would like to review a basic wireframe or demo before full development."* Deliver the public storefront shell, logo, and login flow on a private staging server by the end of Week 1 so he sees visual momentum immediately.
* **Rule #20: Solo-Founder Self-Service:**  
  Kalpesh has no in-house technical team. He must be able to publish stock picks, update call statuses, and export his client list to Excel/CSV directly from the Django Admin without calling a developer.
* **Rule #21: Hold Firm on Scope:**  
  Native mobile apps (iOS/Android) and heavy 100-hour video streaming LMS are strictly **Phase 3 ("Grow")** items. Keep the 4-week sprint laser-focused on the website, portal, anti-piracy, and SEBI compliance.

---

## 3. What We Have to Build: Feature Breakdown & Responsibilities

```
=============================================================================
                       PLATFORM ARCHITECTURAL OVERVIEW
=============================================================================
[ PUBLIC STOREFRONT ]
  ├── Home Page (Hero, Value Prop, Founder Bio)
  ├── Dual-Vertical Separation (Advisory vs. Education)
  ├── Free Learning Hub / Concept Explainers (Lead Magnet)
  ├── Public Performance Track Record (Closed Calls + SEBI Disclaimers)
  ├── Investor Charter, Disclosures & Grievance Matrix (SCORES / SMART ODR)
  └── Lead Capture Form (Free Registered User Onboarding)

[ CLIENT PORTAL - portal.kalphora.com ]
  ├── Single Authentication Flow (Free User vs. Active Paid Subscriber)
  ├── Onboarding Gate: Profile, Risk Assessment & Click-Wrap MITC Agreement
  ├── Premium Research Feed:
  │     ├── Fields: Ticker, Reco Date, Entry Range, Target, Stop-Loss,
  │     │           Holding Period, Rationale, Risk Disclosure
  │     └── Status Badges: Fresh Call | Open | Update | Target Met | Stop-Loss | Exit
  ├── Anti-Piracy Engine: Dynamic PDF Watermarking (Name, PAN, Time, IP)
  ├── Protected Media Streaming (No direct public links)
  ├── Billing Hub: Plans (Quarterly/Annual), Invoices, Renewal Countdown
  └── Support & Grievance Ticketing Desk

[ COMPLIANCE & ADMIN ENGINE ]
  ├── SEBI Regulation 25 Immutable Audit Log (SHA-256 Snapshots)
  ├── Automated Timestamping on Every Recommendation & Mutation
  ├── Client List Export (Active/Expired Subscribers to Excel/CSV)
  └── Razorpay Webhook State Machine (Instant Automated Provisioning)
=============================================================================
```

### Detailed Functional Responsibilities:

#### 1. Public Storefront & Regulatory Front-End
- **Brand Identity:** Implement modern SVG logo and favicons using the agreed high-trust palette: **Navy (`#0F172A`)**, **Gold (`#D97706`)**, and **White (`#F8FAFC`)**.
- **Dual Verticals:** Clearly separate the Research Advisory services from the Education Academy in top navigation and landing sections.
- **Free Learning Hub / Blog:** A lightweight CMS module for market concepts, glossary terms, and educational explainers.
- **Public Closed Calls Track Record:** A clean table showing completed/closed calls (entry, exit, holding timeframe, return) protected by statutory SEBI disclaimers.
- **Statutory Infrastructure:** Header and footer disclosures across every single page. Modal/page for the SEBI Investor Charter and Grievance Redressal escalation matrix.

#### 2. Client Portal & Content Gatekeeper (`portal.kalphora.com`)
- **Single Auth / Two Experience Levels:**
  - *Free User:* Can log in, read educational articles, view course syllabus, see closed calls track record, and access an "Upgrade to Premium" button.
  - *Active Paid Subscriber:* Accesses real-time stock recommendations, detailed research notes, dynamic watermarked PDF reports, and support tickets.
- **Onboarding Workflow:** Upon upgrading, the user completes their profile (PAN, residential state), takes a simple risk profiling questionnaire, and clicks to accept the digital MITC (Most Important Terms & Conditions) and Risk Disclosure. The system records the IP address, timestamp, and document version.
- **Research Recommendation Feed:** Every card/modal must clearly show:
  - Ticker & Exchange (`NSE: RELIANCE`)
  - Reco Date and Exit Date
  - Entry Price Range, Target Price, Stop-Loss Price
  - Holding Timeframe (e.g., "1–3 Weeks")
  - Status Badge (`Fresh Call`, `Open`, `Update`, `Target Achieved`, `Stop-Loss Hit`, `Exit Call`)
  - Full research rationale and SEBI risk disclaimer
- **Dynamic Watermarking & Protected Streaming:**
  - Reports stored outside public web folders.
  - Streaming view intercepts request, verifies active subscription, dynamically stamps the subscriber's PAN and Name across every page using ReportLab/PyPDF, and streams the bytes inline.
- **Support & Grievances:** In-portal ticketing module allowing subscribers to raise queries or lodge official grievances.

#### 3. Compliance Engine (SEBI Regulation 25)
- **Immutable Audit Logging:** Post-save signal intercepts every creation or modification of a recommendation.
- **Tamper-Evident SHA-256 Hashing:** Creates a cryptographic hash of the state snapshot (price, target, rationale, timestamp) and stores it in an un-editable audit table.
- **5-Year Retention Readiness:** Provide a 1-click admin export function so Kalpesh can produce historical recommendation records instantly during a SEBI audit inspection.

#### 4. Payments, Billing & Webhooks (Razorpay)
- **Plan Configuration:** Quarterly (₹5,000–₹6,000) and Annual (₹20,000–₹25,000) packages.
- **Webhook State Machine:** Listen for `payment.captured` and `order.paid`. Verify HMAC signature. Automatically set `status='ACTIVE'`, compute `end_date = start_date + duration`, generate a GST tax invoice, and trigger a confirmation email.
- **Expiry Daemon:** Daily Celery/cron task that flags subscriptions as `EXPIRED` on D-0 and sends renewal reminders at T-7, T-3, and T-1 days.

#### 5. Self-Service Admin Panel
- Tailored Django Admin for Kalpesh:
  - Quick-add recommendation form with auto-filled timestamps.
  - 1-click status update buttons.
  - Subscriber list with plan tier, expiration countdown, and 1-click CSV/Excel export.
  - Filterable audit trail viewer.

---

## 4. The 4-Week Milestone Execution Plan

*Sprint Window:* October 10, 2026 ➔ November 7, 2026 (Delivery Deadline)

| Sprint Week | Focus Area | Engineering Tasks & Deliverables | Testing & Review Checkpoints |
| :---: | :--- | :--- | :--- |
| **Week 1** | **Scaffolding, Identity & Staging Demo** | • Configure Django 5 with `config .` layout<br>• Create `accounts` app with `CustomUser` (PAN/Phone)<br>• Design brand identity (SVG logo, Navy/Gold palette)<br>• Deploy staging server with basic auth and admin | **Milestone 1 Demo (Friday):**<br>Kalpesh reviews live staging build, tests login, and verifies brand identity. |
| **Week 2** | **Storefront & Regulatory Front-End** | • Build dual-vertical marketing storefront<br>• Implement Free Learning Hub / Blog CMS<br>• Build Public Closed Calls Track Record with disclaimers<br>• Implement SEBI Header/Footer, Investor Charter & Grievance Matrix | **Milestone 2 Review (Friday):**<br>Verify responsive design on mobile/desktop; audit all statutory disclosure links. |
| **Week 3** | **Client Portal, Security & Audits** | • Configure subdomain routing (`portal.kalphora.com`)<br>• Build Recommendation Feed with lifecycle status badges<br>• Implement Dynamic PDF Watermarking Engine (PAN/Name/IP)<br>• Build SEBI Reg 25 immutable audit log engine & signals<br>• Build Support & Grievance ticketing module | **Milestone 3 Review (Friday):**<br>Test paywall barriers (free vs. paid); test watermark rendering on sample PDF; verify audit log immutability. |
| **Week 4** | **Payments, Training & Go-Live** | • Integrate Razorpay checkout modal<br>• Implement webhook state machine & automated invoicing<br>• Configure Celery expiry reminder cron<br>• Production VPS hardening (Nginx, SSL, UFW, fail2ban)<br>• Conduct 1-on-1 Admin Training with Kalpesh | **Milestone 4 Handover (Nov 7):**<br>End-to-end sandbox payment test; verify automated access unlock; complete production launch. |

---

## 5. Scope Management: What is IN vs. What is DEFERRED

To guarantee high quality within the ₹95,000 budget and meet the November 7 deadline, developers must enforce strict scope boundaries:

### Strictly IN-SCOPE (Phase 1 & 2 Turnkey Build)
- Custom responsive public website (Django SSR + Tailwind)
- Separation of Research Advisory and Academy verticals
- Mandatory SEBI disclosures, Investor Charter, and Grievance Redressal Matrix
- Free Learning Hub (articles, market concept glossary)
- Public Closed Calls performance track record table with disclaimers
- Lead capture and user registration system
- White-labeled client portal on dedicated subdomain
- Role-based gatekeeping (Anonymous, Free User, Active Paid Subscriber)
- Research recommendation feed with full lifecycle status fields
- Dynamic server-side PDF watermarking (Client Name, PAN, Time, IP)
- Protected document streaming (direct downloads blocked)
- SEBI Regulation 25 immutable audit trail with SHA-256 hashes
- Razorpay payment gateway integration (Quarterly & Annual plans)
- Cryptographic webhook state machine with instant automated provisioning
- Automated PDF tax invoice generation and billing history
- Subscriber support and grievance ticketing system
- Gated Academy study material distribution (downloadable course PDFs/PPTs)
- Self-service admin panel with client export to Excel/CSV
- Trademark availability search & filing application assistance
- Production VPS deployment, SSL, security hardening, and admin training

### Strictly DEFERRED (Phase 3 "Grow" Post-Launch)
- **Native Mobile Apps (Android & iOS):** Explicitly deferred to Phase 3 in client briefing slide 7. The web portal is fully mobile-responsive (PWA-ready) for phone browsers.
- **100-Hour Video LMS & Streaming Platform:** Hosting, transcoding, and streaming 100 hours of video courses belongs in Phase 3. Initial release provides syllabus marketing and downloadable student study materials.
- **UPI AutoPay / Recurring e-Mandates:** Requires specialized banking aggregator approvals for SEBI RAs. Launch uses fixed-term one-time payments with automated renewal reminder workflows.
- **Third-Party API Fees:** VPS hosting server, domain purchase, SMS gateway credits, and DigiLocker/e-Sign per-transaction costs are billed at actuals as defined in the proposal.

---

## 6. Pre-Flight Developer Checklist (Before Writing Any Feature)

Before touching feature code, verify every item below:

- [ ] **Virtual Environment Active:** Using `Kalpesh_venv` with Python 3.12+ (or active venv).
- [ ] **Dependencies Frozen:** `requirements.txt` contains pinned versions (`django==5.1.2`, `psycopg[binary]`, `pillow`, `reportlab`, `pypdf`, `python-dotenv`).
- [ ] **Project Scaffolding Clean:** Django initialized with `config .` (no nested project folder).
- [ ] **Custom User Configured First:** `apps.accounts.CustomUser` defined with PAN, phone, and KYC status, set as `AUTH_USER_MODEL`, and initial migrations executed.
- [ ] **Protected Media Segregated:** `/secure_reports/` directory located completely outside static/public web root.
- [ ] **Design Tokens Set:** Global templates configured with **Navy (`#0F172A`)** and **Gold (`#D97706`)**.
- [ ] **Git Commits Structured:** Conventional commit messages (`feat:`, `fix:`, `docs:`, `compliance:`), working on feature branches with protected `main`.
