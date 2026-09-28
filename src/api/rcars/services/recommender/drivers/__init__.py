"""Content-type driver registry."""

from __future__ import annotations

from rcars.services.recommender.drivers.base import ContentTypeDriver

_REGISTRY: dict[str, ContentTypeDriver] = {}


def _register(driver: ContentTypeDriver) -> None:
    for ct in driver.content_types:
        _REGISTRY[ct] = driver


def get_driver(content_type: str) -> ContentTypeDriver:
    """Get the driver for a content type. Raises KeyError if unknown."""
    return _REGISTRY[content_type]


def get_drivers_for_types(content_types: list[str]) -> dict[str, ContentTypeDriver]:
    """Group content types by driver. Returns {category_key: driver}."""
    result: dict[str, ContentTypeDriver] = {}
    for ct in content_types:
        driver = get_driver(ct)
        result[driver.category_key] = driver
    return result


def registered_content_types() -> list[str]:
    """All content types with registered drivers."""
    return list(_REGISTRY.keys())


def _init_drivers() -> None:
    from rcars.services.recommender.drivers.hands_on import HandsOnDriver
    from rcars.services.recommender.drivers.architecture import ArchitectureDriver
    _register(HandsOnDriver())
    _register(ArchitectureDriver())


_init_drivers()
