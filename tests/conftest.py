# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 CERN.
# Copyright (C) 2021 Northwestern University.
# Copyright (C) 2021 TU Wien.
# Copyright (C) 2023 Graz University of Technology.
#
# Invenio-Requests is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest configuration.

See https://pytest-invenio.readthedocs.io/ for documentation on which test
fixtures are available.
"""

# Monkey patch Werkzeug 2.1
# Flask-Login uses the safe_str_cmp method which has been removed in Werkzeug
# 2.1. Flask-Login v0.6.0 (yet to be released at the time of writing) fixes the
# issue. Once we depend on Flask-Login v0.6.0 as the minimal version in
# Flask-Security-Invenio/Invenio-Accounts we can remove this patch again.
try:
    # Werkzeug <2.1
    from werkzeug import security

    security.safe_str_cmp
except AttributeError:
    # Werkzeug >=2.1
    import hmac

    from werkzeug import security

    security.safe_str_cmp = hmac.compare_digest

import pytest
from flask_principal import Identity, Need, UserNeed
from flask_security import login_user
from flask_security.utils import hash_password
from invenio_access.models import ActionRoles
from invenio_access.permissions import superuser_access
from invenio_accounts.models import Role
from invenio_accounts.testutils import login_user_via_session
from invenio_app.factory import create_api as _create_api
from invenio_notifications.backends import EmailNotificationBackend
from invenio_notifications.services.builders import NotificationBuilder
from invenio_records_resources.references.entity_resolvers import ServiceResultResolver
from invenio_users_resources.proxies import current_users_service
from invenio_users_resources.records import UserAggregate
from invenio_users_resources.services.schemas import (
    NotificationPreferences,
    UserPreferencesSchema,
    UserSchema,
)
from marshmallow import fields

from invenio_requests.customizations import CommentEventType, LogEventType, RequestType
from invenio_requests.notifications.builders import (
    CommentRequestEventCreateNotificationBuilder,
)


class UserPreferencesNotificationsSchema(UserPreferencesSchema):
    """Schema extending preferences with notification preferences for model validation."""

    notifications = fields.Nested(NotificationPreferences)


class NotificationsUserSchema(UserSchema):
    """Schema for dumping a user with preferences including notifications."""

    preferences = fields.Nested(UserPreferencesNotificationsSchema)


class DummyNotificationBuilder(NotificationBuilder):
    """Dummy builder class to do nothing.

    Specific test cases should override their respective builder to test functionality.
    """

    @classmethod
    def build(cls, **kwargs):
        """Build notification based on type and additional context."""
        return {}


@pytest.fixture(scope="module")
def celery_config():
    """Override pytest-invenio fixture.

    TODO: Remove this fixture if you add Celery support.
    """
    return {}


# @pytest.fixture(scope="module")
# def extra_entry_points():
#     """Extra entry points to load the mock_module features."""
#     return {
#         'invenio_db.model': [
#             'mock_module = mock_module.models',
#         ],
#         'invenio_jsonschemas.schemas': [
#             'mock_module = mock_module.jsonschemas',
#         ],
#         'invenio_search.mappings': [
#             'comments = mock_module.mappings',
#         ]
#     }


@pytest.fixture(scope="module")
def app_config(app_config):
    """Mimic an instance's configuration."""
    app_config["JSONSCHEMAS_HOST"] = "localhost"
    app_config["BABEL_DEFAULT_LOCALE"] = "en"
    # app_config["I18N_LANGUAGES"] = [('da', 'Danish')]
    app_config[
        "RECORDS_REFRESOLVER_CLS"
    ] = "invenio_records.resolver.InvenioRefResolver"
    app_config[
        "RECORDS_REFRESOLVER_STORE"
    ] = "invenio_jsonschemas.proxies.current_refresolver_store"
    app_config["REQUESTS_REGISTERED_TYPES"] = [RequestType()]
    app_config["REQUESTS_REGISTERED_EVENT_TYPES"] = [
        LogEventType(),
        CommentEventType(),
    ]

    app_config["MAIL_DEFAULT_SENDER"] = "test@inveniosoftware.org"

    # Specifying backend for notifications. Only used in specific testcases.
    app_config["NOTIFICATIONS_BACKENDS"] = {
        EmailNotificationBackend.id: EmailNotificationBackend(),
    }

    # Specifying dummy builders to avoid raising errors for most tests. Extend as needed.
    app_config["NOTIFICATIONS_BUILDERS"] = {
        CommentRequestEventCreateNotificationBuilder.type: DummyNotificationBuilder,
    }

    # Specifying default resolvers. Will only be used in specific test cases.
    app_config["NOTIFICATIONS_ENTITY_RESOLVERS"] = [
        ServiceResultResolver(service_id="users", type_key="user"),
        ServiceResultResolver(service_id="requests", type_key="request"),
        ServiceResultResolver(service_id="request_events", type_key="request_event"),
    ]

    # Extending preferences schemas, to include notification preferences. Should not matter for most test cases
    app_config[
        "ACCOUNTS_USER_PREFERENCES_SCHEMA"
    ] = UserPreferencesNotificationsSchema()
    app_config["USERS_RESOURCES_SERVICE_SCHEMA"] = NotificationsUserSchema
    return app_config


