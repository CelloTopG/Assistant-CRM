# API endpoints for Assistant CRM - SIMPLIFIED SINGLE DATAFLOW
# This module contains ONLY the simplified chat API endpoint

# Import ONLY the simplified chat API (single dataflow)
try:
    from .simplified_chat import send_message, get_chat_status
    __all__ = [
        'send_message', 'get_chat_status'
    ]
except (ImportError, ModuleNotFoundError) as e:
    # Handle import errors gracefully during app installation or when dependencies are not available
    __all__ = []
