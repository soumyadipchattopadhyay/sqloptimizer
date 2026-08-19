import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# 1. Load the .env file FIRST before other custom imports
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.schemas import FusionEbsRequest, FusionEbsResponse, ChatRequest, ChatResponse
from app.services.gemini_service import process_fusion_ebs_action, process_chat_message
from app.services.db_service import connect_to_db, execute_query, generate_explain_plan, DbConnectRequest, DbQueryRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure Gemini API configuration is present when FastAPI starts."""
    print("⏳ Checking Gemini API configuration...")
    
    if not os.environ.get("GEMINI_API_KEY"):
        #print("\n❌ CRITICAL ERROR: GEMINI_API_KEY is not set in .env or system environment!")
        print()
    else:
        print("✅ GEMINI_API_KEY is configured.")
        
    yield

app = FastAPI(title="PwC SQLator", lifespan=lifespan)
# ... rest of your main.py code

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")


# --- HTML Page Routes ---

@app.get("/", response_class=HTMLResponse)
async def render_launchpad(request: Request):
    return templates.TemplateResponse(request=request, name="launchpad.html")

@app.get("/fusion-ebs", response_class=HTMLResponse)
async def render_fusion_ebs(request: Request):
    return templates.TemplateResponse(request=request, name="fusion_ebs.html")


# --- API Endpoints ---

@app.post("/api/fusion-ebs/process", response_model=FusionEbsResponse)
async def fusion_ebs_process(req: FusionEbsRequest):
    return process_fusion_ebs_action(req)

@app.post("/api/chat", response_model=ChatResponse)
async def chat_process(req: ChatRequest):
    return process_chat_message(req)


@app.get("/ebs-query", response_class=HTMLResponse)
async def render_ebs_query(request: Request):
    return templates.TemplateResponse(request=request, name="ebs_query.html")

# --- Database API Endpoints ---
@app.post("/api/db/connect")
async def db_connect(req: DbConnectRequest):
    return connect_to_db(req)

@app.post("/api/db/execute")
async def db_execute(req: DbQueryRequest):
    return execute_query(req)

@app.post("/api/db/explain")
async def db_explain(req: DbQueryRequest):
    return generate_explain_plan(req)
