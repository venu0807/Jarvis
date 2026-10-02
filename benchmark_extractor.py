import sys
from pathlib import Path
import timeit
import re

sys.path.insert(0, str(Path("automations/linkedin-outreach").resolve()))
import extractor

# Let's write a function that simulates the loop
def with_inline():
    for _ in range(10000):
        re.match(r"[^@]+@[^@]+\.[a-zA-Z]{2,}$", "test@example.com")

compiled_re = re.compile(r"[^@]+@[^@]+\.[a-zA-Z]{2,}$")
def with_compiled():
    for _ in range(10000):
        compiled_re.match("test@example.com")

if __name__ == "__main__":
    t1 = timeit.timeit("with_inline()", globals=globals(), number=100)
    t2 = timeit.timeit("with_compiled()", globals=globals(), number=100)
    print(f"Inline compilation time: {t1:.4f} seconds")
    print(f"Pre-compiled time: {t2:.4f} seconds")
    print(f"Improvement: {(t1 - t2) / t1 * 100:.2f}%")
