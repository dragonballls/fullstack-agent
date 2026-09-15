import json

import pytest

from quality_of_life.account_access import (
    AccountAccessError,
    AccountAccessRegistry,
    AccountGrant,
    AccountProvider,
    AccountRisk,
    AccountScope,
    GitHubRepositoryClient,
)


def github_grant() -> AccountGrant:
    return AccountGrant(
        provider=AccountProvider.GITHUB,
        account_id="primary",
        scopes=(AccountScope("repo.fork", "Create a fork", AccountRisk.WRITE),),
    )


def test_write_scope_requires_confirmation() -> None:
    access = AccountAccessRegistry([github_grant()])
    with pytest.raises(AccountAccessError, match="confirmation required"):
        access.require(AccountProvider.GITHUB, "primary", "repo.fork")
    access.require(AccountProvider.GITHUB, "primary", "repo.fork", confirmed=True)


def test_unauthorized_scope_is_rejected() -> None:
    access = AccountAccessRegistry([github_grant()])
    with pytest.raises(AccountAccessError, match="scope not authorized"):
        access.require(AccountProvider.GITHUB, "primary", "repo.delete", confirmed=True)


def test_github_fork_uses_authorized_token_without_logging_or_persisting_it() -> None:
    seen = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {
                    "full_name": "primary/example",
                    "html_url": "https://github.com/primary/example",
                    "clone_url": "https://github.com/primary/example.git",
                }
            ).encode()

    def opener(request, timeout):
        seen["url"] = request.full_url
        seen["auth"] = request.headers["Authorization"]
        seen["timeout"] = timeout
        return FakeResponse()

    access = AccountAccessRegistry([github_grant()])
    client = GitHubRepositoryClient(token_resolver=lambda: "secret-token", opener=opener)
    result = client.fork_repository(
        "https://github.com/source/example.git",
        account_id="primary",
        access=access,
        confirmed=True,
    )

    assert result["full_name"] == "primary/example"
    assert seen["url"] == "https://api.github.com/repos/source/example/forks"
    assert seen["auth"] == "Bearer secret-token"
    assert seen["timeout"] == 20


def test_invalid_repository_is_rejected_before_network_call() -> None:
    access = AccountAccessRegistry([github_grant()])
    client = GitHubRepositoryClient(token_resolver=lambda: "token")
    with pytest.raises(Exception, match="repository must be"):
        client.fork_repository("not-a-repository", account_id="primary", access=access, confirmed=True)
