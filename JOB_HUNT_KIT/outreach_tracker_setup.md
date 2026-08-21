# Job Hunt Tracker Setup — Google Sheets

> **Time to set up**: 20 minutes
> **Where**: New Google Sheet you create at sheets.google.com

---

## Quick Start (5 minutes)

1. Go to **sheets.google.com**
2. Click **+ Blank** to create new sheet
3. Name it: **Venu Job Hunt Tracker — 2026**
4. Create 5 tabs (right-click tab → Rename):
   - Tab 1: `Outreach`
   - Tab 2: `Applications`
   - Tab 3: `Companies`
   - Tab 4: `Daily Log`
   - Tab 5: `Dashboard`

---

## Tab 1: Outreach (12 columns)

**Paste this header row (A1:L1):**

```
Date | Company | Tier | Person Name | Role/Title | Channel | Template | JD Link | Personalization | Status | Follow-up Date | Notes
```

**Data validation (set up after pasting data):**
- **C2:C1000** → Dropdown: `T1, T2, T3`
- **F2:F1000** → Dropdown: `LinkedIn DM, Email, Cold DM, Recruiter Reply, Referral, Job Portal`
- **G2:G1000** → Dropdown: `T1, T2, T3, T4, T5`
- **J2:J1000** → Dropdown: `Sent, Replied, No Response, Bounced, Phone Screen, Rejected, Hired`

**Conditional formatting:**
- J = "Hired" → Green
- J = "Rejected" → Red
- J = "Phone Screen" → Blue
- K (follow-up date) is past AND J = "Sent" → Red (overdue)

**Sample row (A2):**
```
2026-08-22 | Sarvam AI | T1 | Pratyusha Sharma | Founder & CEO | LinkedIn DM | T1 | https://sarvam.ai/careers | Sovereign LLM launch post | Sent | 2026-08-29 | Sent 9:02 AM
```

**Bulk import option:**
1. Download `tracker_outreach.csv` from this folder
2. In Google Sheets: File → Import → Upload → Select CSV → Replace current sheet
3. Then re-format the dropdowns

---

## Tab 2: Applications (9 columns)

**Paste header row (A1:I1):**

```
Date Applied | Company | Role | Portal | Status | Resume Version | Follow-up | Notes | Salary Range
```

**Data validation:**
- **D2:D1000** → Dropdown: `LinkedIn, Naukri, Internshala, Indeed, Foundit, Company Site, Referral`
- **E2:E1000** → Dropdown: `Drafted, Sent, Viewed, Shortlisted, Interviewing, Offered, Rejected, Ghosted`
- **F2:F1000** → Dropdown: `FullStackAI, AI-Engineer, Backend, DataAnalyst`

**Bulk import:** Use `tracker_applications.csv`

---

## Tab 3: Companies (7 columns)

**Paste header row (A1:G1):**

```
Company | Tier | Status | Reason | Date Added | Next Step | Priority
```

**Data validation:**
- **B2:B1000** → Dropdown: `T1, T2, T3`
- **C2:C1000** → Dropdown: `Active, Watch, Applied, Hired, Rejected`
- **G2:G1000** → Dropdown: `1-High, 2-Medium, 3-Low`

**Bulk import:** Use `tracker_companies.csv` (already has 70+ companies pre-loaded)

---

## Tab 4: Daily Log (6 columns)

**Paste header row (A1:F1):**

```
Date | Time | Activity | Duration (min) | Notes | Energy Level
```

**Data validation:**
- **F2:F1000** → Dropdown: `High, Medium, Low`

**Bulk import:** Use `tracker_daily.csv`

---

## Tab 5: Dashboard (auto-calculate metrics)

**In cell A1, paste these formulas (one per line, with labels):**

```
Outreach Metrics:
=COUNTA(Outreach!A2:A1000)    [Total outreaches sent]

Response Rate:
=COUNTIF(Outreach!J:J,"Replied")/COUNTA(Outreach!A2:A1000)    [As %]

Phone Screens:
=COUNTIF(Outreach!J:J,"Phone Screen")    [Count]

Offers:
=COUNTIF(Outreach!J:J,"Hired")    [Count]

Application Metrics:
=COUNTA(Applications!A2:A1000)    [Total applications]

Interview Rate:
=COUNTIF(Applications!E:E,"Interviewing")/COUNTA(Applications!A2:A1000)    [As %]

Daily Activity (last 7 days):
=COUNTIFS(DailyLog!A:A,">="&(TODAY()-7),DailyLog!A:A,"<="&TODAY())    [Count]
```

---

## Daily Routine (15 min)

**Morning (9 AM):**
- Open Dashboard tab — see metrics
- Check follow-up column in Outreach — any "Sent" with red date = overdue, send follow-up

**Evening (8 PM):**
- Log today's activities in Daily Log
- Update any status changes in Outreach/Applications

---

## Weekly Review (Sunday 10 AM, 30 min)

- Count outreach sent this week (target: 35)
- Count applications submitted (target: 20)
- Review response rate
- Adjust templates if response rate < 5%
- Add new companies to Companies tab

---

## Files in This Folder

| File | Purpose |
|---|---|
| `tracker_outreach.csv` | Bulk import data for Outreach tab |
| `tracker_applications.csv` | Bulk import data for Applications tab |
| `tracker_companies.csv` | Bulk import data for Companies tab (70+ companies) |
| `tracker_daily.csv` | Bulk import data for Daily Log tab |
| `outreach_tracker_setup.md` | This file |

---

## Quick Setup (3 minutes)

1. Create new Google Sheet
2. Create 5 tabs (Outreach, Applications, Companies, Daily Log, Dashboard)
3. File → Import each CSV into its respective tab
4. Set up dropdowns (Data → Data validation)
5. Set up conditional formatting (Format → Conditional formatting)
6. Add formulas to Dashboard tab

**Total: 20 minutes setup, 15 min/day, 30 min/week**
