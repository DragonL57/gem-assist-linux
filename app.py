from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from assistant import Assistant, SEARCH_TOOLS  # Import SEARCH_TOOLS directly from assistant
import config as conf
from utils import TOOLS
import json
import traceback
import time
from rich.console import Console
from rich.panel import Panel

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Create a comprehensive list of tool categories for better organization and debugging
TOOL_CATEGORIES = {
    "SEARCH_TOOLS": ["advanced_duckduckgo_search", "google_search", "meta_search", "reddit_search", 
                    "search_wikipedia", "get_wikipedia_summary", "get_full_wikipedia_page", "find_tools"],
    "MEDIA_TOOLS": ["get_youtube_transcript"],
    "FILE_TOOLS": ["read_file", "write_files", "list_dir", "find_files", "get_current_directory", 
                  "get_file_metadata", "copy_file", "move_file", "rename_file", "rename_directory", 
                  "create_directory", "get_directory_size", "get_multiple_directory_size", "read_file_content"],
    "WEB_TOOLS": ["get_website_text_content", "http_get_request", "http_post_request", "open_url", 
                 "download_file_from_url"],
    "SYSTEM_TOOLS": ["get_system_info", "run_shell_command", "get_current_datetime", 
                    "evaluate_math_expression", "get_environment_variable"],
    "ARCHIVE_TOOLS": ["zip_archive_files", "zip_extract_files"],
    "MEMORY_TOOLS": ["read_memory", "update_memory", "remove_memory", "summarize_memory", "analyze_user_input"],
    "DOCUMENT_TOOLS": ["convert_document", "read_excel_file", "read_excel_structure", "read_pdf_text", 
                      "convert_excel_to_format"],
    "WEB_SCRAPING_TOOLS": ["extract_structured_data", "extract_tables_to_dataframes", 
                          "scrape_with_pagination", "scrape_dynamic_content"],
    "CODE_EXECUTION_TOOLS": ["execute_python_code", "analyze_pandas_dataframe"]
}

# Initialize the assistant with required parameters - use existing config prompt
assistant = Assistant(
    model=conf.MODEL,
    name="Web Assistant",
    tools=TOOLS,
    system_instruction=conf.get_system_prompt()  # Use the existing system prompt from config
)

# Create a console for formatted terminal output
terminal_console = Console()

# List all available tools for debugging
print(f"Available tools ({len(TOOLS)}):")
for category, tools in TOOL_CATEGORIES.items():
    print(f"- {category}: {len(tools)} tools")
    # Only print detailed tool list in debug mode to avoid cluttering the console
    if conf.DEBUG_MODE:
        for tool in tools:
            print(f"  - {tool}")

# Custom wrapper to intercept tool calls
class WebUIToolHandler:
    def __init__(self, socket):
        self.socket = socket
    
    def handle_tool_call(self, tool_name, tool_args, tool_id):
        # Emit tool call to the client
        self.socket.emit('tool_call', {
            'tool': tool_name,
            'args': tool_args,
            'id': tool_id
        })
    
    def handle_tool_result(self, tool_name, tool_result, execution_time):
        # Emit tool result to the client
        self.socket.emit('tool_result', {
            'tool': tool_name,
            'result': str(tool_result)[:500] + ('...' if len(str(tool_result)) > 500 else ''),
            'execution_time': execution_time
        })

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
    """Return information about available tools to the frontend."""
    return jsonify({
        'categories': TOOL_CATEGORIES,
        'total_tools': len(TOOLS)
    })

@socketio.on('send_message')
def handle_message(data):
    user_message = data.get('message', '')
    if not user_message:
        emit('response', {'error': 'Message cannot be empty'})
        return
    
    # Start the conversation flow
    try:
        print("Starting conversation flow")
        # Phase 1: Reasoning
        emit('reasoning_start')
        reasoning = assistant.get_reasoning(user_message)
        print(f"Got reasoning: {reasoning[:50]}...")
        emit('reasoning', {'reasoning': reasoning})
        
        # Add the user message to the assistant's message history
        assistant.messages.append({"role": "user", "content": user_message})
        
        # Create a new message list for execution phase with the reasoning context
        execution_messages = []
        
        # Use the standard execution prompt from config with the reasoning
        execution_messages.append({
            "role": "system", 
            "content": f"{conf.EXECUTION_SYSTEM_PROMPT}\n\nYour reasoning plan: {reasoning}"
        })
        
        # Add conversation history (except system message)
        for msg in assistant.messages[:-1]:  # Skip the newly added user message
            if msg["role"] != "system":
                execution_messages.append(msg)
        
        # Add the user message again
        execution_messages.append({"role": "user", "content": user_message})
        
        # Phase 2: Execution with tool handling
        # Always emit execution_start to make sure it appears in the UI
        print("Starting execution phase")
        emit('execution_start')
        
        # Get first response which might contain tool calls
        response = assistant.get_completion_with_retry(execution_messages)
        process_response_with_tools(response)
        
    except Exception as e:
        traceback.print_exc()
        emit('response', {'error': f"Error processing message: {str(e)}"})

