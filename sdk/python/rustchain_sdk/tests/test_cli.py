# SPDX-License-Identifier: MIT
"""Unit tests for the RustChain SDK CLI commands."""

import json

import httpx
import pytest
import respx
from click.testing import CliRunner

from rustchain_sdk.cli import main
from rustchain_sdk.client import DEFAULT_NODE_URL
from rustchain_sdk.wallet import RustChainWallet


@pytest.fixture
def runner():
    """Create a Click CLI runner."""
    return CliRunner()


@pytest.fixture
def test_wallet():
    """Create a deterministic test wallet."""
    seed_phrase = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
    words: list[str] = [str(w) for w in seed_phrase.split()]
    wallet = RustChainWallet.from_seed_phrase(words)
    return wallet, seed_phrase


class TestCliAttest:
    """Tests for the `rustchain attest` CLI command."""

    @respx.mock
    def test_attest_executes_full_flow_with_json(self, runner, test_wallet):
        """CLI attest --json runs full challenge-sign-submit flow and outputs json."""
        wallet, seed_phrase = test_wallet

        status_route = respx.get(
            f"{DEFAULT_NODE_URL}/attestation/status?miner_public_key={wallet.public_key_hex}"
        ).mock(
            return_value=httpx.Response(200, json={"status": "registered"})
        )
        challenge_route = respx.post(f"{DEFAULT_NODE_URL}/attestation/challenge").mock(
            return_value=httpx.Response(
                200,
                json={"challenge": "test-challenge-uuid-1234"},
            )
        )
        submit_route = respx.post(f"{DEFAULT_NODE_URL}/attestation/submit").mock(
            return_value=httpx.Response(
                200,
                json={"status": "attested", "miner_public_key": wallet.public_key_hex},
            )
        )

        result = runner.invoke(
            main,
            [
                "attest",
                wallet.address,
                "--seed",
                seed_phrase,
                "--json",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert status_route.called
        assert challenge_route.called
        assert submit_route.called

        parsed = json.loads(result.output)
        assert parsed["status"] == "attested"
        assert parsed["miner_public_key"] == wallet.public_key_hex

    @respx.mock
    def test_attest_executes_full_flow_plain_text(self, runner, test_wallet):
        """CLI attest plain text logs progress steps and final submission result."""
        wallet, seed_phrase = test_wallet

        status_route = respx.get(
            f"{DEFAULT_NODE_URL}/attestation/status?miner_public_key={wallet.public_key_hex}"
        ).mock(
            return_value=httpx.Response(200, json={"status": "registered"})
        )
        challenge_route = respx.post(f"{DEFAULT_NODE_URL}/attestation/challenge").mock(
            return_value=httpx.Response(
                200,
                json={"challenge": "test-challenge-uuid-1234"},
            )
        )
        submit_route = respx.post(f"{DEFAULT_NODE_URL}/attestation/submit").mock(
            return_value=httpx.Response(
                200,
                json={"status": "attested", "miner_public_key": wallet.public_key_hex},
            )
        )

        result = runner.invoke(
            main,
            [
                "attest",
                wallet.address,
                "--seed",
                seed_phrase,
            ],
        )

        assert result.exit_code == 0
        assert status_route.called
        assert challenge_route.called
        assert submit_route.called
        assert "Requesting attestation challenge..." in result.output
        assert "Submitting attestation..." in result.output
        assert "Attestation submitted!" in result.output

    def test_attest_address_mismatch(self, runner, test_wallet):
        """CLI attest exits with code 1 when seed phrase does not match wallet address."""
        _, seed_phrase = test_wallet
        wrong_address = "RTCwrongaddress000000000000000000000000000000"

        result = runner.invoke(
            main,
            [
                "attest",
                wrong_address,
                "--seed",
                seed_phrase,
            ],
        )

        assert result.exit_code == 1
        assert "Address mismatch" in result.output

    @respx.mock
    def test_attest_no_challenge_json(self, runner, test_wallet):
        """CLI attest --json returns structured error when no challenge is received."""
        wallet, seed_phrase = test_wallet

        respx.get(
            f"{DEFAULT_NODE_URL}/attestation/status?miner_public_key={wallet.public_key_hex}"
        ).mock(
            return_value=httpx.Response(200, json={"status": "inactive"})
        )
        respx.post(f"{DEFAULT_NODE_URL}/attestation/challenge").mock(
            return_value=httpx.Response(200, json={"challenge": ""})
        )

        result = runner.invoke(
            main,
            [
                "attest",
                wallet.address,
                "--seed",
                seed_phrase,
                "--json",
            ],
        )

        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["error"] == "No challenge received"
        assert parsed["status"]["status"] == "inactive"

    @respx.mock
    def test_attest_no_challenge_plain(self, runner, test_wallet):
        """CLI attest plain text outputs warning when no challenge is received."""
        wallet, seed_phrase = test_wallet

        respx.get(
            f"{DEFAULT_NODE_URL}/attestation/status?miner_public_key={wallet.public_key_hex}"
        ).mock(
            return_value=httpx.Response(200, json={"status": "inactive"})
        )
        respx.post(f"{DEFAULT_NODE_URL}/attestation/challenge").mock(
            return_value=httpx.Response(200, json={"challenge": ""})
        )

        result = runner.invoke(
            main,
            [
                "attest",
                wallet.address,
                "--seed",
                seed_phrase,
            ],
        )

        assert result.exit_code == 0
        assert "No challenge received" in result.output
