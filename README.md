# Compliance-as-a-Service: AML/KYC Assistant PoC

## What This Is

A proof-of-concept system that demonstrates how to apply AI responsibly in regulated financial compliance. It processes customer datasets through AML/KYC screening, combining deterministic rule-based detection with LLM-powered summarization for compliance officers.

**The Problem**: Compliance teams face a scaling dilemma: manual review doesn't scale, but fully automated AI creates regulatory risk because regulators require explainability. Black-box models fail all three regulatory checks (explainability, auditability, governance).

**The Solution**: Split the problem into two parts:
- **Deterministic rules make decisions** (auditable, reproducible, explainable)
- **AI explains those decisions** (useful for humans, but cannot override rules)
- **Humans make final approvals** (accountability remains with compliance officer)

This architecture satisfies regulatory requirements while gaining efficiency benefits of AI.

---

## Design Philosophy

### AI is Assistive, Not Autonomous

The fundamental architectural choice is to **never let AI make compliance decisions**. Instead:

1. **Deterministic rules identify violations** (fully auditable, reproducible)
   - Each finding traces back to specific rule and record index
   - Same data always produces same result
   - Regulators can read the code and understand exactly why a customer was flagged

2. **LLM summarizes findings** (improves usability, adds context)
   - Explains what violations mean in plain English
   - Cannot override rules or reinterpret findings
   - System works without it (graceful degradation)

3. **Humans make final decisions** (accountability remains with compliance officers)
   - Full accountability chain with logging and timestamps
   - Officers can exercise judgment on edge cases
   - Prevents catastrophic failures

### Multi-Step Explicit Workflow

The system follows 5 explicit steps, each independently testable and logged:

1. **Validate**: Check dataset integrity (columns, types, no corruption)
2. **Parse**: Normalize data (dates, names, amounts)
3. **Apply Rules**: Execute 6 deterministic compliance rules
4. **Enrich**: Add context (record indices, affected customer count)
5. **Summarize**: LLM explains findings in plain language (or fallback to rule-based summary)

### Graceful Degradation

The system works even if external services fail:
- **No OpenAI API key?** Uses rule-based summary (still produces valid report)
- **API timeout?** Fallback kicks in automatically
- **No network?** Core rules are local, system still processes files

---

## Why This Design?

Regulators examine three things in compliance systems: **explainability**, **auditability**, **governance**. Black-box AI fails all three. This architecture satisfies all three requirements:

| Aspect | Black-Box AI | This Architecture |
|--------|-------------|------------------|
| **Can you explain it?** | "Model said so" | "Rule X flagged it, see line Y of code" |
| **Can you reproduce it?** | Maybe (model drift) | Always (deterministic rules) |
| **Who's accountable?** | ??? | Compliance officer |

**See [ARCHITECTURE.md](ARCHITECTURE.md) for the detailed technical deep dive**, including implementation details, design decisions, governance considerations, and production roadmap.

---

## Quick Start

### Prerequisites
- Python 3.9+ (tested on 3.11, 3.13)
- pip (comes with Python)
- OpenAI API key (optional—system works without it)

### Setup (Local Machine)

```bash
git clone <repo-url>
cd compliance-assistant

# Create virtual environment
python -m venv venv

# Activate (choose for your OS):
# Windows (Command Prompt): venv\Scripts\activate
# Windows (PowerShell): .\venv\Scripts\Activate.ps1
# Mac/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set API key (optional - system works without it)
# Windows: set OPENAI_API_KEY=sk-your-key-here
# Mac/Linux: export OPENAI_API_KEY=sk-your-key-here

# Start server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` in your browser.

### Setup (GitHub Codespaces - Recommended)

1. Open this repository: https://github.com/traviss00/compliance-assistant
2. Click **Code** → **Codespaces** → **Create codespace on main**
3. Wait 2-3 minutes for environment setup
4. Once ready, run in the terminal:

```bash
export OPENAI_API_KEY="your-key-here"  # Optional
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. Click "Open in Browser" or visit `http://localhost:8000`

---

## Testing

1. Go to `http://localhost:8000`
2. Drag `sample_data.csv` onto the upload area (or click to browse)
3. Click **Upload & Assess**
4. View findings, risk classification, and AI summary

**Sample CSV** (create as `sample_customers.csv`):
```csv
customer_name,country,account_open_date,transaction_amount,verification_status
John Smith,Canada,2024-02-01,50000,verified
Jane Doe,Iran,2024-01-15,500000,pending
Vladimir Putin,Russia,2024-02-05,100000,verified
Ahmed Hassan,Syria,2024-02-10,2500000,incomplete
```

**Expected Result**: High risk due to PEP match (Putin) and high-risk countries (Iran, Syria).

---

