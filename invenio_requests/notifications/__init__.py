# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2022 Graz University of Technology.
#
# Invenio-Notifications is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Invenio module for notifications."""

from .ext import InvenioNotifications
from .proxies import (
    current_notifications, 
    current_notifications_manager,
)

__version__ = "0.1.0"

__all__ = (
    "__version__",
    "current_notifications",
    "current_notifications_manager",
    "InvenioNotifications",
)
