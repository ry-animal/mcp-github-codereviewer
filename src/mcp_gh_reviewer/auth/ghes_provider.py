"""Custom OAuth provider for GitHub Enterprise Server."""

from typing import Optional

import httpx
from fastmcp.server.auth.oauth_proxy import OAuthProxy


class GHESTokenVerifier:
    """Token verifier for GitHub Enterprise Server.

    Verifies OAuth tokens by calling the GHES /user endpoint.
    """

    def __init__(
        self,
        ghes_hostname: str,
        required_scopes: list[str] | None = None,
        timeout_seconds: int = 30,
    ):
        """Initialize the token verifier.

        Args:
            ghes_hostname: GHES hostname (e.g., "github.mycompany.com")
            required_scopes: Scopes required for access
            timeout_seconds: HTTP request timeout
        """
        self.ghes_hostname = ghes_hostname
        self.api_base = f"https://{ghes_hostname}/api/v3"
        self.required_scopes = required_scopes or []
        self.timeout_seconds = timeout_seconds

    async def verify_token(self, token: str) -> dict:
        """Verify token by calling GHES user endpoint.

        Args:
            token: OAuth access token to verify

        Returns:
            Dictionary with user information (sub, login, name, email)

        Raises:
            httpx.HTTPStatusError: If token is invalid
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/user",
                headers={"Authorization": f"Bearer {token}"},
                timeout=float(self.timeout_seconds),
            )
            response.raise_for_status()
            user_data = response.json()
            return {
                "sub": str(user_data["id"]),
                "login": user_data["login"],
                "name": user_data.get("name"),
                "email": user_data.get("email"),
            }

    # Required stubs for AuthProvider interface
    def get_middleware(self):
        """Return auth middleware (handled by OAuthProxy)."""
        return None

    def get_routes(self):
        """Return auth routes (handled by OAuthProxy)."""
        return []

    def get_well_known_routes(self):
        """Return well-known routes (handled by OAuthProxy)."""
        return []

    def set_mcp_path(self, path: str):
        """Set MCP path (handled by OAuthProxy)."""
        pass


class GHESProvider(OAuthProxy):
    """OAuth provider for GitHub Enterprise Server.

    Configures OAuthProxy to use GHES OAuth endpoints instead of github.com.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str,
        ghes_hostname: str,
        scopes: Optional[list[str]] = None,
        redirect_path: str = "/auth/callback",
    ):
        """Initialize the GHES OAuth provider.

        Args:
            client_id: OAuth App client ID from GHES
            client_secret: OAuth App client secret from GHES
            base_url: Base URL of this MCP server (for redirect URI)
            ghes_hostname: GHES hostname (e.g., "github.mycompany.com")
            scopes: OAuth scopes to request (defaults to ["repo", "read:user"])
            redirect_path: Path for OAuth callback
        """
        self.ghes_hostname = ghes_hostname
        default_scopes = scopes or ["repo", "read:user"]

        super().__init__(
            upstream_authorization_endpoint=f"https://{ghes_hostname}/login/oauth/authorize",
            upstream_token_endpoint=f"https://{ghes_hostname}/login/oauth/access_token",
            upstream_client_id=client_id,
            upstream_client_secret=client_secret,
            token_verifier=GHESTokenVerifier(
                ghes_hostname=ghes_hostname,
                required_scopes=default_scopes,
            ),
            base_url=base_url,
            redirect_path=redirect_path,
            valid_scopes=default_scopes,
            forward_pkce=True,  # GitHub supports PKCE
            token_endpoint_auth_method="client_secret_post",
        )

    @property
    def api_base_url(self) -> str:
        """Get the GHES API base URL."""
        return f"https://{self.ghes_hostname}/api/v3"
