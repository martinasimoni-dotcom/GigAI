# FINAL INSTRUCTIONS FOR CLAUDE CODE

## 📦 What to Upload to Claude Code

Upload these 2 files:

1. **GIGAI_SYSTEM_PRD_COMPACT.md** (or GIGAI_SYSTEM_PRD.md)
   - This is the complete system specification
   - Contains all the code Claude Code needs to create

2. **.env.configured** (rename it to just `.env`)
   - This has all your API keys filled in
   - After running the Python script, make sure ACC_ACCESS_TOKEN is filled

---

## ✅ Before Uploading - Complete Your .env

After running `python generate_acc_token.py`, you should have:

```env
# Your complete .env file should have:

✅ ANTHROPIC_API_KEY=sk-ant-api03DNd...
✅ VOYAGE_API_KEY=pa-a04nMD6O3_cw...
✅ FIREFLIES_WEBHOOK_SECRET=3f11d63960c34e59...
✅ GMAIL_CLIENT_ID=919904365153-qrk...
✅ GMAIL_CLIENT_SECRET=GOCSPX-Upicge...
✅ ACC_CLIENT_ID=AZcDrVq55RD612c...
✅ ACC_CLIENT_SECRET=kgB7w7t72XO4cwvQ...
✅ ACC_ACCESS_TOKEN=eyJhbGciOi... (from Python script!)
✅ ACC_HUB_ID=b.c1adef8c-d214...
✅ ACC_PROJECT_ID=b.af6115b4-8d2f...
✅ ACC_CONTAINER_ID=af6115b4-8d2f...

⚠️ DATABASE_URL=postgresql://gigai:gigai@localhost:5432/gigai
⚠️ GCP_PROJECT_ID=your_gcp_project_id_here (optional for now)
```

---

## 🎯 What to Tell Claude Code

### Option 1: Simple Prompt
```
Please implement the complete GIGAI system according to GIGAI_SYSTEM_PRD_COMPACT.md

Use the .env file for all API credentials.

Create all files in the structure specified in the PRD.
```

### Option 2: Detailed Prompt
```
Build the GIGAI Material Change Coordinator system:

1. Read GIGAI_SYSTEM_PRD_COMPACT.md for complete specifications
2. Use .env for all API keys and configuration
3. Create the complete project structure:
   - Backend (FastAPI with ACC + Claude integrations)
   - Frontend (React mobile-first dashboard)
   - Database models (PostgreSQL + pgvector)
   - Scripts (setup, test, demo)
4. Follow the architecture exactly as specified
5. Create all files with complete, production-ready code

The .env file has all required API keys filled in.
```

### Option 3: Step-by-Step (Recommended)
```
I have a complete PRD for the GIGAI system and a configured .env file with all API keys.

Please:
1. Read the PRD to understand the system architecture
2. Create the complete project structure
3. Implement all backend code (FastAPI, integrations, database)
4. Implement all frontend code (React mobile dashboard)
5. Create all helper scripts
6. Use the .env file for all credentials

Start with the backend core, then frontend, then scripts.
After each phase, let me know what was created.
```

---

## 🚀 What Claude Code Will Create

```
gigai/
├── .env (your file with API keys)
├── .env.example
├── .gitignore
├── requirements.txt
├── docker-compose.yml
│
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── api/ (webhooks.py, proposals.py)
│   ├── integrations/ (acc_client.py, claude_client.py)
│   ├── models/ (database.py, schemas.py)
│   └── data/demo/ (demo scenarios)
│
├── frontend/
│   ├── package.json
│   ├── src/ (App.jsx, Dashboard.jsx)
│   └── public/ (manifest.json)
│
└── scripts/
    ├── setup_database.py
    ├── test_acc_connection.py
    ├── test_claude_api.py
    ├── run_demo.py
    └── get_gmail_token.py
```

---

## ✅ After Claude Code Finishes

### 1. Start Database
```bash
docker-compose up -d
python scripts/setup_database.py
```

### 2. Test APIs
```bash
python scripts/test_claude_api.py      # Should work!
python scripts/test_acc_connection.py  # Should work!
python scripts/test_database.py        # Should work!
```

### 3. Start Backend
```bash
cd backend
pip install -r ../requirements.txt
python main.py
```

### 4. Start Frontend (new terminal)
```bash
cd frontend
npm install
npm run dev
```

### 5. Access on Phone
```
http://YOUR_COMPUTER_IP:5173
```

### 6. Run Demo
```bash
python scripts/run_demo.py
```

This will trigger the porthole window scenario and you should see:
- ✅ Proposal appears in dashboard
- ✅ 89% confidence score
- ✅ Cost: €2,340
- ✅ Click Accept → Creates RFI in your ACC "Sea house" project!

---

## 🎯 Summary

**Upload to Claude Code:**
1. PRD file (GIGAI_SYSTEM_PRD_COMPACT.md)
2. .env file (with ACC_ACCESS_TOKEN from Python script)

**Say to Claude Code:**
"Implement the complete GIGAI system according to the PRD. Use .env for credentials."

**Claude Code will:**
- Create all 50+ files
- Complete backend + frontend + scripts
- Production-ready code

**You do:**
```bash
docker-compose up -d
python backend/main.py
# (new terminal) cd frontend && npm run dev
# Open on phone: http://YOUR_IP:5173
```

**That's it!** 🎉

---

## ⚠️ Important Notes

1. **Token Expiration**: ACC_ACCESS_TOKEN expires in 1 hour
   - For testing: Just regenerate when needed
   - For production: Implement OAuth refresh (already in code)

2. **GCP Pub/Sub**: Optional for now
   - System works without it (processes events directly)
   - Add later when ready

3. **Gmail Token**: Optional for now
   - Email notifications disabled without it
   - Dashboard + ACC notifications still work

4. **Database**: Use Docker (easiest)
   - Just `docker-compose up -d`
   - Or use cloud provider (Neon, Supabase)

---

## 🎊 You're Ready!

Just upload the 2 files to Claude Code and let it build the complete system! 🚀
