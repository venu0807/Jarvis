import time
from collections import deque

def test_list_pop(n):
    q = list(range(n))
    start = time.time()
    while q:
        q.pop(0)
    return time.time() - start

def test_deque_popleft(n):
    q = deque(range(n))
    start = time.time()
    while q:
        q.popleft()
    return time.time() - start

def test_deque_pop(n):
    q = deque(range(n))
    start = time.time()
    while q:
        q.pop()
    return time.time() - start

print(f"List pop(0): {test_list_pop(100000):.6f}s")
print(f"Deque popleft: {test_deque_popleft(100000):.6f}s")
print(f"Deque pop: {test_deque_pop(100000):.6f}s")
