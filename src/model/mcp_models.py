from pydantic import BaseModel, Field, conint
from typing import Any, Dict, List, Optional, Union

class JsonRpcRequest(BaseModel):
    jsonrpc: str="2.0"
    id: Union[str, int]
    method: str
    params: Optional[Dict[str, Any]]=None

class JsonRpcResponse(BaseModel):
    jsonrpc: str="2.0"
    id: Union[str, int]
    result: Optional[Any]=None
    error: Optional[Dict[str, Any]]=None

class JsonRpcNotification(BaseModel):
    jsonrpc: str="2.0"
    id: Union[str, int]
    params: Optional[Dict[str, Any]]=None


class ToolInputSchema(BaseModel):
    type: str="object"
    properties: Dict[str, Any]={}
    required: List[str]=[]

class ToolDefinition(BaseModel):
    name: str
    description:str
    inputSchema: ToolInputSchema

class ToolCallParams(BaseModel):
    toolName:str
    toolArgs:Dict[str, Any]= Field(default_factory=dict)

class ToolOutput(BaseModel):
    output:Any

class ServerCapabilities(BaseModel):
    tools: Optional[Dict[str, Any]]=None


class InlineDataPart(BaseModel):
    mime_type: str
    data: str # Base64 encoded string

class ContentPart(BaseModel):
    text: Optional[str] = None
    inline_data: Optional[InlineDataPart] = None
    # For tool calls, you might add 'function_call' field if you want to
    # explicitly parse and represent tool calls as parts in the client side.
    # function_call: Optional[Dict[str, Any]] = None

class LLMMessage(BaseModel):
    role: str # "user", "assistant", "system", "tool"
    parts: List[ContentPart] # NEW: Use list of parts for multimodal
    tool_calls: Optional[List[Dict[str, Any]]] = None # For tool calls from the model
    tool_response: Optional[Dict[str, Any]] = None # For tool outputs (from the user to the model)
    # name: Optional[str] = None # For naming the tool call context in some LLMs

class LLMQueryParams(BaseModel):
    messages: List[LLMMessage]
    model_name: Optional[str] = None
    # Add other LLM specific parameters here, e.g., temperature, max_tokens, etc.
    # temperature: Optional[float] = None
    # max_tokens: Optional[int] = None

class LLMResponseResult(BaseModel):
    message: LLMMessage
    # usage: Optional[Dict[str, Any]] = None
    # prompt_feedback: Optional[Dict[str, Any]] = None
