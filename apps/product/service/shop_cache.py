
import hashlib
import json
import logging
import time
import uuid

from django.core.cache import cache


logger = logging.getLogger(__name__)

SHOP_CACHE_PREFIX = "shop:v3"
SHOP_CACHE_VERSION_KEY = "shop:version:v3"
SHOP_CACHE_VERSION_TIMEOUT = None

SHOP_CACHE_TIMEOUT = 45
SHOP_CACHE_LOCK_TIMEOUT = 15
SHOP_CACHE_WAIT_TIMEOUT = 3
SHOP_CACHE_WAIT_INTERVAL = 0.05


def get_shop_cache_version():
    version = cache.get(SHOP_CACHE_VERSION_KEY)

    if version is not None:
        return version

    candidate = uuid.uuid4().hex
    cache.add(
        SHOP_CACHE_VERSION_KEY,
        candidate,
        timeout=SHOP_CACHE_VERSION_TIMEOUT,
    )

    return cache.get(SHOP_CACHE_VERSION_KEY) or candidate


def invalidate_shop_cache():
    """
    Invalidate every versioned shop result without scanning Redis keys.
    """
    cache.set(
        SHOP_CACHE_VERSION_KEY,
        uuid.uuid4().hex,
        timeout=SHOP_CACHE_VERSION_TIMEOUT,
    )


def normalize_shop_params(params):
    normalized = {}

    for key in sorted(params.keys()):
        value = params[key]

        if isinstance(value, (list, tuple)):
            value = sorted(str(item).strip() for item in value)
        else:
            value = str(value).strip()

        normalized[key] = value

    return normalized


def build_shop_cache_key(params):
    payload = json.dumps(
        normalize_shop_params(params),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    version = get_shop_cache_version()

    return f"{SHOP_CACHE_PREFIX}:{version}:{digest}"


def get_or_build_shop_cache(
    params,
    builder,
    timeout=SHOP_CACHE_TIMEOUT,
):
    """
    Redis-backed cache-aside with a distributed fill lock.

    The builder must return a cache-serializable value.
    """
    key = build_shop_cache_key(params)

    cached_value = cache.get(key)

    if cached_value is not None:
        return cached_value, True

    lock_key = f"{key}:fill-lock"
    lock_token = uuid.uuid4().hex

    acquired = cache.add(
        lock_key,
        lock_token,
        timeout=SHOP_CACHE_LOCK_TIMEOUT,
    )

    if not acquired:
        deadline = time.monotonic() + SHOP_CACHE_WAIT_TIMEOUT

        while time.monotonic() < deadline:
            time.sleep(SHOP_CACHE_WAIT_INTERVAL)

            cached_value = cache.get(key)

            if cached_value is not None:
                return cached_value, True

        # Avoid blocking a request indefinitely if the lock owner
        # failed or the Redis lock expired.
        cached_value = cache.get(key)

        if cached_value is not None:
            return cached_value, True

        return builder(), False

    try:
        # Another request may have populated the key while we
        # were acquiring the lock.
        cached_value = cache.get(key)

        if cached_value is not None:
            return cached_value, True

        result = builder()

        # Do not publish a result under a stale version if a
        # model change invalidated the cache during computation.
        expected_key = build_shop_cache_key(params)

        if expected_key == key:
            cache.set(key, result, timeout=timeout)

        return result, False

    finally:
        # Do not delete another worker's lock after our lock expires.
        if cache.get(lock_key) == lock_token:
            cache.delete(lock_key)
