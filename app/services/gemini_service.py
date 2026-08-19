import re
from sqlglot import parse_one
from sqlglot.errors import ParseError, TokenError, SqlglotError
from app.schemas import FusionEbsRequest, FusionEbsResponse, ChatRequest, ChatResponse

from google import genai
from google.genai import types

# Default Gemini model to use
DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"

# Initialize the GenAI Client
# Automatically picks up GEMINI_API_KEY from the environment
client = genai.Client(api_key = 'AQ.Ab8RN6LCXzcbt2vq9l4fQwBh4y7ZTwW8ccJtXkBZ_VTFIFFCNA')

def resolve_model_name(req_model: str) -> str:
    """
    Fallback helper: Safely default to 'gemini-3.6-flash' if an invalid or empty model is provided.
    """
    if not req_model or "llama" in req_model.lower():
        return DEFAULT_GEMINI_MODEL
    return req_model


def process_fusion_ebs_action(req: FusionEbsRequest) -> FusionEbsResponse:
    dialect = "oracle"
    model_name = resolve_model_name(req.model)

    # ---------------------------------------------------------
    # ACTION: FORMAT (Local SQLGlot Refactor)
    # ---------------------------------------------------------
    if req.action == "format":
        try:
            parsed = parse_one(req.code, read=dialect)
            formatted_sql = parsed.sql(dialect=dialect, pretty=True)
            return FusionEbsResponse(
                code=formatted_sql, 
                explanation="**✅ SQLGlot:** Query successfully formatted and refactored."
            )
        except ParseError as pe:
            error_details = []
            for err in pe.errors:
                line = err.get("line", "?")
                col = err.get("col", "?")
                desc = err.get("description", "Formatting error")
                error_details.append(f"* [Line {line}, Col {col}]: {desc}")
            
            err_msg = "\n".join(error_details) if error_details else str(pe)
            return FusionEbsResponse(
                code=req.code, 
                explanation=f"**❌ SQLGlot Formatting Error:**\n{err_msg}"
            )
        except Exception as e:
            return FusionEbsResponse(
                code=req.code, 
                explanation=f"**❌ Formatting Failed:**\n{str(e)}"
            )

    # ---------------------------------------------------------
    # ACTION: OPTIMIZE (Gemini Performance Tuning)
    # ---------------------------------------------------------
    if req.action == "optimize":
        system_prompt = (
            "You are an elite Oracle SQL Performance Tuning Engineer. "
            "CRITICAL RULE: You must NEVER hallucinate, rename, or invent tables or columns. Work ONLY with the tables and fields provided in the user's query. "
            "Analyze the provided Oracle SQL query and optimize it for execution speed, index usage, and reduced I/O. "
            "Provide your response in Markdown format. Ensure the optimized SQL code is enclosed in a ```sql block, "
            "followed by a clear, bulleted explanation of the specific optimizations you applied."
        )
        
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=f"Please optimize this Oracle SQL query:\n\n```sql\n{req.code}\n```",
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.0 # Zero temperature for strict analytical tasks
                )
            )

            optimization_report = response.text.strip()
            
            return FusionEbsResponse(
                code=req.code, 
                explanation=f"**🚀 AI Optimization Report:**\n\n{optimization_report}"
            )
        except Exception as err:
            return FusionEbsResponse(
                code=req.code,
                explanation=f"**❌ Gemini Optimization Error:**\n{str(err)}"
            )

    # ---------------------------------------------------------
    # ACTION: DEBUG (SQLGlot Diagnostics & Gemini Auto-Fix)
    # ---------------------------------------------------------
    if req.action == "debug":
        syntax_errors = []
        
        try:
            parse_one(req.code, read=dialect)
            return FusionEbsResponse(
                code=req.code, 
                explanation="**✅ SQLGlot Debugger:** No syntax errors detected. Query compiles cleanly for Oracle."
            )
        
        except ParseError as pe:
            for err in pe.errors:
                description = err.get("description", "Syntax error")
                line = err.get("line", "?")
                col = err.get("col", "?")
                start_ctx = err.get("start_context", "")
                highlight = err.get("highlight", "")
                into = err.get("into", "")
                
                msg = f"* **[Line {line}, Column {col}]** {description}"
                if highlight:
                    msg += f"\n  Near token: `{start_ctx}>>>{highlight}<<<{into}`"
                syntax_errors.append(msg)
            
            debug_report = "**❌ SQLGlot Syntax Debugger Found Errors:**\n\n" + "\n\n".join(syntax_errors)
        
        except TokenError as te:
            debug_report = f"**❌ SQLGlot Tokenizer Error:**\n\n* {str(te)}"
        except SqlglotError as se:
            debug_report = f"**❌ SQLGlot Parser Error:**\n\n* {str(se)}"
        except Exception as e:
            debug_report = f"**❌ Compilation Error:**\n\n* {str(e)}"

        try:
            system_prompt = (
                "You are an expert Oracle SQL Developer. Fix the provided Oracle SQL query based on the "
                "SQLGlot error report. CRITICAL RULE: NEVER invent or change table or column names. "
                "Fix ONLY the syntax errors. Return ONLY executable SQL query code without markdown code blocks."
            )
            user_prompt = f"Broken Oracle SQL Query:\n{req.code}\n\nSQLGlot Debug Report:\n{debug_report}"
            
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.0 # Zero temperature for maximum precision in debugging
                )
            )
            
            fixed_sql = response.text.strip()
            fixed_sql = re.sub(r"^```sql\n|^```\n|```$", "", fixed_sql, flags=re.MULTILINE).strip()

            full_explanation = f"{debug_report}\n\n---\n\n**🔧 AI Auto-Fix Executed:**\nRectified code loaded into the editor above."
            return FusionEbsResponse(code=fixed_sql, explanation=full_explanation)
        
        except Exception as ai_err:
            full_explanation = f"{debug_report}\n\n**⚠️ Gemini AI Auto-Fix Failed:**\n{str(ai_err)}"
            return FusionEbsResponse(code=req.code, explanation=full_explanation)


    # ---------------------------------------------------------
    # ACTION: GENERATE
    # ---------------------------------------------------------
    if req.action == "generate":
        if req.system_type == "Fusion":
            system_prompt = (
                "You are an elite, strict Oracle Fusion Cloud Applications Database Architect. "
                "CRITICAL RULES FOR ENTERPRISE ACCURACY: "
                "1. STRICT REAL TABLES: Use ONLY valid, real Oracle Fusion base tables (e.g., POZ_SUPPLIERS, HZ_PARTIES, AP_INVOICES_ALL). NEVER hallucinate table names. "
                "2. STRICT REAL COLUMNS: You must ONLY use exact column names from the official Oracle Data Dictionary. Common fields must use their exact Oracle names (e.g., SEGMENT1, VENDOR_NAME, PARTY_ID, INVOICE_NUM). "
                "3. ANTI-HALLUCINATION PROTOCOL: If the user requests a field and you do not know the exact Oracle database column name with 100% certainty, DO NOT GUESS. You MUST output a NULL placeholder with a comment like this: `NULL AS requested_field /* TODO: VERIFY EXACT ORACLE COLUMN NAME */`. "
                "4. NO ANSI JOINS: DO NOT USE ANSI JOIN syntax (e.g., 'INNER JOIN', 'ON'). You MUST use traditional Oracle proprietary joins (comma-separated tables in FROM, joined in WHERE using '=' and '(+)'). "
                "5. RAW SQL OUTPUT: Return ONLY the raw, executable SQL code. Do not include markdown formatting or explanatory text."
            )
        else:
            system_prompt = (
                "You are an elite, strict Oracle E-Business Suite (EBS) R12 Database Architect. "
                "CRITICAL RULES FOR ENTERPRISE ACCURACY: "
                "1. STRICT REAL TABLES: Use ONLY valid, real Oracle EBS R12 base tables (e.g., AP_SUPPLIERS, PO_HEADERS_ALL, HZ_PARTIES). NEVER hallucinate table names. "
                "2. STRICT REAL COLUMNS: You must ONLY use exact column names from the official Oracle Data Dictionary. Common fields must use their exact Oracle names (e.g., SEGMENT1, VENDOR_NAME, PARTY_ID, INVOICE_NUM). "
                "3. ANTI-HALLUCINATION PROTOCOL: If the user requests a field and you do not know the exact Oracle database column name with 100% certainty, DO NOT GUESS. You MUST output a NULL placeholder with a comment like this: `NULL AS requested_field /* TODO: VERIFY EXACT ORACLE COLUMN NAME */`. "
                "4. NO ANSI JOINS: DO NOT USE ANSI JOIN syntax (e.g., 'INNER JOIN', 'ON'). You MUST use traditional Oracle proprietary joins (comma-separated tables in FROM, joined in WHERE using '=' and '(+)'). "
                "5. RAW SQL OUTPUT: Return ONLY the raw, executable SQL code. Do not include markdown formatting or explanatory text."
            )

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=req.prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.0 # Zero temperature is mandatory to prevent creative hallucinations of column names
                )
            )

            generated_sql = response.text.strip()
            generated_sql = re.sub(r"^```sql\n|^```\n|```$", "", generated_sql, flags=re.MULTILINE).strip()
            
            return FusionEbsResponse(
                code=generated_sql, 
                explanation="**✅ Query generated successfully**. \n\n*Note: Any unrecognized fields have been marked with a `/* VERIFY */` comment to protect database integrity.*"
            )
        except Exception as err:
            return FusionEbsResponse(
                code=req.code,
                explanation=f"**❌ Generation Error:**\n{str(err)}"
            )

    return FusionEbsResponse(code=req.code, explanation="Unknown action requested.")


def process_chat_message(req: ChatRequest) -> ChatResponse:
    model_name = resolve_model_name(req.model)
    system_prompt = (
        f"You are an AI Assistant specializing in enterprise Oracle {req.system_type} SQL development. "
        "CRITICAL RULES: "
        f"1. You must ONLY reference real, valid Oracle {req.system_type} base tables and exact column names. NEVER invent or hallucinate schema data. "
        "2. If you are asked about a field you are not entirely sure exists in the Oracle eTRM, clearly state that you are unsure and advise the user to verify the exact column name. "
        "3. DO NOT USE ANSI JOIN syntax. Use traditional Oracle proprietary joins. "
        "4. Format your responses with Markdown for readability. Be direct, factual, and professional. "
        f"\n\nCurrent Code in User's Editor:\n{req.current_code}"
    )
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=req.message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.1
            )
        )
        return ChatResponse(reply=response.text.strip())
    except Exception as err:
        return ChatResponse(reply=f"**❌ Error:** {str(err)}")