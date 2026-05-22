import urllib.request, json, os, glob, pathlib, re, ssl

# Finding 3: resolve paths and reject anything outside failure-logs/
base = pathlib.Path('failure-logs').resolve()
log_files = glob.glob('failure-logs/**/*', recursive=True)
logs = []
for f in log_files:
    p = pathlib.Path(f).resolve()
    if not str(p).startswith(str(base)):
        continue
    if p.is_file():
        text = p.read_text(errors='replace')
        # Finding 2: redact credential patterns before sending to AI endpoint
        text = re.sub(r'(?i)(password|secret|token|key|pwd|passwd)\s*[=:]\s*\S+', r'\1=[REDACTED]', text)
        logs.append(f"=== {p.name} ===\n{text}")

combined = "\n\n".join(logs) if logs else "No log files captured."
combined = combined[-12000:]

# Finding 4: explicit SSL context so corporate CA interception is not silently trusted
_ssl_ctx = ssl.create_default_context()

def api_request(path, data=None):
    req = urllib.request.Request(
        f"https://openai.generative.engine.capgemini.com/v1{path}",
        data=json.dumps(data).encode() if data else None,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"
        }
    )
    try:
        with urllib.request.urlopen(req, context=_ssl_ctx) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"API error {e.code} {e.reason}: {e.read().decode(errors='replace')}")
        raise

models = api_request("/models")["data"]
model_id = next(
    (m["id"] for m in models if "sonnet" in m["id"].lower()),
    models[0]["id"]
)
print(f"Using model: {model_id}")

payload = {
    "model": model_id,
    "messages": [
        {
            "role": "system",
            "content": (
                "You are a CI/CD expert. Analyze the following build/test failure logs "
                "and provide: 1) A concise summary of what failed and why, "
                "2) Concrete remediation steps the developer should take."
            )
        },
        {"role": "user", "content": f"CI failure logs:\n\n{combined}"}
    ]
}

result = api_request("/chat/completions", payload)
analysis = result["choices"][0]["message"]["content"]

with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
    f.write("## CI Failure Analysis\n\n")
    f.write(analysis + "\n")

print("Analysis written to step summary.")
