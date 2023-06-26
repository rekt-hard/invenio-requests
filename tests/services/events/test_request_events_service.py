# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 CERN.
# Copyright (C) 2021 Northwestern University.
# Copyright (C) 2023 Graz University of Technology.
#
# Invenio-Requests is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Service tests."""
import copy
from unittest.mock import MagicMock

import pytest
from invenio_access.permissions import system_identity
from invenio_notifications.proxies import current_notifications_manager
from sqlalchemy.exc import NoResultFound

from invenio_requests.customizations import CommentEventType, LogEventType
from invenio_requests.customizations.event_types import EventType
from invenio_requests.notifications.builders import (
    CommentRequestEventCreateNotificationBuilder,
)
from invenio_requests.proxies import current_event_type_registry, current_requests
from invenio_requests.records.api import RequestEvent


def test_schemas(app, example_request):
    events_service = current_requests.request_events_service
    request_id = example_request.id

    class InvalidEventType(EventType):
        """Invalid event type."""

        type_id = "INVALID"

    with pytest.raises(TypeError, match="Event type INVALID is not registered."):
        events_service.create(system_identity, request_id, {}, InvalidEventType)


def test_simple_flow(
    app, identity_simple, events_service_data, create_request, request_events_service
):
    """Interact with comment events."""
    request = create_request(identity_simple)
    request_id = request.id
    comment = events_service_data["comment"]

    # Create a comment
    item = request_events_service.create(
        identity_simple, request_id, dict(**comment), CommentEventType
    )
    item_dict = item.to_dict()

    assert comment["type"] == item_dict["type"]
    assert comment["payload"] == {
        "content": item_dict["payload"]["content"],
        "format": item_dict["payload"]["format"],
    }
    id_ = item.id

    # Read it
    read_item = request_events_service.read(identity_simple, id_)
    assert item.id == read_item.id
    assert item.to_dict() == read_item.to_dict()

    # Update it
    data = read_item.to_dict()  # should be equivalent to comment
    data["payload"]["content"] = "An edited comment"
    updated_item = request_events_service.update(identity_simple, id_, data)
    assert id_ == updated_item.id
    assert "An edited comment" == updated_item.to_dict()["payload"]["content"]

    # Delete it
    deleted_item = request_events_service.delete(identity_simple, id_)
    assert deleted_item is True
    RequestEvent.index.refresh()
    # find the newly created deleted event
    res = request_events_service.search(identity_simple, request_id, sort="newest")
    deleted = list(res.hits)[0]

    assert LogEventType.type_id == deleted["type"]
    assert "comment_deleted" == deleted["payload"]["event"]
    assert "deleted a comment" == deleted["payload"]["content"]
    # Search (batch read) events
    # Let's create a separate request with comment and make sure search is isolated
    data = copy.deepcopy(comment)
    data["payload"]["content"] = "Another comment."
    create_request(identity_simple, data)
    # Refresh to make changes live
    RequestEvent.index.refresh()
    # then search
    searched_items = request_events_service.search(
        identity_simple,
        request_id,
        size=10,
        page=1,
    )
    assert 1 == searched_items.total


def test_delete_non_comment(
    events_service_data, example_request, request_events_service
):
    # Deleting a regular comment empties content and changes type (tested above)
    # Deleting an accept/decline/cancel event removes them
    request_id = example_request.id
    comment = events_service_data["comment"]
    del comment["payload"]

    non_comment_types = [
        t for t in current_event_type_registry if t != CommentEventType
    ]
    for typ in non_comment_types:
        comment["type"] = typ.type_id
        item = request_events_service.create(system_identity, request_id, comment, typ)
        event_id = item.id

        with pytest.raises(PermissionError):
            request_events_service.delete(system_identity, event_id)


