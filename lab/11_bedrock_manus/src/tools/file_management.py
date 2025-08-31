import logging
import json
from typing import Dict, Any
from langchain_community.tools.file_management import WriteFileTool
from .decorators import create_logged_tool, log_io

logger = logging.getLogger(__name__)

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    END = '\033[0m'

# Initialize file management tool with logging
LoggedWriteFile = create_logged_tool(WriteFileTool)
write_file_tool = LoggedWriteFile()

@log_io
def handle_read_file_tool(input_data: Dict[str, Any]) -> str:
    """Read file content from the specified path."""
    if isinstance(input_data, dict):
        file_path = input_data.get('file_path')
    else:
        file_path = input_data
    
    logger.info(f"{Colors.GREEN}===== Reading file: {file_path} ====={Colors.END}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"{Colors.GREEN}===== File read successful ====={Colors.END}")
        return content
    except Exception as e:
        error_msg = f"Failed to read file {file_path}. Error: {repr(e)}"
        # logger.debug(f"{Colors.RED}{error_msg}{Colors.END}")
        return error_msg

@log_io
def handle_write_file_tool(input_data: Dict[str, Any]) -> str:
    """Write content to the specified file path."""
    if isinstance(input_data, dict):
        file_path = input_data.get('file_path')
        content = input_data.get('content')
    else:
        # If input is not a dict, return error
        return "Error: Invalid input format. Expected dict with 'file_path' and 'content'"
    
    logger.info(f"{Colors.GREEN}===== Writing file: {file_path} ====={Colors.END}")
    try:
        # If content is a dict or list, convert to JSON
        if isinstance(content, (dict, list)):
            content = json.dumps(content, indent=2, ensure_ascii=False)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"{Colors.GREEN}===== File write successful ====={Colors.END}")
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        error_msg = f"Failed to write file {file_path}. Error: {repr(e)}"
        # logger.debug(f"{Colors.RED}{error_msg}{Colors.END}")
        return error_msg
