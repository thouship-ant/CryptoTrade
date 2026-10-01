import re


def remove_tail_dot_zeros(a):
    tail_dot_rgx = re.compile(r'(?:(\.)|(\.\d*?[1-9]\d*?))0+(?=\b|[^0-9])')
    return tail_dot_rgx.sub(r'\2', a)