def test_cannot_change_event_type(
    identity_simple, events_service_data, example_request
):
    # The `update`` service method can't be used to change the type
    events_service = current_requests.request_events_service
    comment = events_service_data["comment"]

    request_id = example_request.id

    item = events_service.create(identity_simple, request_id, comment, CommentEventType)
    comment_id = item.id
    data = {**comment, "type": LogEventType.type_id}

    updated_event = events_service.update(identity_simple, comment_id, data).to_dict()
    # data aren't changed
    assert updated_event["type"] == CommentEventType.type_id


def test_events_are_searchable(
    app, identity_simple, events_service_data, create_request, request_events_service
):
    """Search all type of events."""
    request = create_request(identity_simple)
    request_id = request.id
    comment = events_service_data["comment"]
    log_event = events_service_data["log"]

    # Create a comment
    request_events_service.create(
        identity_simple, request_id, comment, CommentEventType
    )

    # Create a log event
    request_events_service.create(identity_simple, request_id, log_event, LogEventType)

    # Refresh to make changes live
    RequestEvent.index.refresh()

    # search all events
    searched_items = request_events_service.search(
        identity_simple,
        request_id,
        size=10,
        page=1,
    )
    assert 2 == searched_items.total

    search_comment = list(searched_items.hits)[0]
    assert comment["payload"] == search_comment["payload"]
    assert search_comment["type"] == CommentEventType.type_id
    search_log_event = list(searched_items.hits)[1]
    assert search_log_event["payload"] == log_event["payload"]
    assert search_log_event["type"] == LogEventType.type_id


#
# invenio-notification testcases
#
def test_comment_request_event_notification(
    app,
    events_service_data,
    submit_request,
    request_events_service,
    user1,
    user2,
    superuser,
    monkeypatch,
):
    """Test notifcation being sent on request comment create."""

    original_builder = CommentRequestEventCreateNotificationBuilder

    # mock build to observe calls
    mock_build = MagicMock()
    mock_build.side_effect = original_builder.build
    monkeypatch.setattr(original_builder, "build", mock_build)
    # setting specific builder for test case
    monkeypatch.setattr(
        current_notifications_manager,
        "builders",
        {
            **current_notifications_manager.builders,
            original_builder.type: original_builder,
        },
    )
    assert not mock_build.called

    mail = app.extensions.get("mail")
    assert mail

    request = submit_request(user2.identity, receiver=user1.user)
    request_id = request.id
    comment = events_service_data["comment"]

    with mail.record_messages() as outbox:
        # Create a comment as creator
        request_events_service.create(
            user2.identity, request_id, dict(**comment), CommentEventType
        )

        # check notification is build on create
        assert mock_build.called

        # only request receiver should get notification
        assert len(outbox) == 1
        assert user1.email in outbox[0].recipients
        html = outbox[0].html
        # TODO: update to `req["links"]["self_html"]` when addressing https://github.com/inveniosoftware/invenio-rdm-records/issues/1327
        assert "/me/requests/{}".format(request_id) in html
        assert comment["payload"]["content"] in html

    with mail.record_messages() as outbox:
        # Create a comment as receiver
        request_events_service.create(
            user1.identity, request_id, dict(**comment), CommentEventType
        )

        # check notification is build on create
        assert mock_build.called

        # only request creator should get notification
        assert len(outbox) == 1
        assert user2.email in outbox[0].recipients
        html = outbox[0].html
        # TODO: update to `req["links"]["self_html"]` when addressing https://github.com/inveniosoftware/invenio-rdm-records/issues/1327
        assert "/me/requests/{}".format(request_id) in html
        assert comment["payload"]["content"] in html

    with mail.record_messages() as outbox:
        # Create a comment as superuser
        request_events_service.create(
            superuser.identity, request_id, dict(**comment), CommentEventType
        )

        # check notification is build on create
        assert mock_build.called

        # request creator and receiver should get notifications
        assert len(outbox) == 2
        assert user1.email in outbox[0].recipients
        assert user2.email in outbox[1].recipients
        html = outbox[0].html
        # TODO: update to `req["links"]["self_html"]` when addressing https://github.com/inveniosoftware/invenio-rdm-records/issues/1327
        assert "/me/requests/{}".format(request_id) in html
        assert comment["payload"]["content"] in html
