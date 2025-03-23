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

class Message:
    """Represents a message in the chat with its metadata."""
    def __init__(self, role, content, reasoning=None, tool_calls=None, tool_results=None):
        self.role = role
        self.content = content
        self.reasoning = reasoning
        self.tool_calls = tool_calls or []
        self.tool_results = tool_results or []
        self.timestamp = time.time()

class ChatSession:
    """Manages chat session state and assistant instance."""
    def __init__(self):
        self.assistant = Assistant(
            model=conf.MODEL,
            name=conf.NAME,
            tools=TOOLS,
            system_instruction=conf.get_system_prompt()
        )
        self.messages = []  # List of Message objects
        self.current_reasoning = None
        self.current_execution = None
        self.current_tool_calls = []
        self.current_tool_results = []
        self.processing = False
        self.stop_requested = False

    def clear(self):
        """Reset the session state."""
        self.current_reasoning = None
        self.current_execution = None
        self.current_tool_calls = []
        self.current_tool_results = []
        self.stop_requested = False

    def add_message(self, role, content, reasoning=None, tool_calls=None, tool_results=None):
        """Add a message to the session history with metadata."""
        message = Message(
            role=role,
            content=content, 
            reasoning=reasoning,
            tool_calls=tool_calls,
            tool_results=tool_results
        )
        self.messages.append(message)
        
        # Add to assistant's message history for context
        if role != "system":
            self.assistant.messages.append({
                "role": role,
                "content": content
            })

    def start_processing(self):
        """Mark session as processing."""
        self.processing = True
        self.stop_requested = False
        self.current_tool_calls = []
        self.current_tool_results = []

    def stop_processing(self):
        """Request processing to stop."""
        if self.processing:
            self.stop_requested = True
            return True
        return False

    def finish_processing(self):
        """Mark session as done processing."""
        self.processing = False
        self.stop_requested = False

    def get_reasoning(self, message: str) -> str:
        """Get reasoning for the current message."""
        reasoning_messages = []
        reasoning_messages.append({"role": "system", "content": conf.REASONING_SYSTEM_PROMPT})
        
        # Add limited conversation history
        history_limit = 4
        if len(self.assistant.messages) > 1:
            for msg in self.assistant.messages[-history_limit:]:
                if msg["role"] != "system":
                    reasoning_messages.append(msg)
        
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
        """Process message using the two-phase approach."""
        try:
            self.start_processing()
            
            # Store user message first
            self.add_message("user", message)
            
            # Phase 1: Reasoning
            socketio.emit('reasoning_start', room=request_sid)
            if self.stop_requested:
                socketio.emit('processing_stopped', {'phase': 'reasoning'}, room=request_sid)
                return
                
            reasoning = self.get_reasoning(message)
            socketio.emit('reasoning', {'content': reasoning}, room=request_sid)
            self.current_reasoning = reasoning
            
            if self.stop_requested:
                socketio.emit('processing_stopped', {'phase': 'between_phases'}, room=request_sid)
                return
                
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
                
            # Get initial response which may contain tool calls
            response = self.assistant.get_completion_with_retry(execution_messages)
            process_response(response, self, request_sid)
            
        except Exception as e:
            error_msg = f"Error processing message: {e}. Please try again."
            socketio.emit('error', {'message': error_msg}, room=request_sid)
            self.clear()
        finally:
            self.finish_processing()

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
        "SEARCH_TOOLS": ["advanced_duckduckgo_search", "reddit_search", 
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
        
    session = sessions[session_id]
    if session.processing:
        emit('error', {'message': 'Already processing a message'})
        return
        
    session.process_with_tools(user_message, session_id)

@socketio.on('stop_processing')
def handle_stop():
    """Handle request to stop processing."""
    session_id = request.sid
    if session_id in sessions:
        session = sessions[session_id]
        if session.stop_processing():
            emit('processing_stopped', {'phase': 'current'})

def process_response(response, session, request_sid):
    """Process a response including any tool calls."""
    try:
        if session.stop_requested:
            socketio.emit('processing_stopped', {'phase': 'response'}, room=request_sid)
            return
            
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls if hasattr(response_message, 'tool_calls') else None
        
        # Store current tool calls
        if tool_calls:
            session.current_tool_calls.extend([{
                'name': tc.function.name,
                'args': json.loads(tc.function.arguments)
            } for tc in tool_calls])
        
        # Check for personal information
        if not tool_calls and response_message.content:
            if len(session.messages) > 0 and session.messages[-1].role == "user":
                last_user_msg = session.messages[-1].content.lower()
                memory_triggers = ["my name is", "i am", "i like", "i love", "i hate", "i live in", "i work", "you can call me"]
                if any(trigger in last_user_msg for trigger in memory_triggers):
                    socketio.emit('warning', {
                        'message': 'Personal information detected but no memory update performed!'
                    }, room=request_sid)
        
        # If no tool calls, send the response directly
        if not tool_calls:
            session.add_message(
                role="assistant",
                content=response_message.content,
                reasoning=session.current_reasoning,
                tool_calls=session.current_tool_calls,
                tool_results=session.current_tool_results
            )
            
            # Send response to client
            socketio.emit('response', {
                'message': response_message.content,
                'metadata': {
                    'tool_calls_count': len(session.current_tool_calls),
                    'reasoning': session.current_reasoning
                }
            }, room=request_sid)
            return
        
        # Stop if requested before tool execution
        if session.stop_requested:
            socketio.emit('processing_stopped', {'phase': 'tools'}, room=request_sid)
            return
            
        # Add message with all tool calls
        tool_message = {
            "role": "assistant",
            "content": response_message.content,
            "tool_calls": []
        }
        
        # Process each tool call and collect results
        tool_results = []
        
        # Count for status updates
        total_tools = len(tool_calls)
        current_tool = 0
        
        for tool_call in tool_calls:
            current_tool += 1
            socketio.emit('thinking', {
                'content': f'Processing tool {current_tool}/{total_tools}...'
            }, room=request_sid)
            # Add tool call to message
            tool_message["tool_calls"].append({
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments
                }
            })
            
            if session.stop_requested:
                socketio.emit('processing_stopped', {'phase': 'tools'}, room=request_sid)
                return
                
            # Emit thinking on first tool
            if tool_call == tool_calls[0] and response_message.content:
                socketio.emit('thinking', {'content': response_message.content}, room=request_sid)
                
            # Process tool call
            result = process_tool_call(tool_call, session, request_sid)
            tool_results.append({
                "tool_call_id": tool_call.id,
                "name": tool_call.function.name,
                "content": str(result) if result is not None else str(next(
                    (r['error'] for r in session.current_tool_results 
                     if r['name'] == tool_call.function.name and 'error' in r),
                    "Tool call failed"
                ))
            })
        
        # Record all tool interactions
        session.assistant.messages.append(tool_message)
        for result in tool_results:
            session.assistant.messages.append({
                "role": "tool",
                **result
            })

        # Notify client that tool execution is complete
        socketio.emit('thinking', {'content': 'Processing results...'}, room=request_sid)

        # Get final response after tools
        try:
            # Add a reminder and tool results summary before getting final response
            context_message = {
                "role": "system",
                "content": "Previous tools have been executed. Please provide a complete response that addresses the user's question using the tool results above."
            }
            messages_for_final = session.assistant.messages[-10:] + [context_message]
            
            # Get response with complete context
            final_response = session.assistant.get_completion_with_retry(messages=messages_for_final)
            final_message = final_response.choices[0].message
            
            # Verify response
            if not hasattr(final_message, 'content') or not final_message.content:
                final_message = type('obj', (object,), {
                    "content": "I apologize, but I encountered an issue processing all the results. Let me try again with your next request.",
                    "tool_calls": None
                })
                
        except Exception as e:
            print(f"Error getting final response: {e}")
            final_message = type('obj', (object,), {
                "content": "I apologize, but I ran into an issue while processing the results. Let me try to summarize what I found before the error occurred.",
                "tool_calls": None
            })
        
        # Check for more tool calls
        if hasattr(final_message, 'tool_calls') and final_message.tool_calls:
            process_response(final_response, session, request_sid)
        else:
            # Add final response to the conversation
            session.assistant.messages.append(final_message)
            
            # Store the message with metadata for the session
            session.add_message(
                role="assistant",
                content=final_message.content,
                reasoning=session.current_reasoning,
                tool_calls=session.current_tool_calls,
                tool_results=session.current_tool_results
            )
            
            # Send final response to client with all execution data
            final_data = {
                'message': final_message.content,
                'metadata': {
                    'tool_calls_count': len(session.current_tool_calls),
                    'reasoning': session.current_reasoning,
                    'tool_calls': session.current_tool_calls,
                    'tool_results': session.current_tool_results
                }
            }
            socketio.emit('response', final_data, room=request_sid)
            socketio.emit('thinking', {'content': None}, room=request_sid)  # Clear thinking state
            
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
        
        # Stop if requested before tool execution
        if session.stop_requested:
            socketio.emit('processing_stopped', {'phase': 'tool_execution'}, room=request_sid)
            return None
            
        # Execute the tool with retry on rate limit
        for retry in range(3):
            try:
                start_time = time.time()
                result = function_to_call(**converted_args)
                execution_time = time.time() - start_time
                
                # Store tool result
                session.current_tool_results.append({
                    'name': function_name,
                    'result': str(result),
                    'execution_time': execution_time
                })
                
                # Emit result to client
                socketio.emit('tool_result', {
                    'name': function_name,
                    'result': str(result)[:500] + ('...' if len(str(result)) > 500 else ''),
                    'execution_time': round(execution_time, 4)
                }, room=request_sid)
                
                # Tool result will be recorded in the process_response function
                
                return result
                
            except Exception as e:
                if retry < 2 and "rate limit" in str(e).lower():
                    time.sleep(2 ** retry)  # Exponential backoff
                    continue
                raise
                
    except Exception as e:
        error_msg = str(e)
        socketio.emit('tool_error', {
            'name': function_name,
            'error': error_msg
        }, room=request_sid)
        session.current_tool_results.append({
            'name': function_name,
            'error': error_msg
        })
        # Error will be recorded in the process_response function
        return None

if __name__ == '__main__':
    print(f"Starting Gem-Assist web interface with model: {conf.MODEL}")
    socketio.run(app, debug=True)
