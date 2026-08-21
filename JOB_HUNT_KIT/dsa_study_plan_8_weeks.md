# 8-Week DSA + System Design Study Plan

> **For**: Full Stack AI Engineer roles, India, entry-level (0-1 years)
> **Time**: 30-45 min/day + 1 hour weekends for mocks
> **Total**: 8 weeks → first offer target
> **Resource**: NeetCode 150 (https://neetcode.io/practice)

---

## How To Use This

1. **Daily (Mon-Fri, 30-45 min)**:
   - 5 min: review yesterday's problem, recall the pattern
   - 25 min: solve today's new problem
   - 5-10 min: write down the pattern/insight in notebook (NOT the code)
   - If stuck > 15 min: read the editorial, then implement from scratch

2. **Weekend (Sat, 60 min)**:
   - 30 min: review the week's 5 problems, retry the ones you didn't solve optimally
   - 30 min: 1 mock interview (Pramp or peer)

3. **Spaced Repetition**:
   - Day 3: re-solve yesterday's problem without looking
   - Day 7: re-solve Monday's problem
   - Day 14: re-solve the previous week's hardest problem

4. **Tracking**: Log every problem in the DSA Progress tab of your Google Sheet tracker.

---

## Phase 1: Foundations (Weeks 1–2)

**Goal**: Master Arrays, Strings, Hashing, Two Pointers, Sliding Window — the 5 topics that appear in 80% of fresher interviews.

### Week 1

| Day | Topic | Problem | Difficulty | Time | Pattern |
|---|---|---|---|---|---|
| 1 (Mon) | Arrays & Hashing | Two Sum | Easy | 15 min | HashMap for complement lookup |
| 1 | Arrays & Hashing | Best Time to Buy and Sell Stock | Easy | 15 min | Track min-so-far, max profit |
| 2 (Tue) | Arrays & Hashing | Contains Duplicate | Easy | 10 min | HashSet, early exit |
| 2 | Arrays & Hashing | Product of Array Except Self | Medium | 25 min | Prefix × suffix products |
| 3 (Wed) | Arrays & Hashing | Valid Anagram | Easy | 10 min | Char count array, 26 letters |
| 3 | Arrays & Hashing | Group Anagrams | Medium | 25 min | Sorted string as key, list of values |
| 4 (Thu) | Two Pointers | Valid Palindrome | Easy | 10 min | Two pointers, skip non-alphanumeric |
| 4 | Two Pointers | Two Sum II (sorted array) | Medium | 20 min | Two pointers, move based on sum |
| 5 (Fri) | Two Pointers | 3Sum | Medium | 30 min | Sort + skip duplicates, fix one + two-sum |
| Sat | Review | Retry 3Sum, Group Anagrams | — | 30 min | Focus on edge cases |
| Sun | Mock | Pramp or peer — easy problem + behavioral | — | 60 min | Get used to talking through problems |

### Week 2

| Day | Topic | Problem | Difficulty | Time | Pattern |
|---|---|---|---|---|---|
| 8 (Mon) | Sliding Window | Best Time to Buy and Sell Stock (cooldown) | Medium | 25 min | State machine, max profit with cooldown |
| 8 | Sliding Window | Longest Substring Without Repeating | Medium | 25 min | HashSet + sliding window |
| 9 (Tue) | Sliding Window | Longest Repeating Character Replacement | Medium | 25 min | Sliding window with count of most frequent |
| 9 | Sliding Window | Minimum Window Substring | Hard | 35 min | Two hash maps, expand + contract |
| 10 (Wed) | Stack | Valid Parentheses | Easy | 15 min | Stack of open brackets, match on close |
| 10 | Stack | Min Stack | Medium | 25 min | Two stacks, min-so-far tracking |
| 11 (Thu) | Stack | Daily Temperatures | Medium | 25 min | Monotonic stack, indices |
| 11 | Stack | Largest Rectangle in Histogram | Hard | 40 min | Monotonic stack with width tracking |
| 12 (Fri) | Strings | Encode and Decode Strings | Medium | 25 min | Length-prefix encoding |
| Sat | Review | Retry Daily Temperatures, Min Window Substring | — | 30 min | Get these two solid |
| Sun | Mock | Pramp or peer — medium problem + system design intro | — | 60 min | Focus on explaining approach |

### Phase 1 Self-Check (end of Week 2)

- [ ] Can solve any 2-pointer or sliding-window problem in <25 min
- [ ] Understands hash map patterns deeply
- [ ] Comfortable with stack-based monotonic patterns
- [ ] Solved at least 1 problem/day, 70%+ optimal

If you're not 70%+ optimal, spend 1 more week on foundations before moving on.

---

## Phase 2: Trees + Graphs Basics (Weeks 3–4)

**Goal**: BFS, DFS, BST operations, basic graph traversal.

### Week 3

| Day | Topic | Problem | Difficulty | Time | Pattern |
|---|---|---|---|---|---|
| 15 (Mon) | Binary Tree BFS | Binary Tree Level Order Traversal | Medium | 20 min | BFS with queue, level size tracking |
| 15 | Binary Tree BFS | Maximum Depth of Binary Tree | Easy | 10 min | BFS or DFS, count levels |
| 16 (Tue) | Binary Tree DFS | Invert Binary Tree | Easy | 15 min | DFS, swap children |
| 16 | Binary Tree DFS | Same Tree | Easy | 15 min | DFS, compare node by node |
| 17 (Wed) | Binary Tree DFS | Subtree of Another Tree | Easy | 20 min | DFS, check at each node |
| 17 | Binary Tree DFS | Lowest Common Ancestor of BST | Medium | 25 min | Use BST property, recurse |
| 18 (Thu) | BST | Validate BST | Medium | 25 min | DFS with min/max bounds |
| 18 | BST | Kth Smallest in BST | Medium | 25 min | Inorder traversal |
| 19 (Fri) | Graph BFS | Number of Islands | Medium | 25 min | BFS/DFS on grid, mark visited |
| Sat | Review | Retry Validate BST, Number of Islands | — | 30 min | Solidify DFS patterns |
| Sun | Mock | Pramp — medium tree/graph problem | — | 60 min | Focus on recursion clarity |

### Week 4

| Day | Topic | Problem | Difficulty | Time | Pattern |
|---|---|---|---|---|---|
| 22 (Mon) | Graph DFS | Clone Graph | Medium | 30 min | DFS with HashMap of cloned nodes |
| 22 | Graph DFS | Pacific Atlantic Water Flow | Medium | 35 min | Reverse BFS from borders |
| 23 (Tue) | Graph BFS | Rotting Oranges | Medium | 25 min | Multi-source BFS, time-step |
| 23 | Graph BFS | Word Ladder | Hard | 40 min | BFS on word graph, build neighbors |
| 24 (Wed) | Heap | Kth Largest Element | Medium | 20 min | Min-heap of size k |
| 24 | Heap | Top K Frequent Elements | Medium | 25 min | Heap or bucket sort |
| 25 (Thu) | Heap | Find Median from Data Stream | Hard | 40 min | Two heaps, balance sizes |
| 25 | Heap | Task Scheduler | Medium | 30 min | Max-heap + idle slots |
| 26 (Fri) | Linked List | Reverse Linked List | Easy | 15 min | Iterative, three pointers |
| Sat | Review | Retry Word Ladder, Find Median | — | 30 min | These are hard — be okay with partial solution |
| Sun | Mock | Pramp — graph/heap problem + STAR stories review | — | 60 min | Practice explaining your projects |

### Phase 2 Self-Check (end of Week 4)

- [ ] Can BFS/DFS on trees and grids fluently
- [ ] Understands BST property and uses it
- [ ] Can implement a heap-based solution
- [ ] Comfortable with linked list reversal

---

## Phase 3: DP Intro + Advanced Patterns (Weeks 5–6)

**Goal**: Introduction to dynamic programming + remaining graph algorithms.

### Week 5

| Day | Topic | Problem | Difficulty | Time | Pattern |
|---|---|---|---|---|---|
| 29 (Mon) | 1D DP | Climbing Stairs | Easy | 15 min | Fibonacci, dp[i] = dp[i-1] + dp[i-2] |
| 29 | 1D DP | Min Cost Climbing Stairs | Easy | 20 min | Same, with min instead of sum |
| 30 (Tue) | 1D DP | House Robber | Medium | 25 min | dp[i] = max(dp[i-1], dp[i-2] + nums[i]) |
| 30 | 1D DP | House Robber II | Medium | 30 min | Two cases: skip first OR skip last |
| 31 (Wed) | 1D DP | Longest Palindromic Substring | Medium | 35 min | Expand around center |
| 31 | 1D DP | Palindromic Substrings | Medium | 30 min | Same expansion pattern, count |
| 32 (Thu) | 1D DP | Decode Ways | Medium | 30 min | dp[i] = dp[i-1] + dp[i-2] with edge cases |
| 32 | 1D DP | Coin Change | Medium | 30 min | dp[amount] = min(dp[amount-c]) + 1 |
| 33 (Fri) | 1D DP | Maximum Product Subarray | Medium | 30 min | Track max AND min (negatives) |
| Sat | Review | Retry Coin Change, House Robber II | — | 30 min | Solidify 1D DP |
| Sun | Mock | Pramp — DP problem + system design chat | — | 60 min | Talk through your approach out loud |

### Week 6

| Day | Topic | Problem | Difficulty | Time | Pattern |
|---|---|---|---|---|---|
| 36 (Mon) | 2D DP | Unique Paths | Medium | 25 min | dp[i][j] = dp[i-1][j] + dp[i][j-1] |
| 36 | 2D DP | Longest Common Subsequence | Medium | 35 min | dp[i][j] based on char match |
| 37 (Tue) | 2D DP | Edit Distance | Medium | 35 min | Levenshtein distance, insert/delete/replace |
| 37 | 2D DP | Longest Increasing Subsequence | Medium | 30 min | Patience sorting OR dp with binary search |
| 38 (Wed) | Backtracking | Subsets | Medium | 25 min | Include/exclude recursion |
| 38 | Backtracking | Combination Sum | Medium | 30 min | DFS with sum tracking |
| 39 (Thu) | Backtracking | Word Search | Medium | 30 min | DFS grid, mark visited |
| 39 | Backtracking | Palindrome Partitioning | Medium | 35 min | DFS with palindrome check |
| 40 (Fri) | Greedy | Jump Game | Medium | 20 min | Track reachable farthest |
| Sat | Review | Retry Edit Distance, Word Search | — | 30 min | Hard ones — okay if slow |
| Sun | Mock | Pramp — DP or backtracking | — | 60 min | Focus on explaining complexity |

### Phase 3 Self-Check (end of Week 6)

- [ ] Can identify when to use DP (overlapping subproblems)
- [ ] Can implement 1D DP from a clean slate
- [ ] Understands 2D DP table construction
- [ ] Comfortable with backtracking template

---

## Phase 4: System Design + Polish (Weeks 7–8)

**Goal**: System design basics + targeted topic gaps + final mocks.

### Week 7 — System Design Foundations

| Day | Topic | Activity | Time |
|---|---|---|---|
| 43 (Mon) | System Design Reading | Alex Xu Vol 1 Chapter 1 (Scale from 0 to millions) | 30 min |
| 44 (Tue) | System Design | Alex Xu Ch 2 (Back-of-envelope estimation) | 30 min |
| 45 (Wed) | System Design | Alex Xu Ch 3 (Database, cache, CDN) | 30 min |
| 46 (Thu) | System Design | Alex Xu Ch 5-6 (Message queue, search) | 30 min |
| 47 (Fri) | System Design Practice | "Design URL Shortener" — 30 min design + 15 min watch example | 45 min |
| Sat | Mock + Review | Pramp mock + review past failures | 90 min |
| Sun | Project Polish | Walk through JARVIS architecture — be able to whiteboard it | 60 min |

### Week 8 — Interview Polish

| Day | Topic | Activity | Time |
|---|---|---|---|
| 50 (Mon) | System Design Practice | "Design Rate Limiter" | 45 min |
| 51 (Tue) | System Design Practice | "Design Chat App" (WhatsApp-like) | 45 min |
| 52 (Wed) | System Design Practice | "Design Notification System" | 45 min |
| 53 (Thu) | AI-Specific Design | "Design a RAG Chatbot" — think through retrieval + LLM orchestration | 60 min |
| 54 (Fri) | STAR Stories | Finalize 3 strong STAR stories + rehearse them aloud | 45 min |
| Sat | Mock + Review | 2 Pramp mocks: 1 system design, 1 coding | 120 min |
| Sun | Final Prep | Quick review of all weak topics, sleep early | 30 min |

---

## 5 STAR Stories to Prepare

Use this template for each:

**Situation**: Where were you, what was the context? (1 sentence)
**Task**: What needed to be done, by whom, by when? (1 sentence)
**Action**: What specifically did YOU do? (2-3 sentences with details)
**Result**: Quantified outcome — what changed? (1 sentence with metric)

### Story 1: "Tell me about a complex system you built"
**Suggested**: JARVIS — describe the architecture, why you built it, what it does.

### Story 2: "Tell me about a time you had to learn something quickly"
**Suggested**: Ollama/local LLM stack — you had to learn it in 2 weeks for a project.

### Story 3: "Tell me about a time you debugged a hard problem"
**Suggested**: The Prometheus + Grafana observability layer — you had to debug why scraper failures were spiking.

### Story 4: "Tell me about a time you worked in a team"
**Suggested**: Wipro group project, OR a college team project.

### Story 5: "Tell me about a time you failed"
**Suggested**: A college project that didn't work out, what you learned.

---

## System Design Lite — Venu-Specific

For freshers at Indian startups, system design is usually:
- "How would you build X?" — answer in 10-15 min, focused on schema + APIs + one scaling trick
- NOT the FAANG "design Twitter at scale" pressure

### Format for System Design Answers (use this every time)

1. **Clarify** (1 min): "Is this for X users? Real-time or async? What's the read:write ratio?"
2. **High-level** (2 min): User → API → DB → Response. Draw the box diagram.
3. **Data model** (2 min): What tables, what fields, what indexes.
4. **APIs** (2 min): 2-3 main endpoints, request/response shapes.
5. **One scaling trick** (3 min): Pick ONE: caching, queue, CDN, sharding, replicas.
6. **Trade-offs** (2 min): "We could X but it would Y, so I picked Z because..."

### The 4 Canonical Problems (Week 7-8)

1. **URL Shortener**: hash → DB, with cache layer for hot URLs
2. **Rate Limiter**: token bucket or sliding window, Redis-backed
3. **Chat App**: WebSocket connection, message queue, last-N messages cache
4. **Notification System**: queue-based fanout, user preferences, rate limiting

### 1 AI-Specific Problem: RAG Chatbot

**Question**: "How would you build a RAG chatbot for our docs?"

**Your answer template**:
1. User asks question
2. Embed the question (using a model like nomic-embed)
3. Search vector DB (Pinecone/Weaviate) for top-k relevant chunks
4. Pass chunks + question to LLM as context
5. LLM generates grounded answer
6. Stream response back to user

**Scaling considerations**:
- Cache frequent questions
- Pre-compute embeddings for new docs (background job)
- Use smaller LLM for first-pass filtering, larger LLM for generation

---

## Topic Priority Matrix (for last-minute review)

| Topic | Frequency in Fresher Interviews | Your Time Budget |
|---|---|---|
| Arrays/Hashing | Very High (60%) | 1 week |
| Two Pointers | High (40%) | 2 days |
| Sliding Window | High (35%) | 3 days |
| Stack | Medium (25%) | 3 days |
| Trees (BFS/DFS) | Very High (50%) | 1.5 weeks |
| Graphs (BFS/DFS) | Medium (30%) | 1 week |
| Heap | Low (15%) | 2 days |
| Linked List | Medium (25%) | 2 days |
| 1D DP | Medium-High (35%) | 1 week |
| 2D DP | Medium (25%) | 4 days |
| Backtracking | Medium (25%) | 4 days |
| Greedy | Low-Medium (15%) | 2 days |
| Bit Manipulation | Low (5%) | skip for now |
| Trie | Low (5%) | skip for now |
| Union Find | Low (5%) | skip for now |

---

## Daily Routine Template (Copy this for each day)

```
[Date] - [Day X of plan]
[Topic] - [Problem name]
Time spent: [X] min
Solved optimally: Y / N
Key pattern/insight:
  - 
Edge cases I missed:
  - 
What I'd review tomorrow:
  - 
```

---

## Resources

- **NeetCode 150**: https://neetcode.io/practice (primary)
- **NeetCode YouTube**: https://youtube.com/@NeetCode (video explanations)
- **Alex Xu System Design Vol 1**: https://bytebytego.com (book)
- **Pramp**: https://pramp.com (free mock interviews with peers)
- **Big O Cheat Sheet**: https://www.bigocheatsheet.com

## When You're Stuck

1. Read problem 2x — twice is usually enough to clarify
2. Try 1 example manually, watch your thought process
3. If 5 min no idea → read problem hints (LeetCode has them)
4. If 10 min no idea → read editorial, but **don't read code**
5. If 15 min no idea → read code, understand it, then close tab and re-implement from scratch
6. NEVER just submit code you don't understand

## Final Note

8 weeks × 5 problems/week = 40 problems + reviews + system design. That's NOT a lot. The goal isn't to "solve 150 problems". The goal is to internalize 15-20 deep patterns so you can recognize them in unfamiliar problems.

If you can recognize and apply:
- Two pointers
- Sliding window
- HashMap for O(1) lookup
- BFS/DFS on trees and grids
- 1D DP for sequences
- Backtracking for combinations

...you'll pass 80%+ of fresher interviews.
