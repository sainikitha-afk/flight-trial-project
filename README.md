# Flight Trial Data Portal ✈️

A secure web application to upload, manage, and view telemetry data from flight trials.

## 💻 Features
- 🔐 Login & Registration with token-based auth
- 📤 CSV Upload (only after login)
- 🧪 Add parameters to flight data
- 📄 View existing flight IDs from database
- ⚙️ FastAPI backend with MongoDB
- 🎨 React frontend with Axios and routing

## 🧠 Tech Stack
- Frontend React, Axios, React Router
- Backend FastAPI, Pymongo
- Database MongoDB
- Auth JWT (JSON Web Tokens)

## 🚀 Getting Started

### Backend
```bash
cd backend
python -m venv venv
venvScriptsactivate
pip install -r requirements.txt
uvicorn mainapp --reload
