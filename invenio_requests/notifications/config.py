# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2022 Graz University of Technology.
#
# Invenio-Notifications is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Config for notifications."""

from flask_babelex import gettext as _
from invenio_requests.notifications.backends.email.backend import EmailNotificationBackend
from invenio_requests.notifications.models import CommunitySubmissionCreatedEvent, CommunitySubmissionDeclinedEvent, CommunitySubmissionDeletedEvent, CommunitySubmissionEvent, CommunitySubmissionSubmittedEvent
from invenio_requests.services.configurator import ConfiguratorMixin, FromConfig


class NotificationConfig(ConfiguratorMixin):
    backends = FromConfig("NOTIFICATIONS_BACKENDS", {})
    notification_policy = FromConfig("NOTIFICATIONS_NOTIFICATION_POLICY", {})


# NOTIFICATIONS_CONFIG = NotificationConfig

NOTIFICATIONS_BACKENDS = {
    EmailNotificationBackend.id: EmailNotificationBackend,
}

NOTIFICATIONS_DEFAULT_SUBJECT = _("New notification from repository")

NOTIFICATIONS_NOTIFICATION_POLICY = {
    CommunitySubmissionSubmittedEvent.handling_key: {
        'backends': [
            'email',
        ],
    },
    CommunitySubmissionCreatedEvent.handling_key: {
        'backends': [
            'email',
            # 'text',
        ],
    },
    CommunitySubmissionDeclinedEvent.handling_key: {
        'backends': [
            'email',
            # 'text',
        ],
    },
    CommunitySubmissionDeletedEvent.handling_key: {
        'backends': [
            'email',
            # 'text',
        ],
    },
    'comment_created': {
        'backends': [
            'email',
            # 'slack',
        ],
        # 'recipients': []
    },
    'invitation_expired': {
        'backends': []
    },
}
