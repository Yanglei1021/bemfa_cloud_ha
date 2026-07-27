"""Support for bemfa service."""
from __future__ import annotations

from typing import Any
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    DOMAIN,
)
from homeassistant.const import STATE_ON
from .const import TopicSuffix
from .utils import has_key
from .sync import SYNC_TYPES, ControllableSync, UNPUBLISHABLE_STATES


@SYNC_TYPES.register("light")
class Light(ControllableSync):
    """Sync a hass light entity to bemfa light device."""

    @staticmethod
    def get_config_step_id() -> str:
        return "sync_config_light"

    @staticmethod
    def _get_topic_suffix() -> TopicSuffix:
        return TopicSuffix.LIGHT

    @staticmethod
    def _supported_domain() -> str:
        return DOMAIN

    def _generate_msg_payload(self) -> dict[str, Any]:
        state = self._hass.states.get(self._entity_id)
        if state is None or state.state in UNPUBLISHABLE_STATES:
            return {}

        attributes = state.attributes
        payload: dict[str, Any] = {"on": state.state == STATE_ON}
        if has_key(attributes, ATTR_BRIGHTNESS):
            payload["bri"] = round(attributes[ATTR_BRIGHTNESS] / 2.55)
        if has_key(attributes, ATTR_COLOR_TEMP_KELVIN):
            payload["tv"] = attributes[ATTR_COLOR_TEMP_KELVIN]
        elif has_key(attributes, ATTR_RGB_COLOR):
            payload["r"] = attributes[ATTR_RGB_COLOR][0]
            payload["g"] = attributes[ATTR_RGB_COLOR][1]
            payload["b"] = attributes[ATTR_RGB_COLOR][2]
        return payload
