# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 CERN.
# Copyright (C) 2021 Northwestern University.
#
# Invenio-Requests is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Service tests."""

from invenio_requests.customizations.event_types import CommentEventType
from invenio_requests.records.api import Request, RequestEvent, RequestEventFormat


def test_submit_request(app, identity_simple, submit_request, request_events_service):
    request = submit_request(identity_simple)
    request_id = request.id
    RequestEvent.index.refresh()

    assert "submitted" == request.status
    results = request_events_service.search(identity_simple, request_id)
    assert 1 == results.total
    hits = list(results.hits)
    assert CommentEventType.type_id == hits[0]["type"]
    assert "Can I belong to the community?" == hits[0]["payload"]["content"]


def test_accept_request(
    app,
    identity_simple,
    identity_simple_2,
    submit_request,
    requests_service,
    request_events_service,
):
    # Submit a request
    request = submit_request(identity_simple)
    request_id = request.id
    # Other user accepts it with comment
    data = {
        "payload": {
            "content": "Welcome to the community!",
            "format": RequestEventFormat.HTML.value,
        }
    }

    result = requests_service.execute_action(
        identity_simple_2, request_id, "accept", data
    )
    request = result._request
    RequestEvent.index.refresh()

    assert "accepted" == request.status
    results = request_events_service.search(identity_simple, request_id)
    assert 3 == results.total  # submit comment + accept event + comment


def test_cancel_request(
    app,
    identity_simple,
    identity_simple_2,
    submit_request,
    requests_service,
    request_events_service,
):
    # Submit a request
    request = submit_request(identity_simple)
    request_id = request.id

    # Cancel it  (no comment is fine)
    result = requests_service.execute_action(identity_simple, request_id, "cancel", {})
    request = result._request

    RequestEvent.index.refresh()

    assert "cancelled" == request.status
    results = request_events_service.search(identity_simple, request_id)
    assert 2 == results.total  # submit comment + cancel event


def test_decline_request(
    app,
    identity_simple,
    identity_simple_2,
    submit_request,
    requests_service,
    request_events_service,
):
    # Submit a request
    request = submit_request(identity_simple)
    request_id = request.id

    data = {
        "payload": {"content": "Sorry but no.", "format": RequestEventFormat.HTML.value}
    }

    # Other user declines it
    result = requests_service.execute_action(
        identity_simple_2, request_id, "decline", data
    )
    request = result._request

    RequestEvent.index.refresh()

    assert "declined" == request.status
    results = request_events_service.search(identity_simple, request_id)
    assert 3 == results.total  # submit comment + decline event + comment


def test_update_request(app, identity_simple, submit_request, requests_service):
    request = submit_request(identity_simple)
    request_id = request.id

    request = requests_service.update(
        identity_simple, request_id, {"title": "Zim boum ba", "type": "default-request"}
    )

    request_dict = request.to_dict()
    assert "Zim boum ba" == request_dict["title"]


def test_search_user_requests(
    app,
    identity_simple,
    identity_simple_2,
    user1,
    submit_request,
    requests_service,
    create_request,
):
    request = submit_request(identity_simple, receiver=user1.user)
    request_id = request.id
    Request.index.refresh()

    # creator can see the requests
    hits = requests_service.search_user_requests(identity_simple).to_dict()["hits"][
        "hits"
    ]

    assert str(request_id) in [h["id"] for h in hits]

    # requests with created status are not returned to the user
    previous_hits = len(hits)
    create_request(identity_simple)
    Request.index.refresh()
    hits = requests_service.search_user_requests(identity_simple).to_dict()["hits"][
        "hits"
    ]

    assert len(hits) == previous_hits

    # others cannot see the request
    hits = requests_service.search_user_requests(identity=identity_simple_2).to_dict()[
        "hits"
    ]["hits"]

    assert str(request_id) not in [h["id"] for h in hits]
