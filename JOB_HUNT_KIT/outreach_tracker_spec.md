# Job Hunt Tracker — Google Sheets Spec

> **How to use**: Create a new Google Sheet. Create 7 tabs (6 trackers + 1 Dashboard). Copy the column headers and sample rows below. Add the formulas in the Dashboard tab. Set up conditional formatting per the specs.

---

## Tab 1: Outreach Tracker

### Columns (A–N)

| Col | Header | Type | Notes |
|---|---|---|---|
| A | Date | Date | When you sent |
| B | Company | Text | e.g., "Sarvam AI" |
| C | Tier | Dropdown | T1 / T2 / T3 |
| D | Person Name | Text | First + last, e.g., "Pratyusha Sharma" |
| E | Role/Title at Company | Text | e.g., "Founder & CEO" |
| F | Channel | Dropdown | LinkedIn DM / Email / Cold DM / Recruiter Reply / Referral / Job Portal |
| G | Template Used | Dropdown | T1 / T2 / T3 / T4 / T5 |
| H | JD Link | URL | Optional, if responding to a JD |
| I | Personalization Note | Text | One sentence: what specific thing they did |
| J | Status | Dropdown | Sent / Replied / No Response / Bounced / Phone Screen Scheduled / Rejected / Hired |
| K | Follow-up Date | Date | When to send follow-up |
| L | Notes | Text | Anything else |

### Sample Row

```
2026-08-22 | Sarvam AI | T1 | Pratyusha Sharma | Founder & CEO | LinkedIn DM | T1 | https://sarvam.ai/careers/fullstack-ai | Mentioned their new Llama-3 fine-tuning blog | Sent | 2026-08-29 | Sent 9:02 AM, personalized to launch post
```

### Conditional Formatting

| Range | Condition | Color |
|---|---|---|
| J2:J1000 | Text = "Hired" | Green background, white bold text |
| J2:J1000 | Text = "Rejected" | Red background |
| J2:J1000 | Text = "Bounced" | Yellow background |
| J2:J1000 | Text = "Phone Screen Scheduled" | Blue background |
| K2:K1000 | Date is in past AND J is "Sent" | Red background (overdue follow-up) |

### Data Validation Dropdowns

- **C2:C1000** — `T1,T2,T3`
- **F2:F1000** — `LinkedIn DM,Email,Cold DM,Recruiter Reply,Referral,Job Portal`
- **G2:G1000** — `T1,T2,T3,T4,T5`
- **J2:J1000** — `Sent,Replied,No Response,Bounced,Phone Screen Scheduled,Rejected,Hired`

---

## Tab 2: Applications Tracker

### Columns (A–K)

| Col | Header | Type | Notes |
|---|---|---|---|
| A | Date Applied | Date | |
| B | Company | Text | |
| C | Role Title | Text | |
| D | Job Portal | Dropdown | Naukri / Internshala / Indeed / Foundit / LinkedIn / AngelList / Company Site / Referral |
| E | Job Link | URL | |
| F | Resume Variant | Dropdown | FullStackAI / AI-Engineer / Backend / DataAnalyst |
| G | Cover Letter | Text | Filename or "Yes/No" |
| H | Status | Dropdown | Applied / Under Review / Recruiter Screen / Tech Interview / Final / Offer / Rejected / Withdrew |
| I | Method | Dropdown | JARVIS Auto-Applier / Manual / Referral |
| J | Notes | Text | |
| K | Last Updated | Date | Auto-set when status changes |

### Sample Row

```
2026-08-22 | Sarvam AI | Full Stack AI Engineer | LinkedIn | https://linkedin.com/jobs/... | FullStackAI | sarvam_fullstack.docx | Applied | JARVIS Auto-Applier | Auto-applied 4:15 AM, tailored to LLM RAG requirements | 2026-08-22
```

### Conditional Formatting

| Range | Condition | Color |
|---|---|---|
| H2:H1000 | Text = "Offer" | Green |
| H2:H1000 | Text = "Rejected" | Red |
| H2:H1000 | Text = "Tech Interview" or "Final" | Blue |
| H2:H1000 | Text = "Recruiter Screen" | Yellow |

