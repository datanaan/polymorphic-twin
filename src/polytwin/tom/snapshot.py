"""Snapshot generation for TwinObjectInternal state.

Creates immutable point-in-time copies of TwinObject state with
content-addressed snapshot IDs for integrity verification.
"""

import hashlib
import json
from copy import deepcopy
from datetime import datetime

from polytwin.tom.domain_models import TwinObjectInternal


def generate_snapshot_id(internal: TwinObjectInternal, ts: datetime) -> str:
    """Generate a deterministic snapshot ID.

    Format: {twin_id}_{timestamp}_{hash}
    The hash is a truncated SHA-256 of the serialised object state,
    providing content-addressed integrity.

    Args:
        internal: The TwinObjectInternal to snapshot.
        ts: Timestamp for the snapshot.

    Returns:
        Snapshot ID string in the format ``{twin_id}_{timestamp}_{hash12}``.
    """
    ts_str = ts.strftime("%Y%m%dT%H%M%S%f")
    data_hash = hashlib.sha256(
        json.dumps(internal.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()[:12]
    return f"{internal.identity.id}_{ts_str}_{data_hash}"


def create_snapshot_data(internal: TwinObjectInternal) -> dict:
    """Create a deep copy snapshot of TwinObjectInternal state.

    The returned dict is fully independent of the original object --
    mutations to either will not affect the other.

    Args:
        internal: The TwinObjectInternal to snapshot.

    Returns:
        A deep-copy dict of the serialised object state.
    """
    return deepcopy(internal.model_dump(mode="json"))
