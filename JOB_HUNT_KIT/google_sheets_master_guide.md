# Master Job Hunt Tracker — Google Sheets Import Guide

> **Time to set up**: 15 minutes
> **Result**: Single Google Sheet with 4 tabs, auto-formatted, ready for daily use

---

## 📋 Option A: Quick Import (5 minutes)

1. Go to **sheets.google.com** → **Blank spreadsheet**
2. **File → Import → Upload** → Select each CSV → **Replace spreadsheet** for first, **Insert new sheet(s)** for others
3. Rename tabs: `Outreach`, `Applications`, `Daily`, `Companies`
4. Done!

---

## 📋 Option B: Master Template (15 minutes, more powerful)

Create a new Google Sheet with these 4 tabs + formulas:

### Tab 1: `Outreach` (from `tracker_outreach.csv`)

Add these **extra columns** to the right:

| Column | Formula / Purpose |
|---|---|
| `Reply Received` | Checkbox |
| `Reply Date` | Date |
| `Reply Sentiment` | Dropdown: Positive/Neutral/Negative |
| `Next Action` | Text |
| `Days Since Sent` | `=IF(L2="", "", TODAY()-A2)` |
| `Follow-up Due?` | `=IF(AND(L2="", TODAY()>=K2), "⚠️ DUE", "")` |

### Tab 2: `Applications` (from `tracker_applications.csv`)

| Column | Formula / Purpose |
|---|---|
| `Days Since Applied` | `=IF(B2="", "", TODAY()-A2)` |
| `Follow-up Sent?` | Checkbox |
| `Interview Scheduled` | Date |
| `Offer Stage` | Dropdown: None/Phone/Technical/Final/Offer/Rejected |

### Tab 3: `Daily` (from `tracker_daily.csv`)

| Column | Formula / Purpose |
|---|---|
| `Week Number` | `=WEEKNUM(A2)` |
| `DMs Sent` | `=COUNTIFS(C:C,"*DM*",A:A,A2)` (helper) |
| `Emails Sent` | `=COUNTIFS(C:C,"*Email*",A:A,A2)` |
| `Total Time (hrs)` | `=SUMIF(A:A,A2,D:D)/60` |

### Tab 4: `Companies` (from `tracker_companies.csv`)

| Column | Formula / Purpose |
|---|---|
| `Days in Pipeline` | `=IF(B2="", "", TODAY()-E2)` |
| `Stalled?` | `=IF(AND(F2="", TODAY()-E2>14), "⚠️ STALLED", "")` |
| `Priority Score` | `=IF(B2="T1",3,IF(B2="T2",2,1)) * (1+IF(F2="Active",1,0))` |

---

## 📊 Dashboard Tab (Create New Tab: `Dashboard`)

Paste these formulas in row 1:

| Cell | Formula |
|---|---|
| `A1` | `="JOB HUNT DASHBOARD - " & TEXT(TODAY(),"MMM DD, YYYY")` |
| `A3` | `"TOTAL OUTREACH"` |
| `B3` | `=COUNTA(Outreach!A2:A)` |
| `A4` | `"REPLIES RECEIVED"` |
| `B4` | `=COUNTIF(Outreach!M2:M, TRUE)` |
| `A5` | `"REPLY RATE"` |
| `B5` | `=IF(B3=0,0,B4/B3)` → Format as % |
| `A6` | `"INTERVIEWS"` |
| `B6` | `=COUNTIF(Applications!H2:H,"*Interview*")` |
| `A7` | `"OFFERS"` |
| `B7` | `=COUNTIF(Applications!I2:I,"Offer")` |
| `A9` | `"THIS WEEK ACTIVITY"` |
| `B9` | `=SUMIFS(Daily!D:D, Daily!A:A, ">= "&TODAY()-WEEKDAY(TODAY())+2, Daily!A:A, "<="&TODAY()-WEEKDAY(TODAY())+6)` |
| `A10` | `"DMs THIS WEEK"` |
| `B10` | `=COUNTIFS(Outreach!A2:A, ">= "&TODAY()-WEEKDAY(TODAY())+2, Outreach!A2:A, "<="&TODAY()-WEEKDAY(TODAY())+6, Outreach!F2:F, "*DM*")` |
| `A11` | `"Emails THIS WEEK"` |
| `B11` | `=COUNTIFS(Outreach!A2:A, ">= "&TODAY()-WEEKDAY(TODAY())+2, Outreach!A2:A, "<="&TODAY()-WEEKDAY(TODAY())+6, Outreach!F2:F, "*Email*")` |
| `A13` | `"PIPELINE BY TIER"` |
| `B13` | `=QUERY(Companies!A2:F, "SELECT B, COUNT(A) WHERE A IS NOT NULL GROUP BY B LABEL COUNT(A) 'Count'")` |
| `A15` | `"STALLED COMPANIES (>14 days no action)"` |
| `B15` | `=FILTER(Companies!A2:A, Companies!H2:H="⚠️ STALLED")` |

---

## 🎨 Conditional Formatting (Apply After Import)

**Outreach tab:**
- Column M (Reply Received): Green fill when TRUE
- Column N (Follow-up Due?): Red fill when contains "DUE"

**Applications tab:**
- Column H (Interview): Green fill when contains "Interview"
- Column I (Offer Stage): Green when "Offer", Red when "Rejected"

**Companies tab:**
- Column H (Stalled?): Red fill when contains "STALLED"
- Column G (Priority Score): Color scale (Green 3 → Yellow 2 → Red 1)

---

## 🔗 Quick Links for Import

Your CSV files are at:
```
/home/venu/Proposals/Jarvis/JOB_HUNT_KIT/
├── tracker_outreach.csv      (12 cols, 6 rows + header)
├── tracker_applications.csv  (9 cols, 6 rows + header)
├── tracker_daily.csv         (6 cols, 6 rows + header)
├── tracker_companies.csv     (6 cols, 80 rows + header)
```

---

## ✅ Post-Import Checklist

- [ ] All 4 tabs imported
- [ ] Tabs renamed: `Outreach`, `Applications`, `Daily`, `Companies`
- [ ] Dashboard tab created with formulas
- [ ] Conditional formatting applied
- [ ] Column widths adjusted
- [ ] Frozen header row (View → Freeze → 1 row)
- [ ] Filter views created for each tab
- [ ] Shared with yourself (optional: share with accountability partner)

---

## 📱 Mobile-Friendly View

Create a **Filter View** on each tab:
- Outreach: Filter `Status = "Sent"` + `Follow-up Due? = "⚠️ DUE"`
- Companies: Filter `Stalled? = "⚠️ STALLED"`
- Daily: Filter `Date = TODAY()`

Pin these filter views for quick mobile access.