---

## Tab 3: Interview Pipeline

### Columns (A–J)

| Col | Header | Type | Notes |
|---|---|---|---|
| A | Date | Date | |
| B | Company | Text | |
| C | Round | Dropdown | Recruiter Screen / Phone Coding / Live Coding / System Design / Project Walkthrough / Hiring Manager / Behavioral / Final |
| D | Interviewer | Text | Name + LinkedIn URL |
| E | Questions Asked | Text | Comma-separated, brief |
| F | Answers Quality (1-5) | Number | Self-assessment |
| G | Topics Hit | Text | Comma-separated tags: e.g., "LLM, RAG, scaling, observability" |
| H | Result | Dropdown | Pass / Fail / Pending / Withdrew |
| I | Feedback Received | Text | |
| J | Next Round Prep Notes | Text | |

### Sample Row

```
2026-09-01 | Sarvam AI | Recruiter Screen | Anjali Rao (linkedin.com/in/anjali-rao) | Walk me through JARVIS, why Sarvam | 4 | LLM, RAG, scaling, observability | Pass | Strong technical depth, move to tech round | Prep: review their LLM evaluation pipeline, brush up on RAG patterns
```

### Pivot Table Spec (Tab 3 — Summary View)

Create a new sheet "Interview Topics Summary":

1. Select all data on Tab 3 columns G:H
2. Insert → Pivot Table
3. Rows: Topics Hit (split by comma into multiple rows using SPLIT+FLATTEN or in column transformation)
4. Values: COUNT of Result
5. Filter: Result = "Pass" OR "Pending"

**Output**: Bar chart of "Top 10 topics asked in interviews I've passed" — drives your study focus.

---

## Tab 4: DSA Progress

### Columns (A–I)

| Col | Header | Type | Notes |
|---|---|---|---|
| A | Date | Date | |
| B | Problem Name | Text | e.g., "Two Sum" |
| C | Platform | Dropdown | NeetCode / LeetCode / HackerRank |
| D | Topic | Dropdown | Array / Hashing / Two Pointers / Sliding Window / Stack / Linked List / Tree / BST / Heap / Graph / BFS / DFS / DP / Backtracking / Greedy / Bit Manipulation / Trie / Union Find |
| E | Difficulty | Dropdown | Easy / Medium / Hard |
| F | Time Taken (min) | Number | |
| G | Optimal Solution | Dropdown | Yes / No |
| H | Pattern Tag | Text | e.g., "two-sum-hashmap", "sliding-window-fixed" |
| I | Notes | Text | Key insight, edge case, etc. |

### Sample Row

```
2026-08-22 | Two Sum | NeetCode | Hashing | Easy | 8 | Yes | two-sum-hashmap | Edge case: empty array, single element, duplicate values
```

### Conditional Formatting

| Range | Condition | Color |
|---|---|---|
| E2:E1000 | Text = "Easy" | Light green |
| E2:E1000 | Text = "Medium" | Yellow |
| E2:E1000 | Text = "Hard" | Red |
| G2:G1000 | Text = "No" | Orange (needs revisit) |

### Spaced Repetition Sheet (linked from Tab 4)

Create a new sheet "DSA Review Queue":

| Col | Header | Notes |
|---|---|---|
| A | Problem Name | Pull from Tab 4 |
| B | First Solved | Date |
| C | Review 1 (Day 3) | Date |
| D | Review 2 (Day 7) | Date |
| E | Review 3 (Day 14) | Date |
| F | Status | Mastered / Needs Practice |

**Setup**: Use formulas to auto-populate review dates:
- C2: `=B2 + 3`
- D2: `=B2 + 7`
- E2: `=B2 + 14`

Daily routine: solve today's new problem + check Review Queue for problems due today.

---

## Tab 5: Daily Routine Checklist

### Columns (A–H)

