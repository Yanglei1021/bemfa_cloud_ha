"""Support for syncing Home Assistant water heaters to Bemfa Cloud."""
from __future__ import annotations

from typing import Any

from homeassistant.components.water_heater import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_OPERATION_MODE,
    DOMAIN,
)
from homeassistant.const import ATTR_TEMPERATURE, STATE_OFF

from .const import TopicSuffix
from .sync import SYNC_TYPES, ControllableSync, UNPUBLISHABLE_STATES
from .utils import has_key


@SYNC_TYPES.register("water_heater")
class WaterHeater(ControllableSync):
    """Sync a Home Assistant water heater to Bemfa water heater device."""

    @staticmethod
    def get_config_step_id() -> str:
        return "sync_config_water_heater"

    @staticmethod
    def _get_topic_suffix() -> TopicSuffix:
        return TopicSuffix.WATER_HEATER

    @staticmethod
    def _supported_domain() -> str:
        return DOMAIN

    def _generate_msg_payload(self) -> dict[str, Any]:
        state = self._hass.states.get(self._entity_id)
        if state is None or state.state in UNPUBLISHABLE_STATES:
            return {}

        attributes = state.attributes
        payload: dict[str, Any] = {"on": state.state != STATE_OFF}
        if has_key(attributes, ATTR_TEMPERATURE) or has_key(
            attributes, ATTR_CURRENT_TEMPERATURE
        ):
            payload["t"] = round(
                attributes.get(ATTR_TEMPERATURE, attributes.get(ATTR_CURRENT_TEMPERATURE))
            )
        if has_key(attributes, ATTR_OPERATION_MODE):
            payload["mode"] = attributes[ATTR_OPERATION_MODE]
        return payload