def process_response_with_tools(response):
    """Process a response including any tool calls, sending updates to the client."""
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls if hasattr(response_message, 'tool_calls') else None
    
    print(f"Processing response with {len(tool_calls) if tool_calls else 0} tool calls")
    
    # If no tool calls, just return the response
    if not tool_calls:
        assistant.messages.append(response_message)
        emit('response', {'message': response_message.content})
        return
    
    # We have tool calls to process
    emit('thinking', {'content': response_message.content or "Let me process that..."})
    
    # Add the message to the assistant's history (once)
    assistant.messages.append(response_message)
    
    # Process each tool call
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        # Display tool call in terminal with rich formatting
        display_tool_call(function_name, function_args)
        
        # Emit tool call event to the client
        print(f"Emitting tool call for {function_name}")
        emit('tool_call', {
            'name': function_name,
            'args': function_args
        })
        
        # Execute the tool
        try:
            function_to_call = assistant.available_functions.get(function_name)
            if not function_to_call:
                error_msg = f"Function {function_name} not found"
                display_tool_error(function_name, error_msg)
                emit('tool_error', {
                    'name': function_name,
                    'error': error_msg
                })
                assistant.add_toolcall_output(tool_call.id, function_name, error_msg)
                continue
            
            # Convert arguments to appropriate types based on annotations
            sig = inspect.signature(function_to_call)
            converted_args = {}
            for param_name, arg_value in function_args.items():
                if param_name in sig.parameters:
                    param = sig.parameters[param_name]
                    converted_args[param_name] = assistant.convert_to_pydantic_model(
                        param.annotation, arg_value
                    )
                else:
                    converted_args[param_name] = arg_value
            
            # Execute and time the function
            start_time = time.time()
            result = function_to_call(**converted_args)
            execution_time = time.time() - start_time
            
            # Display tool result in terminal
            display_tool_result(function_name, result, execution_time)
            
            # Emit tool result to client
            print(f"Emitting tool result for {function_name}")
            emit('tool_result', {
                'name': function_name,
                'result': str(result)[:500] + ('...' if len(str(result)) > 500 else ''),
                'execution_time': round(execution_time, 4)
            })
            
            # Add tool call output to messages - this format is critical for Vertex AI
            assistant.add_toolcall_output(tool_call.id, function_name, result)
            
        except Exception as e:
            error_msg = str(e)
            # Display error in terminal
            display_tool_error(function_name, error_msg)
            
            emit('tool_error', {
                'name': function_name, 
                'error': error_msg
            })
            assistant.add_toolcall_output(tool_call.id, function_name, error_msg)
    
    # After processing all tools, get the final response
    try:
        print("Getting final response after tool calls")
        final_response = assistant.get_completion()
        final_message = final_response.choices[0].message
        
        # Check if there are more tool calls
        if hasattr(final_message, 'tool_calls') and final_message.tool_calls:
            print(f"Found {len(final_message.tool_calls)} more tool calls, processing recursively")
            # Don't append the message here - it will be done in the recursive call
            process_response_with_tools(final_response)
        else:
            # No more tool calls, append the message and send the final response
            assistant.messages.append(final_message)
            print("No more tool calls, sending final response")
            # Display the final response content in terminal 
            terminal_console.print(f"\n[bold green]Final Response:[/] [dim]{final_message.content[:100]}...[/]")
            
            # Enhanced response object with metadata
            emit('response', {
                'message': final_message.content,
                'metadata': {
                    'tool_calls_count': len(tool_calls) if tool_calls else 0,
                    'processing_time': round(time.time() - start_time, 2) if 'start_time' in locals() else 0
                }
            })
            
    except Exception as e:
        traceback.print_exc()
        print(f"Error getting final response: {e}")
        terminal_console.print(f"[bold red]Error getting final response:[/] {e}")
        emit('response', {'error': f"Error getting final response: {str(e)}"})

