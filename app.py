from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from assistant import Assistant
import config as conf
from utils import TOOLS
import json
import traceback
import time
import inspect
from rich.console import Console
import asyncio
from queue import Queue
from threading import Lock

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # TODO: Move to env var
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

class ChatSession:
    """Manages chat session state and assistant instance."""
    def __init__(self):
        self.assistant = Assistant(
            model=conf.MODEL,
            name=conf.NAME,
            tools=TOOLS,
            system_instruction=conf.get_system_prompt()
        )
        self.messages = []
        self.current_reasoning = None
        self.current_execution = None

    def clear(self):
        """Reset the session state."""
        self.messages = []
        self.current_reasoning = None
        self.current_execution = None

    def get_reasoning(self, message: str) -> str:
        """Replicate assistant.py get_reasoning logic."""
        # Create a temporary messages list for the reasoning phase
        reasoning_messages = []
        reasoning_messages.append({"role": "system", "content": conf.REASONING_SYSTEM_PROMPT})
        
        # Add limited conversation history
        history_limit = 4
        if len(self.assistant.messages) > 1:
            for msg in self.assistant.messages[-history_limit:]:
                if msg["role"] != "system":
                    reasoning_messages.append(msg)
        
        # Add the user's new message
        reasoning_messages.append({
            "role": "user", 
            "content": f"TASK: {message}\n\nProvide your step-by-step reasoning plan."
        })
        
        try:
            response = self.assistant.get_completion_with_retry(reasoning_messages)
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error in reasoning phase: {e}. Will try to proceed with execution."

    def process_with_tools(self, message: str, request_sid: str) -> None:
        """Process message using assistant.py's two-phase approach."""
        try:
            # Phase 1: Reasoning
            socketio.emit('reasoning_start', room=request_sid)
            reasoning = self.get_reasoning(message)
            socketio.emit('reasoning', {'content': reasoning}, room=request_sid)
            self.current_reasoning = reasoning
            
            # Phase 2: Execution
            socketio.emit('execution_start', room=request_sid)
            
            # Create execution messages with reasoning context
            execution_messages = []
            execution_messages.append({
                "role": "system",
                "content": f"{conf.EXECUTION_SYSTEM_PROMPT}\n\nYour reasoning plan: {reasoning}"
            })
            
            # Add conversation history (except system message)
            for msg in self.assistant.messages[1:]:
                execution_messages.append(msg)
                
            # Add the user message
            execution_messages.append({"role": "user", "content": message})
            self.assistant.messages.append({"role": "user", "content": message})
            
            # Get initial response which may contain tool calls
            response = self.assistant.get_completion_with_retry(execution_messages)
            process_response(response, self, request_sid)
            
        except Exception as e:
            error_msg = f"Error processing message: {e}. Please try again."
            socketio.emit('error', {'message': error_msg}, room=request_sid)
            self.clear()

# Store active sessions
sessions = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/model-info')
def model_info():
    return jsonify({
        'model': conf.MODEL,
        'name': conf.NAME
    })

@app.route('/tools-info')
def tools_info():
    """Return information about available tools."""
    tool_categories = {
        "SEARCH_TOOLS": ["advanced_duckduckgo_search", "google_search", "meta_search", "reddit_search", 
                        "search_wikipedia", "get_wikipedia_summary", "get_full_wikipedia_page"],
        "FILE_TOOLS": ["read_file", "write_files", "list_dir", "find_files", "read_file_content"],
        "WEB_TOOLS": ["get_website_text_content", "http_get_request", "http_post_request"],
        "SYSTEM_TOOLS": ["get_system_info", "run_shell_command", "get_current_datetime"],
        "CODE_TOOLS": ["execute_python_code", "analyze_pandas_dataframe"]
    }
    return jsonify({
        'categories': tool_categories,
        'total_tools': len(TOOLS)
    })