@pytest.fixture(scope="module")
def create_app(instance_path):
    """Application factory fixture."""
    return _create_api


@pytest.fixture()
def identity_simple(user1):
    """Simple identity fixture."""
    return user1.identity


@pytest.fixture()
def identity_simple_2(user2):
    """Another simple identity fixture."""
    return user2.identity


@pytest.fixture(scope="module")
def identity_stranger():
    """An unrelated user identity fixture."""
    i = Identity(4)
    i.provides.add(UserNeed(4))
    i.provides.add(Need(method="system_role", value="any_user"))
    return i


# Data layer fixtures
@pytest.fixture(scope="module")
def request_record_input_data():
    """Input data to a Request record."""
    return {"title": "Foo bar", "receiver": {"user": "2"}}


# Resource layer fixtures
@pytest.fixture()
def headers():
    """Default headers for making requests."""
    return {
        "content-type": "application/json",
        "accept": "application/json",
    }


@pytest.fixture(scope="module")
def users(UserFixture, app, database):
    """Users."""
    users = {}
    for r in ["user1", "user2", "user3"]:
        u = UserFixture(
            email=f"{r}@example.org",
            password=r,
            user_profile={
                "full_name": r,
                "affiliations": "CERN",
            },
            preferences={
                "visibility": "public",
                "email_visibility": "restricted",
                "notifications": {
                    "enabled": True,
                },
            },
            active=True,
            confirmed=True,
        )
        u.create(app, database)
        users[r] = u
    # when using `database` fixture (and not `db`), commit the creation of the
    # user because its implementation uses a nested session instead
    database.session.commit()
    current_users_service.indexer.process_bulk_queue()
    current_users_service.record_cls.index.refresh()
    return users


@pytest.fixture()
def user1(users):
    """User 1 for requests."""
    return users["user1"]


@pytest.fixture()
def user2(users):
    """User 2 for requests."""
    return users["user2"]


@pytest.fixture(scope="module")
def superuser(UserFixture, app, database, superuser_role):
    """Admin user for requests."""
    u = UserFixture(
        email="admin@example.org",
        password="admin",
        user_profile={
            "full_name": "admin",
            "affiliations": "CERN",
        },
        preferences={
            "visibility": "public",
            "email_visibility": "restricted",
            "notifications": {
                "enabled": True,
            },
        },
        active=True,
        confirmed=True,
    )
    u.create(app, database)
    u.user.roles.append(superuser_role.role)

    database.session.commit()
    UserAggregate.index.refresh()
    return u


@pytest.fixture(scope="module")
def superuser_role(database):
    """Store 1 role with 'superuser-access' ActionNeed.

    WHY: This is needed because expansion of ActionNeed is
         done on the basis of a User/Role being associated with that Need.
         If no User/Role is associated with that Need (in the DB), the
         permission is expanded to an empty list.
    """
    role = Role(id="superuser-access", name="superuser-access")
    database.session.add(role)

    action_role = ActionRoles.create(action=superuser_access, role=role)
    database.session.add(action_role)

    database.session.commit()

    return action_role


@pytest.fixture()
def example_request(identity_simple, request_record_input_data, user1, user2):
    """Example record."""
    # Need to use the service to get the id I guess...
    from invenio_requests.proxies import current_requests

    requests_service = current_requests.requests_service
    item = requests_service.create(
        identity_simple,
        request_record_input_data,
        RequestType,
        receiver=user2.user,
        creator=user1.user,
    )
    return item._request


@pytest.fixture()
def client_logged_as(client, users, superuser):
    """Logs in a user to the client."""

    def log_user(user_email):
        """Log the user."""
        available_users = list(users.values()) + [superuser]

        user = next((u.user for u in available_users if u.email == user_email), None)
        login_user(user, remember=True)
        login_user_via_session(client, email=user_email)
        return client

    return log_user
