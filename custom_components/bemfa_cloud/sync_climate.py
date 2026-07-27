"""Support for bemfa service."""
from __future__ import annotations
from typing import Any, Final

import logging
from collections.abc import Mapping
import voluptuous as vol

from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_FAN_MODES,
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    ATTR_PRESET_MODE,
    ATTR_SWING_MODE,
    ATTR_SWING_MODES,
    ATTR_PRESET_MODES,
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    SWING_OFF,
    SWING_HORIZONTAL,
    SWING_VERTICAL,
    SWING_BOTH,
    HVACMode,
    DOMAIN,
)

from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from .const import (
    OPTIONS_FAN_SPEED_0_VALUE,
    OPTIONS_FAN_SPEED_1_VALUE,
    OPTIONS_FAN_SPEED_2_VALUE,
    OPTIONS_FAN_SPEED_3_VALUE,
    OPTIONS_FAN_SPEED_4_VALUE,
    OPTIONS_FAN_SPEED_5_VALUE,
    OPTIONS_FAN_SPEED_7_VALUE,
    OPTIONS_FAN_SPEED_8_VALUE,
    OPTIONS_FAN_SPEED_9_VALUE,
    OPTIONS_SWING_OFF_VALUE,
    OPTIONS_SWING_HORIZONTAL_VALUE,
    OPTIONS_SWING_VERTICAL_VALUE,
    OPTIONS_SWING_BOTH_VALUE,
    TopicSuffix,
)
from .utils import has_key
from .sync import (
    SYNC_TYPES,
    CLIMATE_SWING_CONFIG_KEYS,
    CLIMATE_SWING_VALUES,
    ControllableSync,
    UNPUBLISHABLE_STATES,
    _climate_current_swing_axes,
)

_LOGGING = logging.getLogger(__name__)

SUPPORTED_HVAC_MODES = [
    HVACMode.AUTO,
    HVACMode.COOL,
    HVACMode.HEAT,
    HVACMode.FAN_ONLY,
    HVACMode.DRY,
]

ATTR_OPTIONS_NAME: Final = "attr_options_name"
ATTR_NAME: Final = "attr_name"
CFG_KEYS: Final = "cfg_keys"
CFG_VALUES: Final = "cfg_values"
CFG_SUGGESTED = "cfg_suggested"
DETAILS_CFG = [
    {
        ATTR_OPTIONS_NAME: ATTR_FAN_MODES,
        ATTR_NAME: ATTR_FAN_MODE,
        CFG_KEYS: [
            OPTIONS_FAN_SPEED_0_VALUE,
            OPTIONS_FAN_SPEED_1_VALUE,
            OPTIONS_FAN_SPEED_2_VALUE,
            OPTIONS_FAN_SPEED_3_VALUE,
            OPTIONS_FAN_SPEED_4_VALUE,
            OPTIONS_FAN_SPEED_5_VALUE,
            OPTIONS_FAN_SPEED_7_VALUE,
            OPTIONS_FAN_SPEED_8_VALUE,
            OPTIONS_FAN_SPEED_9_VALUE,
        ],
        CFG_VALUES: [0, 1, 2, 3, 4, 5, 7, 8, 9],
        CFG_SUGGESTED: [
            FAN_AUTO,
            FAN_LOW,
            FAN_MEDIUM,
            FAN_HIGH,
            FAN_HIGH,
            FAN_HIGH,
            FAN_LOW,
            FAN_MEDIUM,
            FAN_HIGH,
        ],
    },
    {
        ATTR_OPTIONS_NAME: ATTR_SWING_MODES,
        ATTR_NAME: ATTR_SWING_MODE,
        CFG_KEYS: [
            OPTIONS_SWING_OFF_VALUE,
            OPTIONS_SWING_HORIZONTAL_VALUE,
            OPTIONS_SWING_VERTICAL_VALUE,
            OPTIONS_SWING_BOTH_VALUE,
        ],
        CFG_VALUES: [(0, 0), (1, 0), (0, 1), (1, 1)],
        CFG_SUGGESTED: [SWING_OFF, SWING_HORIZONTAL, SWING_VERTICAL, SWING_BOTH],
    },
]


