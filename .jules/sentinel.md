## 2025-05-15 - Removed Remote Code Execution (RCE) via `eval(metadata)`
**Vulnerability:** Untrusted metadata retrieved from the database was being processed using Python's `eval()`. This allowed for arbitrary code execution if a user could inject malicious metadata (e.g., via a document addition).
**Learning:** Legacy data was stored using `str(dict)`, which tempted the use of `eval()` for easy parsing.
**Prevention:** Always use `json.loads()` for deserialization. If legacy support for Python literal strings is required, use `ast.literal_eval()`, which is safe as it only evaluates literals.
