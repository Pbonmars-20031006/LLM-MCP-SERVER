# main.py

import asyncio
import json
import logging
import base64
import time
import os
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field

from langchain_agent import run_agent_executor_task
from config import EXTERNAL_LLM_MODEL_NAME, EXTERNAL_LLM_API_KEY
from src.playwright.playwright_manager import PlaywrightManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

_pending_requests: Dict[str, asyncio.Future] = {}
_completed_results_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 30

class LLMQueryInput(BaseModel):
    messages: list
    model_name: str = Field(default=EXTERNAL_LLM_MODEL_NAME)

class MCPRequest(BaseModel):
    jsonrpc: str
    id: str
    method: str
    params: Dict[str, Any]

class MCPResponse(BaseModel):
    jsonrpc: str
    id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

# --- Configuration for Playwright and Screenshots ---
HEADLESS_MODE = False
SAVE_SCREENSHOTS_LOCALLY = True
SCREENSHOTS_DIR = "screenshots"

if SAVE_SCREENSHOTS_LOCALLY and not os.path.exists(SCREENSHOTS_DIR):
    os.makedirs(SCREENSHOTS_DIR)
# --- End Configuration ---

async def _run_langchain_agent_task(
    request_id: str,
    messages: list,
    model_name: str,
    future: asyncio.Future
):
    logger.info(f"Starting LangChain Agent task for request_id: {request_id}")
    try:
        final_answer = await run_agent_executor_task(
            prompt_messages=messages,
            external_llm_model_name=model_name,
        )
        response_data = {
            "role": "assistant",
            "parts": [{"text": final_answer}]
        }
        logger.info(f"LangChain Agent task for request_id {request_id} completed successfully.")
        logger.info(f"LangChain Agent Final Result: {final_answer}")
        if not future.done():
            future.set_result(response_data)
            _completed_results_cache[request_id] = {"timestamp": time.time(), "result": response_data}
        else:
            logger.warning(f"Future for {request_id} already done or cancelled.")

    except Exception as e:
        logger.error(f"LangChain Agent task for request_id {request_id} failed: {e}", exc_info=True)
        error_data = {"code": -32000, "message": f"Agent execution failed: {str(e)}"}
        if not future.done():
            future.set_result({"error": error_data})
            _completed_results_cache[request_id] = {"timestamp": time.time(), "result": {"error": error_data}}
        else:
            logger.warning(f"Future for {request_id} already done or cancelled on error.")
    finally:
        if request_id in _pending_requests:
            del _pending_requests[request_id]

# --- REVISED CACHE CLEANUP ---
async def _perform_cleanup_results_cache(request_id: str):
    """Actual cleanup function to be run in a background task."""
    await asyncio.sleep(CACHE_TTL_SECONDS) # Wait for the TTL
    if request_id in _completed_results_cache:
        # Re-check timestamp in case it was updated or already removed
        if time.time() - _completed_results_cache[request_id]["timestamp"] >= CACHE_TTL_SECONDS:
            del _completed_results_cache[request_id]
            logger.info(f"Cleaned up result for request_id {request_id} from cache.")
        else:
            # If the timestamp was recently updated (e.g., accessed again), reschedule cleanup
            # This handles cases where a result is repeatedly accessed.
            pass # No need to reschedule here explicitly, next access will do it.


@app.post("/mcp/request", response_model=MCPResponse)
async def handle_mcp_request(mcp_request: MCPRequest, background_tasks: BackgroundTasks):
    request_id = mcp_request.id
    method = mcp_request.method
    params = mcp_request.params

    if method == "llm_query":
        messages = params.get("messages")
        model_name = params.get("model_name", EXTERNAL_LLM_MODEL_NAME)

        if not messages:
            raise HTTPException(status_code=400, detail="'messages' are required for 'llm_query'.")

        if request_id in _pending_requests:
            raise HTTPException(status_code=409, detail=f"Request with ID {request_id} is already processing.")

        task_future = asyncio.Future()
        _pending_requests[request_id] = task_future

        background_tasks.add_task(
            _run_langchain_agent_task,
            request_id,
            messages,
            model_name,
            task_future
        )

        return MCPResponse(
            jsonrpc="2.0",
            id=request_id,
            message="Request received and processing started."
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported method: {method}")

@app.get("/mcp/result/{request_id}")
async def get_mcp_result(request_id: str, background_tasks: BackgroundTasks):
    if request_id in _completed_results_cache:
        result_data = _completed_results_cache[request_id]["result"]
        # Schedule cleanup only if it hasn't been scheduled recently or if the result is older
        if time.time() - _completed_results_cache[request_id]["timestamp"] >= CACHE_TTL_SECONDS / 2: # Reschedule if accessed in latter half of TTL
            _completed_results_cache[request_id]["timestamp"] = time.time() # Update timestamp on access
            background_tasks.add_task(_perform_cleanup_results_cache, request_id)
        return {"jsonrpc": "2.0", "id": request_id, "result": result_data}
    elif request_id in _pending_requests:
        raise HTTPException(status_code=202, detail="Task is still processing.")
    else:
        logger.warning(f"Request ID {request_id} not found in pending or completed cache (or expired).")
        raise HTTPException(status_code=404, detail="Result not found or has expired.")

@app.on_event("startup")
async def startup_event():
    manager = await PlaywrightManager.get_instance()
    manager.set_config(headless=HEADLESS_MODE, save_screenshots_locally=SAVE_SCREENSHOTS_LOCALLY, screenshots_dir=SCREENSHOTS_DIR)
    await manager.launch_browser()
    logger.info("Playwright browser launched and configured via PlaywrightManager.")

@app.on_event("shutdown")
async def shutdown_event():
    manager = await PlaywrightManager.get_instance()
    await manager.close_browser()
    logger.info("Playwright browser closed via PlaywrightManager.")