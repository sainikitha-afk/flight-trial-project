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


# Flight Telemetry Full Stack App - Setup Guide

## Backend
1. Open terminal in backend folder
2. Create virtual environment:
   python -m venv venv
3. Activate venv:
   venv\Scripts\activate  (Windows)
4. Install dependencies:
   pip install -r requirements.txt
5. Run FastAPI backend:
   uvicorn main:app --reload

## MongoDB
- Install local MongoDB or run via Docker:
  docker run -d --name mongodb -p 27017:27017 mongo:latest

## Frontend
1. Open terminal in frontend folder
2. Install dependencies:
   npm install
3. Run frontend:
   npm start