@socketio.on('connect')
def handle_connect():
    """Handle new client connections."""
    session_id = request.sid
    sessions[session_id] = ChatSession()
    emit('connected', {
        'session_id': session_id,
        'model': conf.MODEL,
        'name': conf.NAME
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Clean up when a client disconnects."""
    if request.sid in sessions:
        del sessions[request.sid]

@socketio.on('send_message')
def handle_message(data):
    """Handle incoming messages using the two-phase approach."""
    session_id = request.sid
    user_message = data.get('message', '')
    
    if not user_message:
        emit('error', {'message': 'Message cannot be empty'})
        return
        
    if session_id not in sessions:
        sessions[session_id] = ChatSession()
        
    # Process the message using the two-phase approach
    session = sessions[session_id]
    session.process_with_tools(user_message, session_id)

def process_response(response, session, request_sid):
    """Process a response including any tool calls."""
    try:
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls if hasattr(response_message, 'tool_calls') else None
        
        # Check for personal information if no tool calls
        if not tool_calls and response_message.content:
            if len(session.assistant.messages) >= 2 and session.assistant.messages[-1]["role"] == "user":
                last_user_msg = session.assistant.messages[-1]["content"].lower()
                memory_triggers = ["my name is", "i am", "i like", "i love", "i hate", "i live in", "i work", "you can call me"]
                
                if any(trigger in last_user_msg for trigger in memory_triggers):
                    socketio.emit('warning', {
                        'message': 'Personal information detected but no memory update performed!'
                    }, room=request_sid)
        
        # If no tool calls, send the response directly
        if not tool_calls:
            session.assistant.messages.append(response_message)
            socketio.emit('response', {
                'message': response_message.content,
                'metadata': {
                    'tool_calls_count': 0,
                    'reasoning': session.current_reasoning
                }
            }, room=request_sid)
            return
        
        # We have tool calls to process
        socketio.emit('thinking', {
            'content': response_message.content or "Processing with tools..."
        }, room=request_sid)
        session.assistant.messages.append(response_message)
        
        # Process each tool call
        for tool_call in tool_calls:
            process_tool_call(tool_call, session, request_sid)
        
        # Get final response after tool calls
        final_response = session.assistant.get_completion_with_retry()
        final_message = final_response.choices[0].message
        
        # Check for more tool calls
        if hasattr(final_message, 'tool_calls') and final_message.tool_calls:
            process_response(final_response, session, request_sid)
        else:
            session.assistant.messages.append(final_message)
            socketio.emit('response', {
                'message': final_message.content,
                'metadata': {
                    'tool_calls_count': len(tool_calls),
                    'reasoning': session.current_reasoning
                }
            }, room=request_sid)
            
    except Exception as e:
        error_msg = str(e)
        traceback.print_exc()
        socketio.emit('error', {
            'message': f"Error processing response: {error_msg}"
        }, room=request_sid)

def process_tool_call(tool_call, session, request_sid):
    """Process a single tool call and emit results to the client."""
    try:
        function_name = tool_call.function.name
        function_to_call = session.assistant.available_functions.get(function_name)
        
        if not function_to_call:
            raise ValueError(f"Tool not found: {function_name}")
        
        # Parse and convert arguments
        function_args = json.loads(tool_call.function.arguments)
        
        # Emit tool call to client
        socketio.emit('tool_call', {
            'name': function_name,
            'args': function_args
        }, room=request_sid)
        
        # Convert arguments based on type annotations
        sig = inspect.signature(function_to_call)
        converted_args = {}
        for param_name, param in sig.parameters.items():
            if param_name in function_args:
                converted_args[param_name] = session.assistant.convert_to_pydantic_model(
                    param.annotation, function_args[param_name]
                )
        
        # Execute the tool with retry on rate limit
        for retry in range(3):
            try:
                start_time = time.time()
                result = function_to_call(**converted_args)
                execution_time = time.time() - start_time
                
                # Emit result to client
                socketio.emit('tool_result', {
                    'name': function_name,
                    'result': str(result)[:500] + ('...' if len(str(result)) > 500 else ''),
                    'execution_time': round(execution_time, 4)
                }, room=request_sid)
                
                session.assistant.add_toolcall_output(tool_call.id, function_name, result)
                return
                
            except Exception as e:
                if retry < 2 and "rate limit" in str(e).lower():
                    time.sleep(2 ** retry)
                    continue
                raise
                
    except Exception as e:
        error_msg = str(e)
        socketio.emit('tool_error', {
            'name': function_name,
            'error': error_msg
        }, room=request_sid)
        session.assistant.add_toolcall_output(tool_call.id, function_name, error_msg)

if __name__ == '__main__':
    print(f"Starting Gem-Assist web interface with model: {conf.MODEL}")
    socketio.run(app, debug=True)
