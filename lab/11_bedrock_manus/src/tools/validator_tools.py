from typing import Dict, Any, List
from src.tools.python_repl import handle_python_repl_tool
from src.tools.file_management import handle_read_file_tool, handle_write_file_tool
import json
import pandas as pd
from datetime import datetime
import os
from ..utils.common_utils import get_logger

logger = get_logger(__name__)

class OptimizedValidator:
    """
    Performance-optimized validator for large datasets with many calculations
    """
    
    def __init__(self):
        self.data_cache: Dict[str, pd.DataFrame] = {}
        self.validation_results = {}
        
    def load_data_once(self, file_path: str) -> pd.DataFrame:
        """Cache data loading to avoid repeated I/O operations"""
        if file_path not in self.data_cache:
            logger.info(f"📁 Loading data from {file_path}")
            try:
                if file_path.endswith('.csv'):
                    self.data_cache[file_path] = pd.read_csv(file_path)
                elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                    self.data_cache[file_path] = pd.read_excel(file_path)
                else:
                    # Try CSV as default
                    self.data_cache[file_path] = pd.read_csv(file_path)
                    
                logger.info(f"✅ Loaded {len(self.data_cache[file_path])} rows from {file_path}")
            except Exception as e:
                logger.error(f"❌ Failed to load data from {file_path}: {e}")
                raise
        return self.data_cache[file_path]
    
    def filter_calculations_by_priority(self, calculations: List[Dict]) -> tuple:
        """
        Filter calculations by importance to optimize processing time
        Returns: (filtered_calculations, stats)
        """
        high_priority = [calc for calc in calculations if calc.get('importance') == 'high']
        medium_priority = [calc for calc in calculations if calc.get('importance') == 'medium']
        low_priority = [calc for calc in calculations if calc.get('importance') == 'low']
        
        # Performance optimization: limit processing based on total count
        total_calcs = len(calculations)
        
        if total_calcs > 50:
            # For large datasets, prioritize aggressively
            priority_calcs = high_priority + medium_priority[:min(10, len(medium_priority))]
            logger.info(f"🔧 Large dataset detected ({total_calcs} calculations). Using aggressive filtering.")
        elif total_calcs > 20:
            # Medium datasets, moderate filtering
            priority_calcs = high_priority + medium_priority[:min(15, len(medium_priority))]
            logger.info(f"🔧 Medium dataset detected ({total_calcs} calculations). Using moderate filtering.")
        else:
            # Small datasets, validate most calculations
            priority_calcs = high_priority + medium_priority + low_priority[:5]
            logger.info(f"🔧 Small dataset detected ({total_calcs} calculations). Validating most calculations.")
        
        stats = {
            'total': total_calcs,
            'high': len(high_priority),
            'medium': len(medium_priority),
            'low': len(low_priority),
            'selected': len(priority_calcs)
        }
        
        return priority_calcs, stats

tool_list = [
    {
        "toolSpec": {
            "name": "python_repl_tool",
            "description": "Use this to execute python code for calculation validation and verification. Print output with `print(...)` to display results.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The python code to execute for validation, re-calculation, or verification."
                        }
                    },
                    "required": ["code"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "read_file_tool",
            "description": "Use this to read files like calculation_metadata.json, data files, or analysis results.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file to read"
                        }
                    },
                    "required": ["file_path"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "write_file_tool",
            "description": "Use this to write validation results, citations.json, or validation reports.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path where to write the file"
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write to the file"
                        }
                    },
                    "required": ["file_path", "content"]
                }
            }
        }
    }
]

def process_validator_tool(tool) -> str:
    """Process tool calls for the validator agent.
    
    Args:
        tool: Tool invocation dictionary containing name, input, and toolUseId
        
    Returns:
        Result of the tool invocation as a properly formatted message
    """
    
    tool_name, tool_input = tool["name"], tool["input"]
    
    if tool_name == "python_repl_tool":
        results = handle_python_repl_tool(code=tool_input["code"])
        tool_result = {
            "toolUseId": tool['toolUseId'],
            "content": [{"json": {"text": results}}]
        }
    elif tool_name == "read_file_tool":
        results = handle_read_file_tool(tool_input)
        tool_result = {
            "toolUseId": tool['toolUseId'],
            "content": [{"json": {"text": results}}]
        }
    elif tool_name == "write_file_tool":
        results = handle_write_file_tool(tool_input)
        tool_result = {
            "toolUseId": tool['toolUseId'],
            "content": [{"json": {"text": results}}]
        }
    else:
        print(f"Unknown tool: {tool_name}")
        results = f"Error: Unknown tool '{tool_name}'"
        tool_result = {
            "toolUseId": tool['toolUseId'],
            "content": [{"json": {"text": results}}]
        }
        
    results = {"role": "user","content": [{"toolResult": tool_result}]}
    
    return results

# Tool configuration for the validator agent
validator_tool_config = {
    "tools": tool_list,
    "toolChoice": {"auto": {}}
}