# Two-Tier Flask + MySQL App with CI/CD Pipeline

## What is this project?

This is a two-tier web application. That means the app has two separate parts:
- **Tier 1** — A Flask web app (the part users see and interact with)
- **Tier 2** — A MySQL database (the part that stores messages)

Both parts run as separate Docker containers on an AWS EC2 server. Whenever I push new code to GitHub, Jenkins automatically pulls the code and redeploys the app. This is called a **CI/CD pipeline** — it's how real companies ship code to production.

---

## Tools Used

| Tool | Why |
|------|-----|
| Python + Flask | Backend web app |
| MySQL | Database to store messages |
| Docker | Package the app into containers |
| Docker Compose | Run Flask + MySQL containers together |
| AWS EC2 | Cloud server to host everything |
| Jenkins | Automatically deploy on every git push |
| GitHub | Store the code + trigger Jenkins |

---

## How the App Works

1. User opens the app in browser
2. Flask fetches all messages from MySQL and shows them
3. User types a message and clicks Send
4. jQuery sends the message to Flask without reloading the page (AJAX)
5. Flask saves the message to MySQL
6. Message appears on screen instantly

---

## Project Structure

```
two-tier-app/
├── app.py               # Flask backend
├── Dockerfile           # How to build the Flask container
├── docker-compose.yaml  # Run Flask + MySQL together
├── Jenkinsfile          # CI/CD pipeline steps
├── requirements.txt     # Python dependencies
├── message.sql          # SQL schema
└── templates/
    └── index.html       # Frontend UI
```

---

## Issues I Faced & How I Fixed Them

### Issue 1 — Tried to install MySQL locally (not needed)
**What happened:** I started installing MySQL using Homebrew on my Mac thinking the app needed it locally.

**The loophole:** In a Dockerized project, MySQL runs as a container. You don't need to install it on your machine at all.

**Fix:** Stopped the Homebrew installation with `Ctrl+C` and used MySQL as a Docker container instead via `docker-compose.yaml`.

---

### Issue 2 — Dockerfile was using unnecessary multi-stage build
**What happened:** The Dockerfile had two stages — `base` and `development` — which added complexity for no reason.

**The loophole:** Multi-stage builds are useful when you're compiling code (like Go or Java). For a simple Python Flask app, one stage is enough.

**Fix:** Simplified the Dockerfile to a single stage.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y pkg-config default-libmysqlclient-dev build-essential
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

---

### Issue 3 — `pkg-config: not found` error during Docker build
**What happened:** When building the Docker image, pip failed to install `mysqlclient` with this error:
```
/bin/sh: 1: pkg-config: not found
Can not find valid pkg-config name.
```

**The loophole:** `python:3.12-slim` is a minimal image — it doesn't have system-level MySQL libraries that `mysqlclient` needs to compile itself.

**Fix:** Added these system packages in the Dockerfile before running pip install:
```dockerfile
RUN apt-get update && apt-get install -y \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
```

---

### Issue 4 — Flask crashed because MySQL wasn't ready yet
**What happened:** Flask container started and immediately tried to connect to MySQL, but MySQL was still initializing. Flask crashed with:
```
MySQLdb.OperationalError: (2002, "Can't connect to server on 'mysql-db' (115)")
```

**The loophole:** `depends_on` in Docker Compose only waits for the MySQL *container to start*, not for MySQL to be *actually ready to accept connections*. MySQL takes 20-30 seconds to fully initialize on first boot.

**Fix 1:** Added a healthcheck in `docker-compose.yaml` so Flask waits until MySQL is truly ready:
```yaml
healthcheck:
  test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-pexample"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s
```

**Fix 2:** Added a retry loop in `app.py` so Flask keeps retrying the DB connection instead of crashing:
```python
def init_db():
    retries = 5
    while retries:
        try:
            # connect and create table
            break
        except Exception as e:
            retries -= 1
            time.sleep(5)
```

---

### Issue 5 — Wrong password in healthcheck
**What happened:** The healthcheck was using `-prootpassword` but the actual `MYSQL_ROOT_PASSWORD` was set to `example`. So the healthcheck kept failing and Flask never started.

**The loophole:** Copy-paste error — the healthcheck password didn't match the actual MySQL root password.

**Fix:** Updated healthcheck to use the correct password:
```yaml
test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-pexample"]
```

---

### Issue 6 — `MYSQL_USER: default` caused MySQL error
**What happened:** MySQL refused to create the user because `default` is a reserved keyword in MySQL.

**The loophole:** You can't use reserved words as MySQL usernames.

**Fix:** Changed the username from `default` to `flaskuser`.

---

### Issue 7 — Jenkins build stuck on "Waiting for next available executor"
**What happened:** Jenkins pipeline was triggered but kept saying:
```
Still waiting to schedule task
Waiting for next available executor
```

**The loophole:** Two problems at once:
1. Jenkins built-in node was **offline** because it ran out of swap space and temp space — Jenkins automatically takes nodes offline when resources are low as a safety measure
2. The `Jenkinsfile` had `agent { label 'Jenkins' }` but the node didn't have that label assigned

**Fix:**
1. Added swap space on EC2:
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```
2. Lowered disk threshold in **Manage Jenkins → Nodes → Configure Node Monitors**
3. Added label `Jenkins` to the built-in node in **Node Configuration**
4. Set node usage to **"Use this node as much as possible"**

---

### Issue 8 — debug=True hardcoded in app.py
**What happened:** The Flask app had `debug=True` hardcoded, which is a security risk in production — it exposes system info to anyone who triggers an error.

**The loophole:** Debug mode should never be hardcoded. It should be controlled by an environment variable.

**Fix:**
```python
app.run(host='0.0.0.0', port=5000, debug=os.environ.get('FLASK_DEBUG', 'False') == 'True')
```

---

## CI/CD Flow (How Auto Deploy Works)

```
I push code to GitHub
        ↓
GitHub sends a webhook to Jenkins
        ↓
Jenkins pulls the latest code
        ↓
Jenkins runs docker-compose down then docker-compose up --build
        ↓
New version of app is live on EC2 at http://<ec2-ip>:5000
```

---

## How to Run Locally

```bash
# Clone the repo
git clone https://github.com/<your-username>/two-tier-app.git
cd two-tier-app

# Start the app
docker-compose up --build

# Open browser
http://localhost:5000
```

---

## Key Learnings

- Docker Compose `depends_on` does NOT mean "wait until ready" — always use healthchecks
- Never install databases locally when using Docker — let containers handle it
- Always control `debug` mode via environment variables, never hardcode it
- Jenkins needs enough memory and correct labels to run builds
- Reserved words in MySQL (like `default`) will silently break your setup
- A retry loop in your app is a simple but powerful way to handle startup race conditions
