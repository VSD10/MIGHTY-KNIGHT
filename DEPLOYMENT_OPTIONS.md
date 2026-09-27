# 🚀 Mighty Knight Academy Scheduler — Complete Deployment Guide

This guide provides step-by-step instructions to deploy the Mighty Knight Academy Scheduling system so your staff, coaches, and administrators can access it from anywhere.

---

## 🏆 Deployment Methods at a Glance

| Method | Best For | Effort | Cost | Public URL? |
|---|---|---|---|:---:|
| **1. Unified Cloud Deployment (Render / Railway)** 🌟 | Multi-user team, access anywhere | 5 mins | Free / Low | Yes (`.onrender.com`) |
| **2. Vercel (Frontend) + Render (Backend)** | High-performance CDN distribution | 10 mins | Free | Yes (`.vercel.app`) |
| **3. Academy Office LAN (Wi-Fi Server)** | Staff working inside the academy office | 2 mins | $0 | Local IP (Office only) |
| **4. 1-Click Desktop Windows Launcher** | Single admin PC running offline | 0 mins | $0 | Local (`localhost:5173`) |

---

## 🌟 Method 1: Unified Cloud Deployment on Render (Recommended)

Thanks to the multi-stage [`Dockerfile`](file:///d:/CODESPACE/chess/Dockerfile) and [`render.yaml`](file:///d:/CODESPACE/chess/render.yaml), you can deploy both the React frontend and FastAPI backend **together as a single service** with a persistent database!

### Step 1: Push your code to GitHub
```bash
git add .
git commit -m "Add production deployment config"
git push origin main
```

### Step 2: Deploy on Render.com
1. Go to [Render.com](https://render.com) and sign in with GitHub.
2. Click **New +** → **Web Service**.
3. Select your GitHub repository (`chess` / `Mighty-Knight`).
4. Set the following settings:
   - **Environment**: `Docker`
   - **Region**: Closest to you (e.g., *Singapore* or *Frankfurt*)
   - **Plan**: `Free` or `Starter` ($7/mo with persistent disk)
5. Under **Advanced** → **Add Disk** (to save the database permanently):
   - **Name**: `sqlite-data`
   - **Mount Path**: `/app/backend/data`
   - **Size**: `1 GB`
6. Click **Create Web Service**.

🎉 In 3–5 minutes, your application will be live at `https://mighty-knight-scheduler.onrender.com`!

---

## 🌐 Method 2: Separate Vercel (Frontend) + Render/Railway (Backend)

If you prefer deploying the frontend to Vercel's global edge network:

### Step 1: Deploy Backend to Render or Railway
1. Create a Python Web Service pointing to `backend/`.
2. Build Command: `pip install -r backend/requirements.txt`
3. Start Command: `cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Copy your backend URL (e.g. `https://mighty-knight-api.onrender.com`).

### Step 2: Deploy Frontend to Vercel
1. Go to [Vercel.com](https://vercel.com) and import your repo.
2. Set **Root Directory**: `frontend`.
3. Add Environment Variable:
   - `VITE_API_BASE_URL` = `https://mighty-knight-api.onrender.com/api`
4. Click **Deploy**.

---

## 🏢 Method 3: Local Academy Office Network (LAN Server)

If you want the app running on one main office PC and accessible to all staff connected to the academy Wi-Fi:

### Step 1: Find the Office PC's IP Address
In Windows PowerShell / CMD:
```powershell
ipconfig
```
*(Look for IPv4 Address, e.g. `192.168.1.50`)*

### Step 2: Build the production bundle once
```powershell
cd frontend
npm run build
cd ..
```

### Step 3: Run the unified server accessible across the Wi-Fi
```powershell
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Step 4: Access from any device
Staff on the office Wi-Fi can open Chrome or Safari on their laptops/tablets and go to:
`http://192.168.1.50:8000`

---

## 💻 Method 4: 1-Click Desktop Launcher (`Start_Mighty_Knight.bat`)

For offline use on a single Windows machine:
1. Simply double-click [`Start_Mighty_Knight.bat`](file:///d:/CODESPACE/chess/Start_Mighty_Knight.bat).
2. It automatically starts both backend and frontend servers and launches your browser to `http://localhost:5173/`.

---

## 🐳 Running with Docker Locally

To run the complete production container locally:
```bash
docker-compose up --build
```
Open `http://localhost:8000` in your browser. All database changes persist in `backend/data/`.
