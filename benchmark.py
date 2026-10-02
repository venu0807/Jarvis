import time
from collections import deque

job_data = [{"jk": f"job_{i}", "title": "Test Job"} for i in range(100000)]
daily_limit = 100000
applied = 0

def benchmark_list_pop0():
    queue = job_data.copy()
    start = time.time()
    count = 0
    while queue and count < daily_limit:
        jd = queue.pop(0)
        if count % 100 == 0 and count < 50000:
            queue.append({"jk": f"sim_{count}", "title": "Sim Job"})
        count += 1
    return time.time() - start

def benchmark_deque_popleft():
    queue = deque(job_data)
    start = time.time()
    count = 0
    while queue and count < daily_limit:
        jd = queue.popleft()
        if count % 100 == 0 and count < 50000:
            queue.append({"jk": f"sim_{count}", "title": "Sim Job"})
        count += 1
    return time.time() - start

b1 = benchmark_list_pop0()
b2 = benchmark_deque_popleft()

print(f"List pop(0) baseline: {b1:.4f} seconds")
print(f"Deque popleft time: {b2:.4f} seconds")
print(f"Improvement: {b1/b2:.2f}x faster")
