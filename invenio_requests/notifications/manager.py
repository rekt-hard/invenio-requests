# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2022 Graz University of Technology.
#
# Invenio-Notifications is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Initialization used for notifications."""


from flask import current_app
from invenio_requests.notifications.errors import NotificationBackendAlreadyRegisteredError, NotificationBackendNotFoundError, NotificationTypeNotFoundError
from invenio_requests.notifications.models import Notification


class NotificationManager:

    def __init__(self, config):
        self._config = config
        self._backends = {}
        self._notification_policy = config.notification_policy
        self._init_backends()
        self._validate_policy()

    def _init_backends(self):
        for id, backend_cls in self._config.backends.items():
            backend_cls(self)

    def _validate_policy(self):
        for event_type, event_policy in self._notification_policy.items():
            backend_ids = event_policy.get("backends", [])
            for backend_id in backend_ids:
                if backend_id not in self._backends:
                    raise NotificationBackendNotFoundError(backend_id, type_=event_type)

    def _dispatch_notification(self, notification, backend, **kwargs):
        try:
            extended_notification = backend.extend_notification(notification.dumps(), **kwargs)
            
            # These do not always get logged
            backend.send_notification.apply_async(
                args=[extended_notification],
            )
            backend.send_notification.delay(
                extended_notification,
            )
            
            # This will always get logged
            backend.send_notification(extended_notification)
        except Exception as e:
            current_app.logger.warning(e)
            raise e


    def broadcast(self, notification, **kwargs):
        event_policy = self._notification_policy.get(notification.type)
        if event_policy is None:
            current_app.logger.warning(NotificationTypeNotFoundError(notification.type))
            return
        for backend_id in event_policy.get("backends", []):
            backend = self._backends.get(backend_id)
            if backend is None:
                current_app.logger.warning(NotificationBackendNotFoundError(backend_id, type_=notification.type))
                continue

            self._dispatch_notification(notification, backend, **kwargs)


    def notify(self, notification, backend_id, **kwargs):
        """Set message and notify specific backend.

        Will pass the key for the specific backend to notify.
        """
        backend = self._backends.get(backend_id)
        if backend is None:
            current_app.logger.warning(NotificationBackendNotFoundError(backend_id))
            return

        self._dispatch_notification(notification, backend, **kwargs)

    def register(self, backend):
        if self._backends.get(backend.id) is not None:
            raise NotificationBackendAlreadyRegisteredError(backend.id)
        self._backends[backend.id] = backend

    def deregister(self, backend):
        del self._backends[backend.id]
