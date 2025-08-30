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

```mermaid
graph TD
    User[Hiring Manager] --> Streamlit[Streamlit App (UI)];
    Streamlit --> Client[Agent Client];
    Client --> FastAPI[FastAPI Service];
    FastAPI --> LangGraph[LangGraph Agent (Supervised Recruiting Agent)];
    LangGraph --> LLM[LLM (e.g., OpenAI, Groq)];
    LLM --> LangGraph;
    LangGraph --> FastAPI;
    FastAPI --> Client;
    Client --> Streamlit;
    Streamlit --> User;

    subgraph LangGraph Agent Flow
        A[Start] --> B(Supervisor Agent);
        B --> C{Route Logic};
        C -- "invoke_intent" --> D(Intent Agent);
        D -- "incomplete/complete" --> B;
        C -- "invoke_jd" --> E(JD Agent);
        E -- "incomplete/complete" --> B;
        C -- "invoke_questions" --> F(Question Agent);
        F -- "incomplete/complete" --> B;
        C -- "END" --> G[End];
    end
```

---

## ✨ Key Features

- 🗂️ **Guided Information Collection** → Structured job requirements gathering.  
- 🔄 **Iterative Refinement** → Review & revise JDs and questions.  
- 📝 **Structured Outputs** → Pydantic-based data models for consistency.  
- 🧩 **Modular Design** → Easy to extend with LangGraph agents.  
- 🐳 **Ready-to-Deploy** → Docker support for seamless setup.  
- 💬 **Conversational Flow** → Multi-turn guided interaction with hiring managers.  

---

## ⚙️ Setup & Usage

### 1️⃣ Clone the Repository
```sh
git clone https://github.com/JoshuaC215/agent-service-toolkit.git
cd agent-service-toolkit
```

### 2️⃣ Configure Environment
Create a `.env` file in the root directory and provide at least one LLM API key:  

```sh
cp .env.example .env
# Edit .env and set OPENAI_API_KEY or other provider keys
```

---

### 🐳 Run with Docker (Recommended)

Ensure **Docker** and **Docker Compose (v2.23.0+)** are installed.  
From the project root:

```sh
docker compose watch
```

- Streamlit App → [http://localhost:8501](http://localhost:8501)  
- FastAPI Service → [http://0.0.0.0:8080](http://0.0.0.0:8080)  
- API Docs → [http://0.0.0.0:8080/redoc](http://0.0.0.0:8080/redoc)  

To stop:
```sh
docker compose down
```

---

### 🐍 Run with Python (Without Docker)

Install [uv](https://github.com/astral-sh/uv) if not installed:  
```sh
curl -LsSf https://astral.sh/uv/0.7.19/install.sh | sh
```

Create a virtual environment and install dependencies:  
```sh
uv sync --frozen
source .venv/bin/activate
```

Run the services:

**Terminal 1 (FastAPI Service)**  
```sh
python src/run_service.py
```

**Terminal 2 (Streamlit App)**  
```sh
streamlit run src/streamlit_app.py
```

---

## 💡 How to Interact

1. Start the Streamlit app.  
2. Greet the agent or specify a job (e.g., *"Looking to hire a Data Engineer at Microsoft"*).  
3. The **Intent Agent** collects details.  
4. The **JD Agent** drafts a job description → review & approve.  
5. The **Question Agent** generates **10 screening questions** → review & approve.  
6. Workflow completes once all outputs are finalized.  

---

## 🔧 Customization

- **Agent Logic** → Modify `supervisor_agent.py` for flow changes.  
- **Prompt Engineering** → Adjust `PromptTemplate` instances for tone & style.  
- **LLM Provider** → Update `DEFAULT_MODEL` in `core/settings.py` or `.env`.  

---

## 🤝 Contributing

Contributions are welcome! 🎉  

- Fork the repo  
- Create a feature branch (`git checkout -b feature-name`)  
- Commit changes (`git commit -m 'Add feature'`)  
- Push to branch (`git push origin feature-name`)  
- Open a Pull Request  

---

## 📜 License

This project is licensed under the **MIT License**.  
