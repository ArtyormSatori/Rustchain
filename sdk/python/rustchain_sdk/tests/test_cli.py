# SPDX-License-Identifier: MIT
"""Unit tests for the RustChain SDK CLI."""

import json

import httpx
import pytest
import respx
from click.testing import CliRunner

from rustchain_sdk.cli import main
from rustchain_sdk.client import DEFAULT_NODE_URL


@pytest.fixture
def runner():
    """Create a Click CLI runner."""
    return CliRunner()


class TestCliWalletBalance:
    """Tests for the `rustchain wallet balance` CLI command."""

    @respx.mock
    def test_canonical_amount_rtc_displayed(self, runner):
        """CLI renders amount_rtc from canonical node responses."""
        respx.get(f"{DEFAULT_NODE_URL}/wallet/balance").mock(
            return_value=httpx.Response(
                200,
                json={
                    "miner_id": "stmr",
                    "amount_rtc": 21.0,
                    "amount_i64": 21000000,
                },
            )
        )
        result = runner.invoke(main, ["wallet", "balance", "stmr"])
        assert result.exit_code == 0
        assert "Address:  stmr" in result.output
        assert "Balance:  21.0 RTC" in result.output
        assert "Nonce:    0" in result.output

    @respx.mock
    def test_legacy_balance_compatibility(self, runner):
        """CLI maintains compatibility with legacy balance/nonce responses."""
        respx.get(f"{DEFAULT_NODE_URL}/wallet/balance").mock(
            return_value=httpx.Response(
                200,
                json={
                    "address": "RTClegacy123",
                    "balance": 42,
                    "nonce": 3,
                },
            )
        )
        result = runner.invoke(main, ["wallet", "balance", "RTClegacy123"])
        assert result.exit_code == 0
        assert "Address:  RTClegacy123" in result.output
        assert "Balance:  42 RTC" in result.output
        assert "Nonce:    3" in result.output

    @respx.mock
    def test_amount_i64_fallback_when_amount_rtc_missing(self, runner):
        """CLI calculates balance from amount_i64 if amount_rtc and balance are missing."""
        respx.get(f"{DEFAULT_NODE_URL}/wallet/balance").mock(
            return_value=httpx.Response(
                200,
                json={
                    "miner_id": "RTCfallback",
                    "amount_i64": 5000000,
                },
            )
        )
        result = runner.invoke(main, ["wallet", "balance", "RTCfallback"])
        assert result.exit_code == 0
        assert "Address:  RTCfallback" in result.output
        assert "Balance:  5.0 RTC" in result.output

    @respx.mock
    def test_balance_unavailable_when_no_balance_fields(self, runner):
        """CLI shows 'unavailable' when payload carries none of the balance fields."""
        respx.get(f"{DEFAULT_NODE_URL}/wallet/balance").mock(
            return_value=httpx.Response(
                200,
                json={
                    "miner_id": "RTCunknown",
                },
            )
        )
        result = runner.invoke(main, ["wallet", "balance", "RTCunknown"])
        assert result.exit_code == 0
        assert "Address:  RTCunknown" in result.output
        assert "Balance:  unavailable" in result.output

    @respx.mock
    def test_wallet_balance_json_flag(self, runner):
        """CLI outputs raw formatted JSON when --json flag is provided."""
        respx.get(f"{DEFAULT_NODE_URL}/wallet/balance").mock(
            return_value=httpx.Response(
                200,
                json={
                    "miner_id": "stmr",
                    "amount_rtc": 21.0,
                    "amount_i64": 21000000,
                },
            )
        )
        result = runner.invoke(main, ["wallet", "balance", "stmr", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["amount_rtc"] == 21.0
        assert data["amount_i64"] == 21000000
