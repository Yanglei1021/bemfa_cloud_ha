"""Support for bemfa service."""
from __future__ import annotations

from typing import Any
from homeassistant.components.cover import ATTR_CURRENT_POSITION, DOMAIN

from homeassistant.const import STATE_OPEN
from .const import TopicSuffix
from .utils import has_key
from .sync import SYNC_TYPES, ControllableSync, UNPUBLISHABLE_STATES


@SYNC_TYPES.register("cover")
class Cover(ControllableSync):
    """Sync a hass cover entity to bemfa cover device."""

    @staticmethod
    def get_config_step_id() -> str:
        return "sync_config_cover"

    @staticmethod
    def _get_topic_suffix() -> TopicSuffix:
        return TopicSuffix.COVER

    @staticmethod
    def _supported_domain() -> str:
        return DOMAIN

    def _generate_msg_payload(self) -> dict[str, Any]:
        state = self._hass.states.get(self._entity_id)
        if state is None or state.state in UNPUBLISHABLE_STATES:
            return {}

        attributes = state.attributes
        if has_key(attributes, ATTR_CURRENT_POSITION):
            on = attributes[ATTR_CURRENT_POSITION] != 0
        else:
            on = state.state != "closed"

        payload: dict[str, Any] = {"on": on}
        if has_key(attributes, ATTR_CURRENT_POSITION):
            payload["v"] = attributes[ATTR_CURRENT_POSITION]
        return payload