def _get_detail_value(
    attributes: dict[str, Any], sync_config: dict[str, str], detail_cfg: Any
) -> Any:
    if has_key(attributes, detail_cfg[ATTR_NAME]):
        current_value = attributes[detail_cfg[ATTR_NAME]]
        for i in range(len(detail_cfg[CFG_KEYS])):
            key = detail_cfg[CFG_KEYS][i]
            if key in sync_config and sync_config[key] == current_value:
                return detail_cfg[CFG_VALUES][i]

        if detail_cfg[ATTR_OPTIONS_NAME] == ATTR_FAN_MODES:
            options = attributes.get(detail_cfg[ATTR_OPTIONS_NAME], [])
            if current_value in options:
                if str(current_value).lower() in ("auto", "自动"):
                    return detail_cfg[CFG_VALUES][0]
                option_index = min(
                    options.index(current_value) + 1,
                    len(detail_cfg[CFG_VALUES]) - 1,
                )
                return detail_cfg[CFG_VALUES][option_index]
            if str(current_value).lower() in ("auto", "自动"):
                return detail_cfg[CFG_VALUES][0]
    return detail_cfg[CFG_VALUES][0]


def _bemfa_climate_mode(
    state: str, attributes: Mapping[str, Any]
) -> int | None:
    preset_mode = str(attributes.get(ATTR_PRESET_MODE, "")).lower()
    if preset_mode in ("sleep", "sleep_mode", "睡眠"):
        return 6
    if preset_mode in ("eco", "energy_saving", "节能"):
        return 7
    if state in SUPPORTED_HVAC_MODES:
        return SUPPORTED_HVAC_MODES.index(state) + 1
    return None


@SYNC_TYPES.register("climate")
class Climate(ControllableSync):
    """Sync a hass climate entity to bemfa climate device."""

    @staticmethod
    def get_config_step_id() -> str:
        return "sync_config_climate"

    @staticmethod
    def _get_topic_suffix() -> TopicSuffix:
        return TopicSuffix.CLIMATE

    @staticmethod
    def _supported_domain() -> str:
        return DOMAIN

    @classmethod
    def collect_supported_syncs(cls, hass):
        syncs = []
        for state in hass.states.async_all(cls._supported_domain()):
            hvac_modes = state.attributes.get(ATTR_HVAC_MODES, [])
            if HVACMode.COOL not in hvac_modes:
                continue
            syncs.append(cls(hass, state.entity_id, state.name))
        return syncs

    def generate_details_schema(self) -> dict[str, Any]:
        schema = super().generate_details_schema()
        state = self._hass.states.get(self._entity_id)
        if state is not None:
            for _dc in DETAILS_CFG:
                if _dc[ATTR_OPTIONS_NAME] in state.attributes:
                    options = state.attributes[_dc[ATTR_OPTIONS_NAME]]
                    if options:
                        selector = SelectSelector(
                            SelectSelectorConfig(
                                options=options, mode=SelectSelectorMode.DROPDOWN
                            )
                        )
                        for i in range(len(_dc[CFG_KEYS])):
                            _k = _dc[CFG_KEYS][i]
                            _s = _dc[CFG_SUGGESTED][i]
                            schema[
                                vol.Optional(
                                    _k,
                                    description={
                                        "suggested_value": self._config[_k]
                                        if _k in self._config
                                        and self._config[_k] in options
                                        else _s
                                        if _s in options
                                        else options[0]
                                    },
                                )
                            ] = selector
        return schema

    def _generate_msg_payload(self) -> dict[str, Any]:
        state = self._hass.states.get(self._entity_id)
        if state is None or state.state in UNPUBLISHABLE_STATES:
            return {}

        attributes = state.attributes
        on = state.state != HVACMode.OFF
        payload: dict[str, Any] = {"on": on}

        if not on:
            return payload

        mode = _bemfa_climate_mode(state.state, attributes)
        if mode is not None:
            payload["mode"] = mode

        if has_key(attributes, ATTR_TEMPERATURE):
            payload["t"] = round(attributes[ATTR_TEMPERATURE])

        fan_value = _get_detail_value(attributes, self._config, DETAILS_CFG[0])
        if fan_value is not None:
            payload["fan"] = fan_value

        swing_value = _get_detail_value(attributes, self._config, DETAILS_CFG[1])
        if isinstance(swing_value, tuple) and len(swing_value) == 2:
            l2r, u2d = swing_value
            payload["l2r"] = 360 if l2r else 0
            payload["u2d"] = 360 if u2d else 0

        return payload


@SYNC_TYPES.register("thermostat")
class Thermostat(Climate):
    """Sync a Home Assistant thermostat-like climate to Bemfa thermostat device."""

    @staticmethod
    def get_config_step_id() -> str:
        return "sync_config_thermostat"

    @staticmethod
    def _get_topic_suffix() -> TopicSuffix:
        return TopicSuffix.THERMOSTAT

    @classmethod
    def collect_supported_syncs(cls, hass):
        return [
            cls(hass, state.entity_id, state.name)
            for state in hass.states.async_all(cls._supported_domain())
            if HVACMode.COOL not in state.attributes.get(ATTR_HVAC_MODES, [])
        ]
