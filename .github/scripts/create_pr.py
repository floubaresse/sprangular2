import urllib.request, json, os, re, subprocess, tempfile, ssl

branch = os.environ['BRANCH']

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

title   = run("git log -1 --pretty=%s")
commits = run("git log origin/main..HEAD --pretty=format:'%h %s'")
stat    = run("git diff origin/main..HEAD --stat")
diff    = run("git diff origin/main..HEAD -- ':(exclude)*.env' ':(exclude)*.env.*' ':(exclude)*secret*' ':(exclude)*credential*' ':(exclude)*password*'")[:10000]

sonar_url = None
sonar_log_path = os.environ.get('SONAR_LOG_PATH', '')
if sonar_log_path and os.path.exists(sonar_log_path):
    with open(sonar_log_path, 'r', errors='replace') as f:
        sonar_log = f.read()
    m = re.search(r'ANALYSIS SUCCESSFUL, you can find the results at:\s*(\S+)', sonar_log)
    if m:
        sonar_url = m.group(1)

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
        print(f"API error {e.code}: {e.read().decode(errors='replace')}")
        raise

models   = api_request("/models")["data"]
model_id = next((m["id"] for m in models if "sonnet" in m["id"].lower()), models[0]["id"])
print(f"Using model: {model_id}")

sonar_pipeline_status = "SonarQube ✅" if sonar_url else "SonarQube ✅ (no URL found)"
sonar_context = f"\nSonarQube results URL: {sonar_url}" if sonar_url else ""

prompt = f"""You are a senior software engineer writing a pull request description for a code reviewer.

Branch: {branch}
Title: {title}

Commits:
{commits}

Changed files:
{stat}

Diff (truncated to 10 000 chars):
{diff}

Pipeline: Backend ✅  |  Frontend ✅  |  {sonar_pipeline_status}{sonar_context}

Write a professional PR description with exactly these 7 sections in GitHub Markdown.
Be concise. Use bullet points where helpful.

## \U0001f3af General Intention
Summarise the purpose of this PR in 2-4 sentences, inferred from the title, commits, and code changes.

## \U0001f4cb Documentation of Changes
Bullet list of every change made (files, logic, config, dependencies).

## ✅ Tests & Checks Passed
List every static and dynamic check that passed (unit tests, build, linting, type-checking, etc.) based on the pipeline results above.

## \U0001f3d7️ Architectural & Significant Changes
Call out any changes that affect system design, introduce new patterns, or add major features. Write *None* if nothing applies.

## \U0001f512 Security & Risk Detection
Flag potential vulnerabilities (SQL injection, XSS, hardcoded secrets, insecure deserialization, etc.) or performance risks (memory leaks, N+1 queries, missing indexes, unbounded loops). Write *None detected* if the code looks clean.

## \U0001f50d SonarQube Analysis
{"Summarise any notable quality findings. Include this link for reviewers: " + sonar_url if sonar_url else "SonarQube scan passed. No results URL available."}

## \U0001f4ca Recommendation
State exactly one of: **✅ APPROVE**, **⚠️ REQUEST CHANGES**, or **\U0001f4ac NEEDS DISCUSSION** — followed by a one-sentence justification."""

result = api_request("/chat/completions", {
    "model": model_id,
    "max_tokens": 2000,
    "messages": [{"role": "user", "content": prompt}]
})
body = result["choices"][0]["message"]["content"]

existing = subprocess.run(
    ['gh', 'pr', 'list', '--head', branch, '--json', 'number', '--jq', '.[0].number'],
    capture_output=True, text=True
).stdout.strip()

with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
    f.write(body)
    tmp = f.name

if existing:
    subprocess.run(
        ['gh', 'pr', 'edit', existing, '--body-file', tmp],
        check=True
    )
    print(f"PR #{existing} description updated.")
else:
    subprocess.run(
        ['gh', 'pr', 'create', '--title', title, '--body-file', tmp, '--base', 'main', '--head', branch],
        check=True
    )
    print("PR created successfully.")