| Col | Header | Type |
|---|---|---|
| A | Date | Date |
| B | 5 Apps Sent? | Checkbox |
| C | 5 Cold DMs Sent? | Checkbox |
| D | DSA 30 min? | Checkbox |
| E | LinkedIn 15 min? | Checkbox |
| F | Friday Follow-ups? | Checkbox (only relevant Fri) |
| G | Mood/Energy (1-5) | Number |
| H | Notes | Text |

### Sample Row

```
2026-08-22 | TRUE | TRUE | TRUE | TRUE | FALSE | 4 | Strong day, got 1 reply from Sarvam AI
```

### Conditional Formatting

- **B–F columns**: TRUE = green, FALSE = red
- **G column**: 1-2 = red, 3 = yellow, 4-5 = green
- **Highlight entire row** if 4/5 items TRUE = green, 3/5 = yellow, ≤2/5 = red

---

## Tab 6: Wins & Lessons

### Columns (A–D)

| Col | Header | Type |
|---|---|---|
| A | Date | Date |
| B | Type | Dropdown: Win / Lesson / Rejection Insight |
| C | Description | Text |
| D | Strategy Adjustment | Text |

### Sample Rows

```
2026-08-22 | Win | Got first recruiter screen from Sarvam AI | Template T1 (founder cold DM) works — keep sending 3/week
2026-08-24 | Rejection Insight | Razorpay rejected after tech round — said "weak on system design" | Add 1 system design problem/week to DSA routine; do 2 mock interviews
2026-08-25 | Lesson | Sending 7 cold DMs/day felt like spam and got 0 replies | Drop to 5/day, but make each more personalized
```

---

## Tab 7: Dashboard (Auto-Calculated)

### Layout — single tab, top-to-bottom

```
Row 1: WEEKLY METRICS (last 7 days)
Row 3:  Outreach sent        = formula
Row 4:  Apps submitted       = formula
Row 5:  Recruiter screens    = formula
Row 6:  Tech interviews      = formula
Row 7:  DSA problems solved  = formula

Row 9:  CONVERSION RATES (last 30 days)
Row 11: Outreach → Reply rate          = formula
Row 12: Apps → Recruiter Screen rate   = formula
Row 13: Screen → Tech Interview rate   = formula
Row 14: Tech Interview → Offer rate    = formula

Row 16: DAILY ROUTINE (last 7 days)
Row 18: Days hitting 4/5 routine items  = formula
Row 19: Current streak (consecutive)    = formula
Row 20: DSA problems by topic (chart)   = formula

Row 22: PIPELINE HEALTH
Row 24: Apps in progress        = formula
Row 25: Interviews this week    = formula
Row 26: Follow-ups due today    = formula
```

### Formulas (paste into Tab 7)

Assuming:
- Tab 1 = "Outreach"
- Tab 2 = "Applications"
- Tab 3 = "Interviews"
- Tab 4 = "DSA"
- Tab 5 = "Routine"
- Today's cell = `TODAY()`

#### Weekly Metrics

```
B3: =COUNTIFS(Outreach!A:A, ">="&(TODAY()-7), Outreach!A:A, "<="&TODAY())
B4: =COUNTIFS(Applications!A:A, ">="&(TODAY()-7), Applications!A:A, "<="&TODAY())
B5: =COUNTIFS(Applications!H:H, "Recruiter Screen", Applications!K:K, ">="&(TODAY()-7))
B6: =COUNTIFS(Interviews!A:A, ">="&(TODAY()-7), Interviews!A:A, "<="&TODAY())
B7: =COUNTIFS(DSA!A:A, ">="&(TODAY()-7), DSA!A:A, "<="&TODAY())
```

#### Conversion Rates (last 30 days)

```
B11: =COUNTIFS(Outreach!J:J, "Replied", Outreach!A:A, ">="&(TODAY()-30)) / COUNTIFS(Outreach!A:A, ">="&(TODAY()-30))
B12: =COUNTIFS(Applications!H:H, "Recruiter Screen", Applications!K:K, ">="&(TODAY()-30)) / COUNTIFS(Applications!A:A, ">="&(TODAY()-30))
B13: =COUNTIFS(Interviews!H:H, "Pass", Interviews!A:A, ">="&(TODAY()-30)) / COUNTIFS(Interviews!H:H, "<>", "", Interviews!A:A, ">="&(TODAY()-30))
B14: =COUNTIFS(Applications!H:H, "Offer", Applications!K:K, ">="&(TODAY()-30)) / MAX(1, COUNTIFS(Applications!H:H, "Tech Interview", Applications!K:K, ">="&(TODAY()-30)))
```

