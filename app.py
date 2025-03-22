from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from assistant import Assistant
import config as conf
from utils import TOOLS
import json
import traceback

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Initialize the assistant with required parameters
assistant = Assistant(
    model=conf.MODEL,
    name="Web Assistant",
    tools=TOOLS,
    system_instruction=conf.get_system_prompt()
)

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

@socketio.on('send_message')
def handle_message(data):
    user_message = data.get('message', '')
    if not user_message:
        emit('response', {'error': 'Message cannot be empty'})
        return
    
    # Start the conversation flow
    try:
        # Phase 1: Reasoning
        emit('reasoning_start')
        reasoning = assistant.get_reasoning(user_message)
        emit('reasoning', {'reasoning': reasoning})
        
        # Add the user message to the assistant's message history
        assistant.messages.append({"role": "user", "content": user_message})
        
        # Create a new message list for execution phase with the reasoning context
        execution_messages = []
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
        
        # Phase 2: Execution with tool handling - don't emit execution_start yet
        # Get first response which might contain tool calls
        response = assistant.get_completion_with_retry(execution_messages)
        
        # Check if there are tool calls before showing execution phase
        response_message = response.choices[0].message
        if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
            emit('execution_start')
        
        process_response_with_tools(response)
        
    except Exception as e:
        traceback.print_exc()
        emit('response', {'error': f"Error processing message: {str(e)}"})

def process_response_with_tools(response):
    """Process a response including any tool calls, sending updates to the client."""
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls if hasattr(response_message, 'tool_calls') else None
    
    # If no tool calls, just return the response
    if not tool_calls:
        assistant.messages.append(response_message)
        emit('response', {'message': response_message.content})
        return
    
    # We have tool calls to process
    emit('thinking', {'content': response_message.content or "Let me process that..."})
    assistant.messages.append(response_message)
    
    # Process each tool call
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        # Emit tool call event
        emit('tool_call', {
            'name': function_name,
            'args': function_args
        })
        
        # Execute the tool
        try:
            function_to_call = assistant.available_functions.get(function_name)
            if not function_to_call:
                emit('tool_error', {
                    'name': function_name,
                    'error': f"Function {function_name} not found"
                })
                assistant.add_toolcall_output(tool_call.id, function_name, f"Function {function_name} not found")
                continue
            
            # Execute the function with converted arguments
            converted_args = {}
            for arg_name, arg_value in function_args.items():
                sig = inspect.signature(function_to_call)
                if arg_name in sig.parameters:
                    param = sig.parameters[arg_name]
                    converted_args[arg_name] = assistant.convert_to_pydantic_model(
                        param.annotation, arg_value
                    )
                else:
                    converted_args[arg_name] = arg_value
            
            # Execute and time the function
            import time
            start_time = time.time()
            result = function_to_call(**converted_args)
            execution_time = time.time() - start_time
            
            # Emit tool result
            emit('tool_result', {
                'name': function_name,
                'result': str(result)[:500] + ('...' if len(str(result)) > 500 else ''),
                'execution_time': round(execution_time, 4)
            })
            
            # Add to assistant's message history
            assistant.add_toolcall_output(tool_call.id, function_name, result)
            
        except Exception as e:
            error_msg = str(e)
            emit('tool_error', {
                'name': function_name, 
                'error': error_msg
            })
            assistant.add_toolcall_output(tool_call.id, function_name, error_msg)
    
    # After processing all tools, get the final response
    try:
        final_response = assistant.get_completion()
        final_message = final_response.choices[0].message
        assistant.messages.append(final_message)
        
        # Check if there are more tool calls
        if hasattr(final_message, 'tool_calls') and final_message.tool_calls:
            # Process additional tool calls recursively
            process_response_with_tools(final_response)
        else:
            # No more tool calls, send the final response
            emit('response', {'message': final_message.content})
            
    except Exception as e:
        emit('response', {'error': f"Error getting final response: {str(e)}"})

# Make sure to import inspect
import inspect

if __name__ == '__main__':
    print(f"Starting Gem-Assist web interface with model: {conf.MODEL}")
    socketio.run(app, debug=True)