## Files & Structure

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI entry point and upload endpoint |
| `app/services/agent.py` | Multi-step compliance workflow |
| `app/services/rules.py` | 6 deterministic compliance rules |
| `app/services/llm.py` | LLM integration with graceful fallback |
| `app/templates/index.html` | Web UI |
| `ARCHITECTURE.md` | Technical deep dive |

**See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed project structure and service descriptions.**

---

## What's Next (If Moving to Production)

This PoC proves the architecture works. To move toward production:

### Phase 1: Real Compliance Rules
- Connect to real PEP databases (OFAC, UN sanctions lists)
- Implement transaction pattern analysis for money laundering detection
- Integrate external verification services (address validation, ID verification)

### Phase 2: Data Architecture
- Replace single CSV uploads with batch/real-time processing
- Add data warehouse integration
- Implement audit logging to immutable database (7-year retention requirement)

### Phase 3: Regulatory Features
- PDF report export for regulators
- Workflow approvals (compliance officer sign-off)
- Compliance metrics dashboard
- Plain-language rule documentation

### Phase 4: Security & Infrastructure
- Add database (PostgreSQL/MongoDB) for persistence
- Implement role-based access control
- Conduct security audit and penetration testing
- Deploy with authentication (OAuth2/API keys)

### Phase 5: Operations
- Comprehensive logging and monitoring
- Compliance team QA process
- Customer notification and appeals system
- Rule versioning with change audit trail

**See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed production roadmap with phases and timelines.**

---

## Stack

- **FastAPI 0.104+**: Web framework
- **pandas 2.0+**: Data processing
- **pydantic 2.5+**: Data validation
- **OpenAI 1.3+**: LLM integration
- **Python 3.9+**: Language

---

## Support & Troubleshooting

### Common Issues

**"OPENAI_API_KEY not set"**
- System falls back to rule-based summary automatically
- Compliance assessment still works perfectly

**"Port 8000 is already in use"**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

**"ModuleNotFoundError: No module named 'fastapi'"**
```bash
pip install -r requirements.txt
```

**See [ARCHITECTURE.md](ARCHITECTURE.md#troubleshooting--support) for more troubleshooting and detailed API reference.**

---

## License

This PoC is provided as-is for educational and demonstration purposes.

---

## Important Disclaimer

**This is a Proof-of-Concept, Not Production Code**

This demonstrates a reference architecture for AI-assisted compliance. Before any production use, you must:

### Regulatory & Legal Review
- Engage compliance and legal teams
- Document how this meets your regulatory requirements (FinCEN, GDPR, etc.)
- Define compliance officer accountability for system decisions
- Establish escalation procedures for edge cases

### Security & Operations
- Conduct security audit and penetration testing
- Implement authentication, authorization, and encryption
- Establish monitoring, alerting, and incident response
- Plan backup, recovery, and capacity scaling

### Data & Compliance
- Implement data protection and privacy controls
- Define data retention policies
- Document rule versioning and change control
- Plan for regulatory audit support

### Testing & Validation
- Validate rule accuracy against real regulatory requirements
- Stress test with realistic data volumes
- Test fallback modes (LLM unavailable, etc.)
- Conduct end-to-end testing with compliance team

### Accountability
Before deploying:
1. **Compliance Officer** must understand and approve all rules
2. **Legal Team** must review regulatory alignment
3. **Security Team** must approve architecture and controls
4. **Operations Team** must plan support and response

**Use this PoC to understand the architecture. Adapt it based on your specific regulatory requirements and risk tolerance.**

---

## Comparison: Our Architecture vs. Black-Box AI

### Scenario 1: How Does It Work?

**With Black-Box AI**: "Um... the model said so? We can't explain it."

**With Our Architecture**: "Rule 002 (Sanctions List Match) flagged customer at record index 1247. Here's the record. Here's the sanctions list. Here's our data source. See line 15 of rules.py where we check it."

### Scenario 2: Customer Disputes the Decision

Customer: "I'm not on any sanctions list!"

**With Black-Box AI**: "Well, the model scored you 0.87... seems pretty high?" (No defense)

**With Our Architecture**: "Record shows your name exactly matched entry XYZ in the sanctions list. You can see it here. You have 10 days to appeal." (Clear, defensible)

### Scenario 3: Fixing a False Positive

Business: "We're getting too many false positives on Rule 4."

**With Black-Box AI**: "Retrain the entire model? Good luck." (Weeks of work, new bugs)

**With Our Architecture**: "Update the $1M threshold to $5M in line 87 of rules.py. Test with historical data. Deploy." (Minutes of work, fully reviewable)

---

## More Information

**For technical implementation details, design decisions, governance considerations, and production roadmap:**

👉 **See [ARCHITECTURE.md](ARCHITECTURE.md)**
