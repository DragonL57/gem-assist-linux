# Gem-Assist Utilities Module

This module contains all the utility functions used by the gem-assist package, organized into logical submodules. This structure makes the code more maintainable and easier to navigate.

## Module Structure

- `__init__.py` - Exports all tools and provides a unified interface
- `core.py` - Core utility functions used across the package
- `filesystem.py` - File system operations (listing, reading, writing)
- `network.py` - Network operations (HTTP requests, downloads)
- `system.py` - System operations (command execution, environment)
- `search.py` - Search functionalities (DuckDuckGo, Reddit, Wikipedia)
- `archive.py` - Archive operations (zip/unzip)

## Usage

Import the specific function you need:

```python
from utils import get_current_directory, read_file, http_get_request
```

Or import all tools:

```python
from utils import TOOLS
```

## Platform Compatibility

This module is designed to work on both Windows and Unix-like systems. 
Windows-specific dependencies are optional and will be loaded only when needed.

To install Windows-specific dependencies:

```bash
uv sync --extras windows
```