#### Daily Routine

```
B18: =SUMPRODUCT((Routine!A:A >= TODAY()-7) * ((Routine!B:B="TRUE") + (Routine!C:C="TRUE") + (Routine!D:D="TRUE") + (Routine!E:E="TRUE") + (Routine!F:F="TRUE") >= 4))
B19: Streak — paste this complex formula:
     =IF(B18>0, SUMPRODUCT((Routine!A2:A100 = TODAY())*1) +
        IF(COUNTIFS(Routine!A:A, TODAY()-1, Routine!B:F, "TRUE")>=4, 1, 0) +
        IF(COUNTIFS(Routine!A:A, TODAY()-2, Routine!B:F, "TRUE")>=4, 1, 0) +
        IF(COUNTIFS(Routine!A:A, TODAY()-3, Routine!B:F, "TRUE")>=4, 1, 0) +
        IF(COUNTIFS(Routine!A:A, TODAY()-4, Routine!B:F, "TRUE")>=4, 1, 0) +
        IF(COUNTIFS(Routine!A:A, TODAY()-5, Routine!B:F, "TRUE")>=4, 1, 0) +
        IF(COUNTIFS(Routine!A:A, TODAY()-6, Routine!B:F, "TRUE")>=4, 1, 0), 0)
B20: DSA by topic (last 30 days):
     =QUERY(DSA!D:D, "SELECT D, COUNT(D) WHERE D IS NOT NULL AND A >= date '"&TEXT(TODAY()-30,"yyyy-MM-dd")&"' GROUP BY D ORDER BY COUNT(D) DESC LIMIT 10", 0)
```

#### Pipeline Health

```
B24: =COUNTIF(Applications!H:H, "Applied") + COUNTIF(Applications!H:H, "Under Review")
B25: =COUNTIFS(Interviews!A:A, ">="&(TODAY()-7), Interviews!A:A, "<="&TODAY())
B26: =COUNTIFS(Outreach!K:K, TODAY(), Outreach!J:J, "Sent")
```

### Conditional Formatting on Dashboard

- **B3:B7** — Numbers: green if meeting weekly target (5), red if <50% of target
- **B11:B14** — Percentages: green if improving, red if declining (compare to last week)
- **B18:B19** — Streak: green if ≥7, yellow if 3-6, red if <3

---

## Pivot Tables (Build These Manually)

### Pivot 1: "Which templates get the most replies?"

1. Source: Tab 1, columns G (Template) + J (Status)
2. Insert → Pivot Table → new sheet "Template Performance"
3. Rows: Template Used (G)
4. Values: COUNT of Status, COUNTIF Status = "Replied"
5. Add a calculated field: Reply Rate = Replies / Total Sent
6. Sort by Reply Rate descending
7. Insert → Chart → Bar chart of Reply Rate by Template

**Insight**: After 30 messages, you'll see which template converts best. Double down on that one.

### Pivot 2: "Which tier has highest callback rate?"

1. Source: Tab 1, columns C (Tier) + J (Status)
2. New sheet "Tier Performance"
3. Rows: Tier
4. Values: COUNT of Status, COUNTIF Status = "Phone Screen Scheduled" or "Replied"
5. Add field: Callback Rate
6. Chart: Bar chart of Callback Rate by Tier

**Insight**: If T1 has 20% callbacks and T3 has 2%, focus more on T1.

### Pivot 3: "DSA topics in interviews"

1. Source: Tab 3, column G (Topics Hit)
2. New sheet "Topic Frequency"
3. Split Topics Hit by comma (use SPLIT + ARRAYFORMULA)
4. Rows: Topic
5. Values: COUNT of Result
6. Filter: Result = "Pass"
7. Chart: Top 10 topics in passed interviews

