from poke_track.models import Product, StockResult, StockStatus
from poke_track.notifiers.discord import DiscordNotifier
from poke_track.notifiers.email import EmailNotifier

PRODUCT = Product(store="bestbuy", url="https://example.com/item", name="Test Item")


def test_discord_not_configured_without_webhook(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    assert DiscordNotifier().is_configured() is False


def test_discord_configured_with_webhook(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")
    assert DiscordNotifier().is_configured() is True


def test_discord_send_posts_expected_content(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse()

    monkeypatch.setattr("poke_track.notifiers.discord.requests.post", fake_post)

    result = StockResult(product=PRODUCT, status=StockStatus.IN_STOCK, price="19.99")
    DiscordNotifier().send(result)

    assert captured["url"] == "https://discord.com/api/webhooks/x/y"
    assert "Test Item" in captured["json"]["content"]
    assert "19.99" in captured["json"]["content"]


def test_email_not_configured_when_missing_vars(monkeypatch):
    for var in ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "EMAIL_TO"]:
        monkeypatch.delenv(var, raising=False)
    assert EmailNotifier().is_configured() is False


def test_email_configured_when_all_vars_set(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "me@gmail.com")
    monkeypatch.setenv("SMTP_PASS", "app-password")
    monkeypatch.setenv("EMAIL_TO", "me@gmail.com")
    assert EmailNotifier().is_configured() is True
