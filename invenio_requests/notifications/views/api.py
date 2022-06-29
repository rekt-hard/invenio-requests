# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2022 Graz University of Technology.
#
# Invenio-Notifications is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""View functions for the notifications."""


def create_requests_bp(app):
    """Create requests blueprint."""
    ext = app.extensions["invenio-requests"]
    return ext.requests_resource.as_blueprint()


def create_request_events_bp(app):
    """Create request events blueprint."""
    ext = app.extensions["invenio-requests"]
    return ext.request_events_resource.as_blueprint()
