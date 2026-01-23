"""Tests for security utilities."""

from uuid import uuid4

from src.utils.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
    verify_refresh_token,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password_returns_hash(self) -> None:
        """Hash password should return a bcrypt hash."""
        password = "mypassword123"
        hashed = hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self) -> None:
        """Verify password should return True for correct password."""
        password = "mypassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self) -> None:
        """Verify password should return False for incorrect password."""
        hashed = hash_password("mypassword123")

        assert verify_password("wrongpassword", hashed) is False

    def test_hash_is_unique(self) -> None:
        """Each hash should be unique due to salt."""
        password = "mypassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestRefreshToken:
    """Tests for refresh token functions."""

    def test_generate_refresh_token_length(self) -> None:
        """Generated token should be URL-safe and have sufficient entropy."""
        token = generate_refresh_token()

        # 32 bytes base64-encoded is ~43 characters
        assert len(token) >= 40

    def test_generate_refresh_token_unique(self) -> None:
        """Each generated token should be unique."""
        tokens = [generate_refresh_token() for _ in range(10)]

        assert len(set(tokens)) == 10

    def test_hash_refresh_token(self) -> None:
        """Hash refresh token should return bcrypt hash."""
        token = generate_refresh_token()
        hashed = hash_refresh_token(token)

        assert hashed != token
        assert hashed.startswith("$2b$")

    def test_verify_refresh_token_correct(self) -> None:
        """Verify refresh token should return True for correct token."""
        token = generate_refresh_token()
        hashed = hash_refresh_token(token)

        assert verify_refresh_token(token, hashed) is True

    def test_verify_refresh_token_incorrect(self) -> None:
        """Verify refresh token should return False for incorrect token."""
        token = generate_refresh_token()
        hashed = hash_refresh_token(token)
        other_token = generate_refresh_token()

        assert verify_refresh_token(other_token, hashed) is False


class TestAccessToken:
    """Tests for JWT access token functions."""

    def test_create_access_token(self) -> None:
        """Create access token should return a JWT string."""
        user_id = uuid4()
        token = create_access_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 0
        # JWT has 3 parts separated by dots
        assert token.count(".") == 2

    def test_decode_access_token_valid(self) -> None:
        """Decode should return user_id for valid token."""
        user_id = uuid4()
        token = create_access_token(user_id)

        decoded_id = decode_access_token(token)

        assert decoded_id == user_id

    def test_decode_access_token_invalid(self) -> None:
        """Decode should return None for invalid token."""
        result = decode_access_token("invalid.token.here")

        assert result is None

    def test_decode_access_token_expired(self) -> None:
        """Decode should return None for expired token."""
        user_id = uuid4()
        # Create token that expired immediately
        token = create_access_token(user_id, expires_minutes=-1)

        result = decode_access_token(token)

        assert result is None

    def test_decode_access_token_tampered(self) -> None:
        """Decode should return None for tampered token."""
        user_id = uuid4()
        token = create_access_token(user_id)

        # Tamper with the payload
        parts = token.split(".")
        parts[1] = parts[1] + "tampered"
        tampered_token = ".".join(parts)

        result = decode_access_token(tampered_token)

        assert result is None

    def test_create_with_custom_expiry(self) -> None:
        """Create should accept custom expiry time."""
        user_id = uuid4()
        token = create_access_token(user_id, expires_minutes=60)

        decoded_id = decode_access_token(token)

        assert decoded_id == user_id
