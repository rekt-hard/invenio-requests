# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2022 Graz University of Technology.
#
# Invenio-Notifications is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Models used for notifications."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

    

@dataclass
class Notification(dict):
    """Notification class."""

    type: str # one of the registered notification types e.g comment_edit, new_invitation etc
    data: dict  # depending on the type. dump of a record, community, etc.
    recipients: list # list of user dumps
    trigger: dict # info about who triggered (and dump thereof), if it was manual or automatic 
    timestamp: str # when the action happened

    def __init__(self, type = "", data = {}, recipients = None, trigger = {}, **kwargs):
        self.type = self["type"] = type
        self.data = self["data"] = data
        self.recipients = self["recipients"] = recipients if recipients else []
        self.trigger = self["trigger"] = trigger
        self.timestamp = self["timestamp"] = datetime.now().isoformat()
        self.update(kwargs)

    def dumps(self):
        # should have a proper dumper defined, to make sure it is serializable for celery
        d = {k:v for k,v in self.items()}
        d.update(self.__dict__)
        return d

    def copy(self):
        return Notification(**self.dumps())
