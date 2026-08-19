# Method 2: implicit concatenation - written directly
result2 = f"hello " "\n" "world"
print('Method 2:', repr(result2))

# Method 3: using + concatenation
result3 = f"hello " + "\n" + f"world"
print('Method 3:', repr(result3))

# Method 4: NL variable
NL = '\n'
result4 = f'hello {NL} world'
print('Method 4:', repr(result4))