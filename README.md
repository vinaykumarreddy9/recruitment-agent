# 🤖 Supervised Recruiting Agent

[![CI](https://github.com/JoshuaC215/agent-service-toolkit/actions/workflows/test.yml/badge.svg)](https://github.com/JoshuaC215/agent-service-toolkit/actions/workflows/test.yml)  
[![codecov](https://codecov.io/github/JoshuaC215/agent-service-toolkit/graph/badge.svg?token=5MTJSYWD05)](https://codecov.io/github/JoshuaC215/agent-service-toolkit)  
![Python Version](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FJoshuaC215%2Fagent-service-toolkit%2Frefs%2Fheads%2Fmain%2Fpyproject.toml)  
![License](https://img.shields.io/github/license/JoshuaC215/agent-service-toolkit)  
![Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_red.svg)

A specialized **AI-powered recruiting assistant** built on the [Agent Service Toolkit](https://github.com/JoshuaC215/agent-service-toolkit).  
The Supervised Recruiting Agent streamlines the hiring process by **gathering job requirements, drafting job descriptions, and generating technical screening questions** in a guided, conversational workflow.

It leverages **LangGraph** for agent orchestration, **FastAPI** for backend service delivery, and **Streamlit** for an interactive chat interface.

---

## 🚀 Overview

The agent acts as an intelligent assistant for hiring managers by automating the **initial recruitment stages**:

1. **Intent Collection** → Collects essential job details (company, role, skills, experience, location, etc.).
2. **Job Description Generation** → Drafts a professional JD with support for review and iteration.
3. **Technical Question Generation** → Creates **10 relevant pre-screening questions** based on the approved JD.

This ensures all outputs are **complete, structured, and manager-approved** before finalization.

---

## 🏗️ Architecture

> If GitHub doesn't render the diagram in preview, ensure GitHub's mermaid support is enabled for the repository or use an external mermaid live editor to visualize.

```mermaid
graph TD
    User[Hiring Manager] --> Streamlit[Streamlit App (UI)]
    Streamlit --> Client[Agent Client]
    Client --> FastAPI[FastAPI Service]
    FastAPI --> LangGraph[LangGraph Agent (Supervised Recruiting Agent)]
    LangGraph --> LLM[LLM (e.g., OpenAI, Groq)]
    LLM --> LangGraph
    LangGraph --> FastAPI
    FastAPI --> Client
    Client --> Streamlit
    Streamlit --> User

    subgraph LangGraph_Agent_Flow["LangGraph Agent Flow"]
        A[Start] --> B[Supervisor Agent]
        B --> C{Route Logic}
        C -- "invoke_intent" --> D[Intent Agent]
        D -- "incomplete/complete" --> B
        C -- "invoke_jd" --> E[JD Agent]
        E -- "incomplete/complete" --> B
        C -- "invoke_questions" --> F[Question Agent]
        F -- "incomplete/complete" --> B
        C -- "END" --> G[End]
    end
```

---

## ✨ Key Features

- 🗂️ **Guided Information Collection** — Structured job requirements gathering.  
- 🔄 **Iterative Refinement** — Review & revise JDs and screening questions.  
- 📝 **Structured Outputs** — Pydantic-based data models for consistency.  
- 🧩 **Modular Design** — Easy to extend with LangGraph agents.  
- 🐳 **Ready-to-Deploy** — Docker support for seamless setup.  
- 💬 **Conversational Flow** — Multi-turn guided interaction with hiring managers.  

---

## ⚙️ Setup & Usage

### 1) Clone the repository
```bash
git clone https://github.com/JoshuaC215/agent-service-toolkit.git
cd agent-service-toolkit
```

### 2) Configure environment
Create a `.env` file in the root and add your LLM credentials (at minimum):

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY or other provider keys
```

---

### 🐳 Run with Docker (Recommended)

Ensure Docker and Docker Compose (v2.23.0+) are installed. From the project root:

```bash
docker compose watch
```

- Streamlit App → http://localhost:8501  
- FastAPI Service → http://0.0.0.0:8080  
- API Docs → http://0.0.0.0:8080/redoc

To stop:

```bash
docker compose down
```

---

### 🐍 Run with Python (Without Docker)

Install `uv` if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/0.7.19/install.sh | sh
```

Create a virtual environment and install dependencies:

```bash
uv sync --frozen
source .venv/bin/activate
```

Run the services:

**Terminal 1 (FastAPI Service)**
```bash
python src/run_service.py
```

**Terminal 2 (Streamlit App)**
```bash
streamlit run src/streamlit_app.py
```

---

## 💡 How to Interact

1. Start the Streamlit app.  
2. Greet the agent or provide job context (e.g., *"Looking to hire a Backend Engineer at Acme Corp"*).  
3. The **Intent Agent** collects role details.  
4. The **JD Agent** drafts a job description — review, request edits, and approve.  
5. The **Question Agent** generates **10 screening questions** — review & finalize.  
6. Workflow completes once JD + questions are approved.

---

## 🧰 Configuration & Customization

- **Agent Logic** — `supervisor_agent.py` controls routing & flow.  
- **Prompt Templates** — modify prompts in the agent code to tune tone/style.  
- **Default LLM** — change `DEFAULT_MODEL` in `core/settings.py` or via `.env` to try different providers.  
- **Data Models** — Pydantic models live under `core` for validation and communication between agents.

---

## ♻️ Extending the Agent

- Add new agent nodes (e.g., interview scheduling, candidate scoring).  
- Replace or augment LLM provider for on-premise or specialized models.  
- Add persistence (Postgres, Redis) for session recovery and audit logs.  
- Integrate with ATS/HRIS systems via webhooks or connectors.

---

## 💬 Example Conversation

**Hiring Manager:** "Hi — I want to hire a Senior ML Engineer for remote at Acme."  
**Agent:** "Great! Which skills, experience, and team level should I capture?"  
**Hiring Manager:** "Skills: PyTorch, MLOps, AWS. 5+ years."  
**Agent:** "Thanks — here's a first draft JD (shortened): ... Would you like the JD to emphasize product or research?"  
*(Iterate until approved; then agent generates 10 targeted screening questions.)*

---

## 🤝 Contributing

Contributions welcome — please follow the standard fork → branch → PR workflow:

1. Fork the repo  
2. Create a feature branch (`git checkout -b feature-name`)  
3. Commit changes (`git commit -m 'Add feature'`)  
4. Push (`git push origin feature-name`)  
5. Open a Pull Request

Please ensure tests are added and CI passes for significant changes.

---

## 📜 License

MIT License — see the `LICENSE` file for details.

---

*README generated and validated to ensure proper badge formatting and a GitHub-compatible Mermaid block.*
