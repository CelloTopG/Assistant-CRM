# Services for Assistant CRM
# This module contains all service classes and functions for the WCFCB Assistant CRM

# Import main service functions to make them available at module level
try:
    from .reply_service import get_bot_reply, validate_message, log_conversation, detect_intent, generate_response
    from .session_bridge_service import SessionBridgeService
    __all__ = ['get_bot_reply', 'validate_message', 'log_conversation', 'detect_intent', 'generate_response', 'SessionBridgeService']
except (ImportError, ModuleNotFoundError) as e:
    # Handle import errors gracefully during app installation or when frappe is not available
    __all__ = []
