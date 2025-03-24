# Gem-assist - A Personal Assistant In Your Terminal

Gem-Assist is a Python-based personal assistant that leverages the power of LLMs like Google's Gemini models to help you with various tasks. It's designed to be versatile and extensible, offering a range of tools to interact with your system and the internet.

## Features

- **Powered by LLM:** Utilizes models like Gemini-2.0-Flash for natural language understanding and generation.
- **Two-Phase Reasoning:** Uses a deliberate two-step process:
  1. **Reasoning Phase:** First plans approach without executing tools
  2. **Execution Phase:** Follows the reasoning plan to execute tools and provide answers
- **In-depth Research:** Performs intelligent search operations optimized to avoid rate limits while gathering comprehensive information.
- **Modular Architecture:** Organized into logical components that are easy to maintain and extend.
- **Tool-based Architecture:** Equipped with a variety of tools for tasks like:
  - Web searching (DuckDuckGo, filtered search)
  - Web content extraction with intelligent rate limit handling
  - File system operations (listing directories, reading/writing files, etc.)
  - Document processing (Excel, PDF, Word files)
  - System information retrieval
  - Reddit interaction
  - Running shell commands
  - Code execution with Python
  - And more!
- **Customizable:** Easily configure the assistant's behavior and extend its capabilities with new tools.
- **Simple Chat Interface:** Interact with the assistant through a straightforward command-line chat interface.
- **Conversation Management:** Save and load previous conversations.
- **Commands:** Supports executing various commands with the `/command` syntax.
- **Intelligent Web Strategy:** Optimized to get rich information while minimizing rate limit issues.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- uv (for dependency management) - [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)
- Google Gemini API key or another supported model - [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey) or check out [docs.litellm.ai/docs/providers/](https://docs.litellm.ai/docs/providers/) for more models

### Installation

1. Clone the repository:

```bash
git clone https://github.com/Fus3n/gem-assist
cd gem-assist
```

2. Install core dependencies using uv:

```bash
uv pip install -e .
```

3. Install optional dependencies based on your needs:

```bash
# For all optional dependencies
uv pip install -e ".[all]"

# Or install specific feature groups
uv pip install -e ".[data-analysis,web-scraping]"

# Available feature groups:
# - data-analysis: pandas, numpy, matplotlib
# - web-scraping: requests, beautifulsoup4
# - dynamic-web: selenium
# - documents: PyPDF2, python-docx
```

These optional dependencies provide enhanced functionality for specific tools. The core functionality will work without them, but certain advanced features may be limited.

4. Set up environment variables:
   - Create a `.env` file in the project root.
   - Add your API key:
     ```
     GEMINI_API_KEY=YOUR_API_KEY # or any other API key with proper key name, if used
     REDDIT_ID=YOUR_REDDIT_CLIENT_ID # (Optional, for Reddit tools)
     REDDIT_SECRET=YOUR_REDDIT_CLIENT_SECRET # (Optional, for Reddit tools)
     ```

### Usage

Run the `main.py` script to start the chat interface:

```bash
uv run main.py
```

Ignore `ollama_assist_old.py`

You can then interact with Gemini by typing commands in the chat. Type `exit`, `quit`, or `bye` to close the chat.

## Configuration

The main configuration file is `config.py`. Here you can customize:

- **`MODEL`**: Choose the Gemini model to use (e.g., `"gemini/gemini-2.0-flash"`, `"gemini/gemini-2.0-pro-exp-02-05"`) for more models checkout: [docs.litellm.ai/docs/providers/](https://docs.litellm.ai/docs/providers/), for local models its recommended to not run really small models.
- **`NAME`**: Set the name of your assistant.
- **`SYSTEM_PROMPT`**: Modify the system prompt to adjust the assistant's personality and instructions.

And more

**Note:** Restart the `main.py` script after making changes to `config.py`.

## Tools

gem-assist comes with a set of built-in tools that you can use in your conversations. These tools are defined in the various utility modules:

- **Web Search:** `web_search` (with integrated content extraction)
- **File System:** `list_dir`, `write_files`, `create_directory`, `copy_file`, `move_file`, `rename_file`, `rename_directory`, `get_file_metadata`, `get_multiple_directory_size`
- **System:** `get_system_info`, `run_shell_command`, `get_current_datetime`, `get_current_directory`, `get_drives`, `get_environment_variable`, `run_parallel_commands` 
- **Web Interaction:** `get_website_text_content` (enhanced with links/images extraction), `http_get_request`, `open_url`, `download_file_from_url`, `extract_structured_data`, `extract_tables_to_dataframes`, `scrape_with_pagination`, `scrape_dynamic_content`
- **Document Processing:** `read_file_content`, `convert_document`, `read_excel_file`, `read_excel_structure`, `read_pdf_text`, `convert_excel_to_format`
- **Code Execution:** `execute_python_code`, `analyze_pandas_dataframe`
- **Reddit:** `reddit_search`, `get_reddit_post`, `reddit_submission_comments`
- **Utility:** `evaluate_math_expression`, `zip_archive_files`, `zip_extract_files`

**And much more!**

## Testing
To run tests, use:
```bash
uv run pytest tests/
```

## Dependencies

The project dependencies are managed by UV and listed in `pyproject.toml`. Key dependencies include:

- `google-genai`
- `ollama`
- `duckduckgo-search`
- `praw`
- `rich`
- `python-dotenv`

## Contributing

All contributions are welcome! Please fork the repository and create a pull request.

## Known Issues

- **Web Interaction:** Web interaction tools may not work as expected due to rate limits and other issues.
- **File download tool:** Might not show progress or filename(if not explicitly provided) correctly if file download endpoint is dynamic

## License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details.

---

**Disclaimer:** This is a personal project and is provided as-is. Use at your own risk.