**Insight**: Drive your DSA study time toward the topics actually asked.

---

## Sample Data Pre-Population (Optional)

Before you go live, add 5 sample rows to each tab so your dashboard formulas work. Use realistic Tier 1 companies:

### Sample Outreach Rows (Tab 1)

| Date | Company | Tier | Person | Title | Channel | Template | Status |
|---|---|---|---|---|---|---|---|
| 2026-08-22 | Sarvam AI | T1 | Pratyusha Sharma | Founder | LinkedIn DM | T1 | Sent |
| 2026-08-22 | Yellow.ai | T1 | Raghu Ravinutala | CEO | LinkedIn DM | T1 | Replied |
| 2026-08-22 | Razorpay | T2 | Harshil Mathur | CEO | Email | T4 | Phone Screen Scheduled |
| 2026-08-23 | Haptik | T1 | Aakrit Vaish | Founder | LinkedIn DM | T1 | No Response |
| 2026-08-23 | Freshworks | T2 | Girish Mathrubootham | Founder | Email | T4 | Replied |

### Sample Application Rows (Tab 2)

| Date | Company | Role | Portal | Resume | Status | Method |
|---|---|---|---|---|---|---|
| 2026-08-22 | Sarvam AI | Full Stack AI Engineer | LinkedIn | FullStackAI | Applied | JARVIS Auto-Applier |
| 2026-08-22 | Yellow.ai | AI Engineer | LinkedIn | AI-Engineer | Recruiter Screen | Manual |
| 2026-08-22 | Razorpay | Backend Engineer | Naukri | Backend | Tech Interview | Referral |
| 2026-08-23 | Haptik | Full Stack AI | Indeed | FullStackAI | Applied | JARVIS Auto-Applier |
| 2026-08-23 | Freshworks | Software Engineer | LinkedIn | FullStackAI | Under Review | Manual |

### Sample DSA Rows (Tab 4)

| Date | Problem | Platform | Topic | Difficulty | Time | Optimal |
|---|---|---|---|---|---|---|
| 2026-08-22 | Two Sum | NeetCode | Hashing | Easy | 8 | Yes |
| 2026-08-22 | Best Time to Buy and Sell Stock | NeetCode | Array | Easy | 12 | Yes |
| 2026-08-23 | Contains Duplicate | NeetCode | Hashing | Easy | 5 | Yes |
| 2026-08-23 | Product of Array Except Self | NeetCode | Array | Medium | 25 | Yes |
| 2026-08-24 | Valid Anagram | NeetCode | Hashing | Easy | 6 | Yes |

---

## Setup Checklist

- [ ] Create new Google Sheet, name it "Venu Job Hunt 2026"
- [ ] Create 7 tabs with the names above
- [ ] Copy column headers into each tab (Row 1)
- [ ] Set up data validation dropdowns
- [ ] Apply conditional formatting rules
- [ ] Copy formulas into Tab 7 (Dashboard)
- [ ] Add 5 sample rows to each tracker tab (so formulas work)
- [ ] Build the 3 pivot tables (or wait until you have 30+ days of data)
- [ ] Pin Dashboard tab to position 1
- [ ] Add a "Today" filter view (Data → Filter views → Save as "Daily View")
- [ ] Set up email reminders: morning (8:30 AM) for routine check, evening (8 PM) for follow-up review

## Time Investment

- Setup: ~45 minutes (one-time)
- Daily use: 5-10 minutes (check off routine items, log outreach)
- Weekly review: 30 minutes (Sunday evening — update Wins & Lessons, check Dashboard)

## Pro Tips

1. **Open the sheet every morning** — first thing, before email
2. **Log as you go** — don't batch at end of day, you'll forget
3. **Use the mobile app** — log outreach DMs from your phone between meetings
4. **Review Wins & Lessons every Sunday** — that's where the meta-learning lives
5. **Don't obsess over perfect data** — a slightly-wrong entry beats a missing entry
6. **The Dashboard is for trend-spotting, not micro-managing** — check it once a week
