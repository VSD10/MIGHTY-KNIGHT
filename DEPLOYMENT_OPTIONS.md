# 🚀 Mighty Knight — Staff Delivery & Deployment Guide

This guide breaks down the **best ways to deliver Mighty Knight to your academy staff** so they can easily use it without technical hassles.

---

## 🏆 Recommendation Matrix: Which Option is Best?

| Deployment Method | Best For | Staff Experience | Setup Effort | Centralized Data? |
|---|---|---|---|---|
| **Option 1: Cloud Deployment** 🌟 *(Recommended)* | Multiple staff members working from anywhere | ⭐⭐⭐⭐⭐ Open URL in browser | Low (1-time setup) | YES (Shared database) |
| **Option 2: Local Office Network (LAN)** | Staff working inside academy office on Wi-Fi | ⭐⭐⭐⭐ Open IP address | Very Low | YES (Shared office DB) |
| **Option 3: Single-Click Desktop Launcher** | Staff running app on 1 local Windows PC | ⭐⭐⭐ Double-click icon | Very Low | NO (Local to PC) |

---

## Option 1: Cloud Deployment (🌟 The BEST Way for Staff)

### Why it's the best:
- **Zero installation for staff**: Staff don't need Python, Node.js, terminal, or Git.
- **Works on any device**: Laptops, iPads, tablets, or phones.
- **Shared Data**: When Manager A uploads an Excel file, Manager B sees the updated schedule instantly.

### How to set it up (Free/Low Cost):
1. **Frontend**: Deploy `frontend/` to **Vercel** or **Netlify** (Free tier).
2. **Backend**: Deploy `backend/` to **Render** or **Railway** (Free/Cheap tier).
3. **Domain**: Connect a custom domain like `https://schedule.yourchessacademy.com`.

---

## Option 2: Local Office Network (LAN Server)

If you want the app to run inside your academy office without paying for cloud servers:

### How it works:
1. Run the backend and frontend on **one main office PC**.
2. Staff connected to the academy Wi-Fi can access the app from their laptops via the PC's local IP address (e.g. `http://192.168.1.100:5173`).

### Setup Steps:
1. On the main office PC, find its local IP address (in CMD: `ipconfig` -> e.g. `192.168.1.100`).
2. Run backend bound to network:
   ```powershell
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
3. Run frontend bound to network:
   ```powershell
   npm run dev -- --host
   ```
4. Staff type `http://192.168.1.100:5173` into their web browser!

---

## Option 3: 1-Click Desktop Launcher for Windows (`.bat` Script)

If a staff member needs to run the app offline on their own Windows PC, you can give them a single **`Start_Mighty_Knight.bat`** file that launches everything with one double-click!

### How `Start_Mighty_Knight.bat` works:
Double-clicking the batch file:
1. Automatically starts the Python backend server in the background.
2. Automatically starts the React frontend server.
3. Automatically opens Chrome/Edge to `http://localhost:5173/`.

---

## 📌 Final Recommendation for Academy Staff

> **If your staff work from home or multiple locations**: Choose **Option 1 (Cloud Deployment)**. It takes 15 minutes to set up on Vercel + Render and gives staff a professional URL.
>
> **If staff only work at the academy office**: Choose **Option 2 (LAN Network)** or **Option 3 (1-Click Launcher)**.
