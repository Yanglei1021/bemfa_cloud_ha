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

    @classmethod
    def collect_supported_syncs(cls, hass):
        return [
            cls(hass, state.entity_id, state.name)
            for state in hass.states.async_all(cls._supported_domain())
            if not cls._is_switch_only_light(state.attributes)
        ]

    @staticmethod
    def get_config_step_id() -> str:
        return "sync_config_light"

    @staticmethod
    def _get_topic_suffix() -> TopicSuffix:
        return TopicSuffix.LIGHT

    @staticmethod
    def _supported_domain() -> str:
        return DOMAIN

    @staticmethod
    def _is_switch_only_light(attributes: Mapping[str, Any]) -> bool:
        supported_color_modes = attributes.get(ATTR_SUPPORTED_COLOR_MODES)
        return supported_color_modes is not None and set(supported_color_modes) == {
            ColorMode.ONOFF
        }

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
