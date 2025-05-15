"""
Admin module package for AdvAITelegramBot

Contains functionality for admin-only features such as:
- Statistics and analytics
- User management
- System controls
- Feature toggles
"""

# Import admin-specific modules
from modules.admin.statistics import (
    handle_stats_panel,
    handle_refresh_stats,
    handle_export_stats
)

from modules.admin.user_management import (
    handle_user_management
)

__all__ = [
    'handle_stats_panel',
    'handle_refresh_stats',
    'handle_export_stats',
    'handle_user_management'
] 