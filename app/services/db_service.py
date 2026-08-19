import oracledb
import uuid
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# In-memory connection store (For production, use a proper session manager or connection pool)
ACTIVE_CONNECTIONS = {}

class DbConnectRequest(BaseModel):
    username: str
    password: str
    host: str
    port: int
    service_name: str

class DbQueryRequest(BaseModel):
    session_id: str
    query: str

def connect_to_db(req: DbConnectRequest) -> Dict[str, Any]:
    try:
        dsn = oracledb.makedsn(req.host, req.port, service_name=req.service_name)
        # Thick mode is only needed for advanced legacy features. Thin mode (default) is faster.
        connection = oracledb.connect(user=req.username, password=req.password, dsn=dsn)
        
        session_id = str(uuid.uuid4())
        ACTIVE_CONNECTIONS[session_id] = connection
        
        return {"success": True, "session_id": session_id, "message": "Connection established successfully."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def execute_query(req: DbQueryRequest) -> Dict[str, Any]:
    if req.session_id not in ACTIVE_CONNECTIONS:
        return {"success": False, "error": "Session expired or invalid. Please reconnect."}
    
    conn = ACTIVE_CONNECTIONS[req.session_id]
    try:
        with conn.cursor() as cursor:
            cursor.execute(req.query)
            if cursor.description is None:
                conn.commit()
                return {"success": True, "columns": ["Result"], "rows": [["Statement executed successfully (e.g., DDL/DML)."]]}
            
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchmany(100) # Limit to 100 rows to prevent browser freezing
            return {"success": True, "columns": columns, "rows": rows}
    except Exception as e:
        return {"success": False, "error": str(e)}

def generate_explain_plan(req: DbQueryRequest) -> Dict[str, Any]:
    if req.session_id not in ACTIVE_CONNECTIONS:
        return {"success": False, "error": "Session expired or invalid. Please reconnect."}
    
    conn = ACTIVE_CONNECTIONS[req.session_id]
    try:
        with conn.cursor() as cursor:
            # 1. Generate the plan
            cursor.execute(f"EXPLAIN PLAN FOR {req.query}")
            # 2. Fetch the plan
            cursor.execute("SELECT PLAN_TABLE_OUTPUT FROM TABLE(DBMS_XPLAN.DISPLAY())")
            plan_rows = cursor.fetchall()
            
            # Format output as a single string block
            plan_text = "\n".join([row[0] for row in plan_rows])
            return {"success": True, "plan": plan_text}
    except Exception as e:
        return {"success": False, "error": str(e)}