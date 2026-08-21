# Contributing to JARVIS

Thanks for your interest in JARVIS! This document covers how to report bugs, suggest features, and submit pull requests.

## 🐛 Reporting Bugs

Open an issue at [github.com/venu0807/Jarvis/issues](https://github.com/venu0807/Jarvis/issues) using the **Bug Report** template. Please include:

- What you were trying to do
- What happened (with logs)
- What you expected to happen
- Environment (WSL version, Docker version, OS)

## 💡 Suggesting Features

Open an issue using the **Feature Request** template. Tell us:

- What problem does this solve?
- How should it work?
- Are there alternatives you considered?

## 🔧 Pull Requests

1. **Fork** the repo
2. **Create a branch** for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make changes** following the existing code style
4. **Test** locally:
   ```bash
   python -m pytest tests/
   docker compose up -d
   # verify your changes work
   ```
5. **Commit** with a clear message:
   ```bash
   git commit -m "feat: add XYZ automation"
   ```
6. **Push** and **open a PR** with:
   - Description of what changed
   - Reference to any related issue
   - Screenshots/logs if relevant

## 🛠 Local Development Setup

```bash
# Clone
git clone https://github.com/venu0807/Jarvis.git
cd Jarvis

# Set up Python venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-base.txt

# Copy environment template
cp automations/job-automation/.env.example automations/job-automation/.env
# Edit .env with your actual credentials

# Start the stack
docker compose up -d

# Verify
curl http://localhost:9090/-/healthy  # Prometheus
open http://localhost:3001            # Grafana (admin/admin)
```

## 📐 Code Style

- **Python**: Black formatter (88 chars), type hints where possible
- **Shell**: bash with `set -e`
- **YAML/JSON**: 2-space indent
- **Markdown**: 80-char wrap for prose

## 🧪 Testing

- Add unit tests for new logic in `tests/`
- Run `python -m pytest tests/` before pushing
- Integration tests live in `tests/integration/`

## 🔐 Security

If you discover a security issue, **DO NOT** open a public issue. Email [pvgreddy3@gmail.com](mailto:pvgreddy3@gmail.com) instead.

## 📜 License

By contributing, you agree your contributions will be licensed under MIT.
