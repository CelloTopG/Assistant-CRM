__version__ = "0.0.1"

# Import submodules to make them available
try:
    from . import services
    from . import api
    from . import page
    from . import doctype
    from . import config
except (ImportError, ModuleNotFoundError) as e:
    # Ignore import errors during app installation or when dependencies are not available
    pass

# Create module aliases to fix import issues
import sys
current_module = sys.modules[__name__]

# Make this module importable as assistant_crm.assistant_crm
try:
    # Register this module under the assistant_crm.assistant_crm path
    parent_module_name = __name__.split('.')[0]  # Gets 'assistant_crm'
    if parent_module_name in sys.modules:
        parent_module = sys.modules[parent_module_name]
        # Create the nested reference
        setattr(parent_module, 'assistant_crm', current_module)
        # Also register in sys.modules for direct import
        sys.modules[parent_module_name + '.assistant_crm'] = current_module
except Exception:
    # Ignore any errors during module registration
    pass

# Module initialization complete
