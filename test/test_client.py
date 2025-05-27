import httpx
import asyncio
import json
import base64
import uuid
from typing import Dict, Any, List, Optional

# --- Configuration ---
SERVER_URL = "http://127.0.0.1:8000"
CLIENT_ID = "test_agent_client" # A unique ID for this client instance

# --- Helper Functions for MCP Communication ---

async def send_mcp_request(method: str, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """
    Sends an MCP JSON-RPC request to the server's /mcp/request endpoint.
    """
    url = f"{SERVER_URL}/mcp/request"
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params
    }
    async with httpx.AsyncClient() as client:
        print(f"\n[CLIENT] Sending request (ID: {request_id}, Method: {method}):")
        # print(json.dumps(payload, indent=2)) # Uncomment for full payload debug
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            ack_response = response.json()
            print(f"[CLIENT] Server acknowledged request (ID: {request_id}): {ack_response.get('message', 'No message')}")
            return ack_response
        except httpx.RequestError as e:
            print(f"[CLIENT ERROR] Request failed: {e}")
            raise
        except json.JSONDecodeError:
            print(f"[CLIENT ERROR] Failed to decode JSON response: {response.text}")
            raise
        except Exception as e:
            print(f"[CLIENT ERROR] An unexpected error occurred: {e}")
            raise

async def get_mcp_result(request_id: str, timeout_seconds: int = 300) -> Dict[str, Any]:
    """
    Polls the server's /mcp/result/{request_id} endpoint for the asynchronous task result.
    """
    url = f"{SERVER_URL}/mcp/result/{request_id}"
    start_time = asyncio.get_event_loop().time()

    async with httpx.AsyncClient() as client:
        # Increase initial short delay to give the server more time to finish
        await asyncio.sleep(1.0) # Changed from 0.5 to 1.0 or even 2.0 if needed

        while True:
            if asyncio.get_event_loop().time() - start_time > timeout_seconds:
                print(f"[CLIENT TIMEOUT] Task {request_id} timed out after {timeout_seconds} seconds.")
                raise TimeoutError(f"Task {request_id} did not complete within the timeout.")

            try:
                response = await client.get(url)
                if response.status_code == 202: # HTTP 202 Accepted: Task is still processing
                    print(f"[CLIENT] Polling for result of {request_id}... (still processing)")
                    await asyncio.sleep(5) # Increased polling interval to reduce API calls
                elif response.status_code == 200: # HTTP 200 OK: Result is ready
                    print(f"[CLIENT] Received final result for {request_id}:")
                    result = response.json()
                    # Print the relevant parts of the result for clarity
                    if result.get("result") and result["result"].get("message"):
                        message = result["result"]["message"]
                        print(f"  Role: {message.get('role')}")
                        if message.get("parts"):
                            for part in message["parts"]:
                                if part.get("text"):
                                    print(f"  Text: {part['text']}")
                                if part.get("inline_data"):
                                    print(f"  Inline Data (MIME Type): {part['inline_data']['mime_type']}")
                        if message.get("tool_calls"):
                            print(f"  Tool Calls Suggested: {json.dumps(message['tool_calls'], indent=2)}")
                        if message.get("tool_response"):
                            print(f"  Tool Response: {json.dumps(message['tool_response'], indent=2)}")
                    else:
                        print(json.dumps(result, indent=2)) # Fallback to full dump
                    return result
                elif response.status_code == 404: # Handle 404 gracefully
                    print(f"[CLIENT] Task {request_id} might have completed too quickly or expired on server (404).")
                    # If it's 404 immediately, it likely means the task finished before the client could poll.
                    # For a test client, we'll re-raise for clarity, but in a robust system, you might
                    # log and consider it 'success' if the task is indeed done.
                    response.raise_for_status()
                else:
                    response.raise_for_status() # Raise an exception for other HTTP errors
            except httpx.RequestError as e:
                print(f"[CLIENT ERROR] Polling request failed for {request_id}: {e}")
                await asyncio.sleep(5) # Wait longer on network errors
            except json.JSONDecodeError:
                print(f"[CLIENT ERROR] Failed to decode JSON response during polling: {response.text}")
                raise
            except Exception as e:
                print(f"[CLIENT ERROR] An unexpected error occurred during polling: {e}")
                raise

# --- Main Client Logic ---

async def main():
    print("--- Starting MCP Client Test (Scenario 2 Only) ---")

    # --- Scenario 2: Go to Google, search, and report the first result's URL ---
    print("\n--- Running Scenario 2: Go to Google, search, and report first result's URL ---")
    task_id_2 = str(uuid.uuid4())

    prompt_messages_2: List[Dict[str, Any]] = [
        {
            "role": "user",
            "parts": [
                {"text": "Acting as a human, please complete the following tasks in Zendesk and take screenshots after each step:\n\n1. Navigate to https://saviynt-trialhelp.zendesk.com/admin/people/team/members\n2. Take a screenshot of the login page\n3. Enter username k1980338@gmail.com and password kiran123*\n4. Take a screenshot showing the credentials entered\n5. Click the login button\n6. Take a screenshot of the successful login page\n7. Find and click on the 'Create team member' button\n8. Enter name 'Abhi Kumar' and email 'akumar@example.com'\n9. Take a screenshot of the completed form\n10. Click the 'Next' button\n11. Take a screenshot of the next page\n12. Find the support role dropdown and select 'Contributor' role\n13. Take a screenshot showing the selected role\n14. Click the 'Save' button\n15. Wait 10 seconds for the user to be created in the system\n16. Take a screenshot showing the new user in the team members list\n17. Click on the user menu button and select 'Sign out' from the dropdown\n18. Take a final screenshot of the logout confirmation\n\nPlease describe what you observe on the screen after each action."}
            ]
        }
    ]

    await send_mcp_request(
        "llm_query",
        {"messages": prompt_messages_2, "model_name": "claude-3-5-sonnet-20240620-v1:0"}, # Using a different model to avoid looping
        task_id_2
    )

    await get_mcp_result(task_id_2)

    print("\n--- Scenario 2 Test Finished ---")

if __name__ == "__main__":
    asyncio.run(main())