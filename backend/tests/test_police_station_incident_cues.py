from __future__ import annotations

from app.services.police_station_incident_cues import alleges_arson_or_fire_at_police_station


def test_fired_up_police_thana() -> None:
    assert (
        alleges_arson_or_fire_at_police_station("someone fired up the police thana in ballia")
        is True
    )


def test_set_on_fire() -> None:
    assert (
        alleges_arson_or_fire_at_police_station("they set the thana on fire last night")
        is True
    )


def test_negative_generic_police() -> None:
    assert alleges_arson_or_fire_at_police_station("police did not file my FIR") is False
