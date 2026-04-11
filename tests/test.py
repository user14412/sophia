script = "abcdef(g)hgc"


def _remove_parentheses(script: str) -> str:
    """去掉括号中的内容"""
    result = []
    skip = 0
    for char in script:
        if char in '({（':
            skip += 1
        elif char in ')}）':
            skip -= 1
        elif skip == 0:
            result.append(char)
    return ''.join(result)

print(_remove_parentheses(script))