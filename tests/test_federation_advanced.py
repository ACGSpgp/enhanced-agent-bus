"""
Advanced tests for bilateral audit and policy learning federation phases.
Constitutional Hash: 608508a9bd224290
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from enhanced_agent_bus.federation import GovernanceCapabilityVector
from enhanced_agent_bus.federation.bilateral_audit import (
    BilateralAuditEntry,
    BilateralAuditLog,
    sign_bilateral_entry,
    verify_bilateral_signature,
)
from enhanced_agent_bus.federation.policy_learning import (
    PolicyLearningChannel,
    ViolationSignal,
    apply_differential_privacy,
    compute_violation_signals,
    generate_amendment_suggestions,
)

CONSTITUTIONAL_HASH = "608508a9bd224290"


def _make_bilateral_entry(
    action_summary: str = "Validated bilateral federation handshake",
) -> BilateralAuditEntry:
    base_entry = BilateralAuditEntry(
        local_org_id="org-local",
        peer_org_id="org-peer",
        action_summary=action_summary,
        local_constitutional_hash=CONSTITUTIONAL_HASH,
        peer_constitutional_hash=CONSTITUTIONAL_HASH,
        local_signature="",
        timestamp=1712345678.5,
        entry_id="entry-001",
    )
    return replace(base_entry, local_signature=sign_bilateral_entry(base_entry, b"local-secret"))


def _make_signal(
    category: str = "safety",
    severity: str = "HIGH",
    frequency_bucket: str = "high",
    temporal_trend: str = "stable",
    org_id: str = "",
) -> ViolationSignal:
    return ViolationSignal(
        category=category,
        severity=severity,
        frequency_bucket=frequency_bucket,
        temporal_trend=temporal_trend,
        org_id=org_id,
        window_start=100.0,
        window_end=200.0,
    )


@pytest.mark.asyncio
async def test_bilateral_entry_record_and_retrieve() -> None:
    log = BilateralAuditLog()
    entry = _make_bilateral_entry()

    await log.record(entry)
    entries = await log.get_entries("org-local")

    assert entries == [entry]


@pytest.mark.asyncio
async def test_bilateral_confirm_sets_peer_signature() -> None:
    log = BilateralAuditLog()
    entry = _make_bilateral_entry()
    await log.record(entry)

    confirmed = await log.confirm(entry.entry_id, "peer-signature")
    stored = await log.get_entries("org-peer")

    assert confirmed is True
    assert stored[0].peer_signature == "peer-signature"
    assert stored[0].bilateral_status == "CONFIRMED"


@pytest.mark.asyncio
async def test_bilateral_get_pending_filters() -> None:
    log = BilateralAuditLog()
    pending_entry = _make_bilateral_entry()
    confirmed_entry = _make_bilateral_entry(action_summary="Confirmed")
    await log.record(pending_entry)
    await log.record(replace(confirmed_entry, entry_id="entry-002"))
    await log.confirm("entry-002", "peer-signature")

    pending = await log.get_pending()

    assert pending == [pending_entry]


@pytest.mark.asyncio
async def test_bilateral_mark_failed() -> None:
    log = BilateralAuditLog()
    entry = _make_bilateral_entry()
    await log.record(entry)

    marked = await log.mark_failed(entry.entry_id, "peer validation rejected")
    stored = await log.get_entries("org-local")

    assert marked is True
    assert stored[0].bilateral_status == "FAILED"


def test_bilateral_signature_valid() -> None:
    entry = _make_bilateral_entry()

    assert verify_bilateral_signature(entry, entry.local_signature, b"local-secret") is True


def test_bilateral_signature_tamper_detected() -> None:
    entry = _make_bilateral_entry()
    tampered = replace(entry, action_summary="Leaked raw agent transcript")

    assert verify_bilateral_signature(tampered, entry.local_signature, b"local-secret") is False


def test_bilateral_entry_has_no_raw_agent_data() -> None:
    entry = _make_bilateral_entry()
    entry_dict = entry.to_dict()

    assert "raw_agent_data" not in entry_dict
    assert "matched_content" not in entry_dict
    assert "agent_payload" not in entry_dict
    assert "transcript" not in entry.action_summary.lower()


def test_violation_signal_no_rule_text() -> None:
    signal = _make_signal()
    payload = signal.to_dict()

    assert "rule_id" not in payload
    assert "matched_content" not in payload
    assert "keywords" not in payload
    assert "patterns" not in payload


def test_compute_signals_frequency_buckets() -> None:
    violations: list[dict[str, object]] = []
    base_timestamp = 10_000.0
    violations.extend(
        {"category": "Safety", "severity": "LOW", "timestamp": base_timestamp + index}
        for index in range(3)
    )
    violations.extend(
        {"category": "Privacy", "severity": "HIGH", "timestamp": base_timestamp + 100 + index}
        for index in range(30)
    )
    violations.extend(
        {"category": "Audit", "severity": "CRITICAL", "timestamp": base_timestamp + 200 + index}
        for index in range(100)
    )

    signals = compute_violation_signals(violations, window_hours=1.0)
    buckets = {signal.category: signal.frequency_bucket for signal in signals}

    assert buckets == {"audit": "high", "privacy": "medium", "safety": "low"}


def test_compute_signals_temporal_trend() -> None:
    base_timestamp = 50_000.0
    violations = [
        {"category": "Safety", "severity": "HIGH", "timestamp": base_timestamp - 3000.0},
        {"category": "Safety", "severity": "HIGH", "timestamp": base_timestamp - 2990.0},
        {"category": "Safety", "severity": "HIGH", "timestamp": base_timestamp - 2980.0},
        {"category": "Safety", "severity": "HIGH", "timestamp": base_timestamp - 2970.0},
        {"category": "Audit", "severity": "LOW", "timestamp": base_timestamp},
    ]

    signals = compute_violation_signals(violations, window_hours=1.0)
    safety_signal = next(signal for signal in signals if signal.category == "safety")

    assert safety_signal.temporal_trend == "decreasing"


def test_differential_privacy_changes_some_buckets() -> None:
    signals = [
        _make_signal(category="audit", frequency_bucket="low"),
        _make_signal(category="privacy", frequency_bucket="medium"),
        _make_signal(category="safety", frequency_bucket="high"),
    ]

    privatized = apply_differential_privacy(signals, epsilon=0.5)

    assert any(
        original.frequency_bucket != redacted.frequency_bucket
        for original, redacted in zip(signals, privatized, strict=True)
    )


def test_differential_privacy_high_epsilon_preserves() -> None:
    signals = [
        _make_signal(category="audit", frequency_bucket="low"),
        _make_signal(category="privacy", frequency_bucket="medium"),
        _make_signal(category="safety", frequency_bucket="high"),
    ]

    privatized = apply_differential_privacy(signals, epsilon=10.0)

    assert [signal.frequency_bucket for signal in privatized] == [
        signal.frequency_bucket for signal in signals
    ]


@pytest.mark.asyncio
async def test_publish_and_receive_signals() -> None:
    channel = PolicyLearningChannel()
    signals = [_make_signal()]

    published = await channel.publish_signals(signals, org_id="org-alpha")
    await channel.inject_signals([_make_signal(org_id="org-beta")])
    received = await channel.receive_signals()

    assert published is True
    assert received[0].org_id == "org-beta"


@pytest.mark.asyncio
async def test_channel_disabled_returns_false() -> None:
    channel = PolicyLearningChannel(enabled=False)

    published = await channel.publish_signals([_make_signal()], org_id="org-alpha")

    assert published is False


def test_amendment_suggestions_high_frequency() -> None:
    local_vector = GovernanceCapabilityVector(
        category_severities={"privacy": "LOW"},
        total_rules=1,
        version="1.0",
        org_id="org-local",
    )
    peer_signals = [
        _make_signal(category="privacy", severity="HIGH", org_id="org-a"),
        _make_signal(category="privacy", severity="HIGH", org_id="org-b"),
    ]

    suggestions = generate_amendment_suggestions(local_vector, peer_signals)

    assert len(suggestions) == 1
    assert suggestions[0].category == "privacy"
    assert suggestions[0].suggested_severity == "HIGH"


def test_amendment_suggestions_capped_influence() -> None:
    local_vector = GovernanceCapabilityVector(
        category_severities={},
        total_rules=0,
        version="1.0",
        org_id="org-local",
    )
    peer_signals = [
        _make_signal(category="audit", severity="CRITICAL", org_id=f"org-{index}")
        for index in range(5)
    ]

    suggestions = generate_amendment_suggestions(local_vector, peer_signals, max_peer_influence=0.1)

    assert suggestions[0].confidence == pytest.approx(0.1)


def test_amendment_suggestions_no_suggestion_for_covered() -> None:
    local_vector = GovernanceCapabilityVector(
        category_severities={"audit": "CRITICAL"},
        total_rules=1,
        version="1.0",
        org_id="org-local",
    )
    peer_signals = [_make_signal(category="audit", severity="CRITICAL", org_id="org-a")]

    suggestions = generate_amendment_suggestions(local_vector, peer_signals)

    assert suggestions == []
