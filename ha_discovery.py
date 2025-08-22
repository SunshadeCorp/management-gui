import json
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SensorDef:
    name: str
    state_topic: str | None = None
    platform: str = 'sensor'
    device_class: str | None = None
    unit: str | None = None
    state_class: str | None = None
    payload_on: str | None = None
    payload_off: str | None = None
    entity_category: str | None = None
    precision: int | None = None


def generate_ha_discovery_payload(sensors: list[SensorDef], dev_id: str, dev_name: str, o_name: str, o_url: str,
                                  av_topic: str, topic_prefix: str) -> str:
    payload: dict[str, dict[str, str | dict[str, str | int]]] = {
        'dev': {  # device
            'ids': dev_id,  # identifiers
            'name': dev_name,
        },
        'o': {  # origin
            'name': o_name,
            'sw': '1.0',  # sw_version
            'url': o_url,  # support_url
        },
        'avty_t': av_topic,  # availability_topic
        'cmps': {}  # components
    }
    for sensor in sensors:
        component: dict[str, str | int] = {
            'p': sensor.platform,  # platform
            'name': sensor.name,
            'uniq_id': f"{payload['dev']['ids']}_{sensor.name}",  # unique_id
            'stat_t': f'{topic_prefix}{sensor.state_topic or sensor.name}',  # state_topic
        }
        if sensor.device_class: component['dev_cla'] = sensor.device_class  # device_class
        if sensor.unit: component['unit_of_meas'] = sensor.unit  # unit_of_measurement
        if sensor.state_class: component['stat_cla'] = sensor.state_class  # state_class
        if sensor.payload_on: component['pl_on'] = sensor.payload_on  # payload_on
        if sensor.payload_off: component['pl_off'] = sensor.payload_off  # payload_off
        if sensor.entity_category: component['ent_cat'] = sensor.entity_category  # entity_category
        if sensor.precision: component['sug_dsp_prc'] = sensor.precision  # suggested_display_precision
        payload['cmps'][sensor.name] = component
    return json.dumps(payload)
