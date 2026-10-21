#!/usr/bin/env python3
"""Reject common credential formats in staged additions without printing values."""
import re
import subprocess
import sys

patterns = [
    r"AKIA[0-9A-Z]{16}",
    r"gh[pousr]_[A-Za-z0-9]{30,}",
    r"sk_(?:live|test)_[A-Za-z0-9]{20,}",
    r"-----BEGIN(?: [A-Z]+)? PRIVATE KEY-----",
    r"(?:https?|mongodb(?:\+srv)?|postgres(?:ql)?)://[^\s/:]+:[^\s@]+@",
]
diff = subprocess.check_output(
    ["git", "diff", "--cached", "--no-ext-diff", "--unified=0", "--diff-filter=ACMR"], text=True
)
added = "\n".join(line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
if any(re.search(pattern, added) for pattern in patterns):
    print("Possible credential in staged additions. Remove it before committing.", file=sys.stderr)
    sys.exit(1)
print("Staged secret scan passed.")
