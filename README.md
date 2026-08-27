# NTI Project

A full-stack AI-powered application featuring document ingestion, vector-based retrieval, media processing (YouTube and images), and interactive learning tools. 

The project is split into two main parts:
* **Backend:** A robust API built with Python (FastAPI), managing AI model integrations, vector stores, and content generation.
* **Frontend:** A responsive, modern user interface built with Next.js, React, and Tailwind CSS.

## 📋 Prerequisites

Before you begin, ensure you have the following installed on your machine:
* **Python 3.8+** (for the backend)
* **Node.js 18+** and **npm** (for the frontend)
* **Git** (to clone the repository)

---

## 🚀 Getting Started

Follow these steps to get both the backend and frontend up and running on your local machine.

### 1. Clone the Repository
git clone <your-repository-url>
cd NTI-Project

### 2. Backend Setup
The backend handles all the heavy lifting, including database interactions, embeddings, and API routes.

1. **Navigate to the backend directory:**
   cd backend

2. **Create and activate a virtual environment:**
   * **Windows:**
     python -m venv venv
     venv\Scripts\activate
   
   * **macOS/Linux:**
     python3 -m venv venv
     source venv/bin/activate

3. **Install dependencies:**
   pip install -r ../requirements.txt

4. **Set up Environment Variables:**
   Duplicate the provided `.env copy` file and rename it to `.env`. Fill in your specific API keys.
   cp ".env copy" .env

5. **Run the Backend Server:**
   uvicorn app.main:app --reload

   The backend API will now be running at http://localhost:8000. You can view the interactive API documentation at http://localhost:8000/docs.

### 3. Frontend Setup
The frontend is a Next.js web application that interacts with the FastAPI backend.

1. **Open a new terminal window** and navigate to the frontend directory from the project root:
   cd frontend

2. **Install dependencies:**
   npm install

3. **Run the Development Server:**
   npm run dev

   The frontend will now be running at http://localhost:3000.

---

## 📂 Project Structure

NTI-Project/
│
├── backend/                  # FastAPI Python application
│   ├── .env copy             # Template for environment variables
│   ├── pyproject.toml        # Backend dependencies and configuration
│   ├── tests/                # Unit testing
│   └── app/
│       ├── main.py           # Application entry point
│       ├── api/              # API routers and endpoints
│       ├── core/             # Core configuration and dependencies
│       ├── models/           # Data schemas and Pydantic models
│       └── services/         # Business logic (vector store, embeddings, chunking, etc.)
│
├── frontend/                 # Next.js React application
│   ├── package.json          # Frontend dependencies
│   ├── next.config.ts        # Next.js configuration
│   ├── postcss.config.mjs    # Tailwind/PostCSS config
│   └── app/                  # Next.js App Router (pages, layouts, globals.css)
│
└── requirements.txt          # Root Python dependencies

## 🛠️ Built With

* **Backend:** Python, FastAPI, Uvicorn, Vector Databases, LLM Integrations.
* **Frontend:** Next.js (App Router), React, TypeScript, Tailwind CSS.