# Add these helper functions to display tool information in terminal
def display_tool_call(function_name, function_args):
    """Format and display a tool call with its arguments in the terminal."""
    args_display = []
    for arg_name, arg_value in function_args.items():
        if isinstance(arg_value, str) and len(arg_value) > 50:
            # Truncate long string arguments for display
            display_val = f"{arg_value[:47]}..."
        else:
            display_val = str(arg_value)
        args_display.append(f"{arg_name}={display_val}")
    
    args_str = ", ".join(args_display)
    
    terminal_console.print(Panel.fit(
        f"[bold cyan]Tool:[/] [bold]{function_name}[/]\n[cyan]Arguments:[/] {args_str}",
        border_style="cyan",
        title="🔧 TOOL EXECUTION",
        padding=(0, 2)
    ))

def display_tool_result(function_name, result, execution_time):
    """Display the result of a tool execution in the terminal."""
    # For search tools, just show count of results
    if function_name in SEARCH_TOOLS:
        result_count = count_search_results(result)
        terminal_console.print(Panel.fit(
            f"[bold green]✓[/] Completed in {execution_time:.4f}s: received {result_count} results",
            border_style="green",
            title="✅ TOOL RESULT",
            padding=(0, 2)
        ))
    # Special handling for code execution tools
    elif function_name in ["execute_python_code", "analyze_pandas_dataframe"]:
        # For code execution, show success/failure and execution time
        if isinstance(result, dict) and 'success' in result:
            status = "successfully" if result.get('success') else "with errors"
            terminal_console.print(Panel.fit(
                f"[bold {'green' if result.get('success') else 'red'}]✓[/] Code executed {status} in {execution_time:.4f}s",
                border_style="green" if result.get('success') else "red",
                title="✅ CODE EXECUTION" if result.get('success') else "❌ CODE EXECUTION ERROR",
                padding=(0, 2)
            ))
        else:
            # Fallback to standard preview
            brief_response = get_condensed_preview(result)
            terminal_console.print(Panel.fit(
                f"[bold green]✓[/] Completed in {execution_time:.4f}s: {brief_response}",
                border_style="green",
                title="✅ TOOL RESULT",
                padding=(0, 2)
            ))
    else:
        # For non-search tools, show condensed preview
        brief_response = get_condensed_preview(result)
        terminal_console.print(Panel.fit(
            f"[bold green]✓[/] Completed in {execution_time:.4f}s: {brief_response}",
            border_style="green",
            title="✅ TOOL RESULT",
            padding=(0, 2)
        ))

def display_tool_error(function_name, error_message):
    """Display a tool error in the terminal."""
    terminal_console.print(Panel.fit(
        f"[bold red]Error executing {function_name}:[/] {error_message}",
        border_style="red",
        title="❌ TOOL ERROR",
        padding=(0, 2)
    ))

def count_search_results(result):
    """Count the number of results in a search response."""
    result_count = 0
    if isinstance(result, list):
        result_count = len(result)
    elif isinstance(result, dict) and 'pages' in result:
        result_count = len(result.get('pages', []))
    elif isinstance(result, dict):
        # For nested results like meta_search
        for source, results in result.items():
            if isinstance(results, list):
                result_count += len(results)
    return result_count

def get_condensed_preview(result):
    """Get a condensed preview of a result for display."""
    # Convert to string first
    if isinstance(result, (dict, list)):
        try:
            if isinstance(result, dict):
                keys = list(result.keys())[:3]
                return f"Dict with {len(result)} keys: {', '.join(str(k) for k in keys)}{' ...' if len(result) > 3 else ''}"
            else:  # List
                return f"List with {len(result)} items: {str(result[:2])[:40]}{' ...' if len(result) > 2 else ''}"
        except:
            result_str = str(result)
    else:
        result_str = str(result)
    
    # Limit by lines
    lines = result_str.splitlines()
    if len(lines) > 3:
        return "\n".join(lines[:3]) + " ..."
    
    # Limit overall length if it's a single line
    if len(lines) <= 1 and len(result_str) > 100:
        return result_str[:97] + "..."
        
    return result_str

# Add this helper function to validate the message history
def _validate_message_history(messages):
    """
    Validate that all tool calls have corresponding responses.
    This helps prevent the Vertex AI error about function response parts.
    """
    tool_call_ids = set()
    tool_response_ids = set()
    
    for msg in messages:
        # Track tool calls
        if msg.get("role") == "assistant" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_call_ids.add(tool_call.id)
        
        # Track tool responses
        if msg.get("role") == "tool" and "tool_call_id" in msg:
            tool_response_ids.add(msg["tool_call_id"])
    
    # If we find any missing responses, log a warning
    missing = tool_call_ids - tool_response_ids
    if missing:
        print(f"WARNING: Found {len(missing)} tool calls without responses")
        for id in missing:
            print(f"Missing response for tool call ID: {id}")

# Make sure to import inspect
import inspect

if __name__ == '__main__':
    print(f"Starting Gem-Assist web interface with model: {conf.MODEL}")
    socketio.run(app, debug=True)
