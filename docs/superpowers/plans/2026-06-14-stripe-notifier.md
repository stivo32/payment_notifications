# This file has been created with the assistance of an AI tool.

# Stripe Notification Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Long-running Python process on Raspberry Pi that polls Stripe for new `checkout.session.completed` events and sends formatted Telegram notifications enriched with Supabase user data.

**Architecture:** Modular Python package with one file per integration layer (`stripe_client`, `supabase_client`, `telegram_client`, `state`, `message_formatter`) orchestrated by a polling loop in `main.py`. SQLite tracks processed event IDs and last-seen timestamp to prevent duplicates.

**Tech Stack:** Python 3.11+, `stripe` SDK, `supabase-py`, `python-dotenv`, `requests`, `sqlite3` (stdlib), `pytest`

---

## File Map

| File | Responsibility |
|---|---|
| `main.py` | Entry point, infinite polling loop |
| `config.py` | Load + validate env vars |
| `state.py` | SQLite: processed event IDs, last_event_created timestamp |
| `stripe_client.py` | Fetch `checkout.session.completed` events from Stripe API |
| `supabase_client.py` | Fetch user record by user_id from Supabase |
| `message_formatter.py` | Build Telegram message text from Stripe + Supabase data |
| `telegram_client.py` | Send message via Telegram Bot API with retry logic |
| `tests/test_state.py` | Tests for SQLite state module |
| `tests/test_stripe_client.py` | Tests for Stripe client (mocked SDK) |
| `tests/test_supabase_client.py` | Tests for Supabase client (mocked SDK) |
| `tests/test_message_formatter.py` | Tests for message formatting logic |
| `tests/test_telegram_client.py` | Tests for Telegram client retry logic (mocked requests) |
| `tests/test_main.py` | Integration test for poll cycle |
| `.env.example` | Example env file |
| `requirements.txt` | Production dependencies |
| `requirements-dev.txt` | Dev/test dependencies |
| `stripe-notifier.service` | systemd unit file for Pi deployment |

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `requirements.txt`**

```
stripe>=7.0.0
supabase>=2.0.0
python-dotenv>=1.0.0
requests>=2.31.0
```

- [ ] **Step 2: Create `requirements-dev.txt`**

```
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 3: Create `.env.example`**

```
STRIPE_API_KEY=sk_live_...
STRIPE_POLL_INTERVAL_SECONDS=60
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=-100...
STATE_DB_PATH=./state.db
```

- [ ] **Step 4: Create `.gitignore`**

```
.env
*.db
__pycache__/
*.pyc
.pytest_cache/
venv/
```

- [ ] **Step 5: Create `tests/__init__.py`** (empty file)

- [ ] **Step 6: Install dependencies**

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
```

Expected: all packages install without error.

- [ ] **Step 7: Commit**

```bash
git init
git add requirements.txt requirements-dev.txt .env.example .gitignore tests/__init__.py
git commit -m "chore: project scaffold"
```

---

## Task 2: Config Module

**Files:**
- Create: `config.py`

- [ ] **Step 1: Create `config.py`**

```python
# This file has been created with the assistance of an AI tool.
import os
from dotenv import load_dotenv

load_dotenv()

def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value

STRIPE_API_KEY: str = _require("STRIPE_API_KEY")
SUPABASE_URL: str = _require("SUPABASE_URL")
SUPABASE_SERVICE_KEY: str = _require("SUPABASE_SERVICE_KEY")
TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID: str = _require("TELEGRAM_CHAT_ID")
POLL_INTERVAL: int = int(os.getenv("STRIPE_POLL_INTERVAL_SECONDS", "60"))
STATE_DB_PATH: str = os.getenv("STATE_DB_PATH", "./state.db")
```

- [ ] **Step 2: Verify config loads with a test `.env`**

Create `.env` from `.env.example` with real or placeholder values, then run:
```bash
python -c "import config; print('POLL_INTERVAL:', config.POLL_INTERVAL)"
```
Expected: `POLL_INTERVAL: 60`

- [ ] **Step 3: Commit**

```bash
git add config.py
git commit -m "feat: add config module with env var validation"
```

---

## Task 3: State Module (SQLite)

**Files:**
- Create: `state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_state.py
# This file has been created with the assistance of an AI tool.
import os
import time
import pytest
import state

TEST_DB = "./test_state.db"

@pytest.fixture(autouse=True)
def clean_db():
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_is_processed_returns_false_for_new_event():
    s = state.State(TEST_DB)
    assert s.is_processed("evt_123") is False

def test_mark_processed_then_is_processed_returns_true():
    s = state.State(TEST_DB)
    s.mark_processed("evt_123")
    assert s.is_processed("evt_123") is True

def test_get_last_event_created_returns_default_when_not_set():
    s = state.State(TEST_DB)
    result = s.get_last_event_created()
    expected = int(time.time()) - 86400
    assert abs(result - expected) < 5  # within 5 seconds of now-24h

def test_set_and_get_last_event_created():
    s = state.State(TEST_DB)
    s.set_last_event_created(1700000000)
    assert s.get_last_event_created() == 1700000000
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_state.py -v
```
Expected: `ModuleNotFoundError: No module named 'state'`

- [ ] **Step 3: Create `state.py`**

```python
# This file has been created with the assistance of an AI tool.
import sqlite3
import time


class State:
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_events (
                    event_id TEXT PRIMARY KEY,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

    def is_processed(self, event_id: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM processed_events WHERE event_id = ?", (event_id,)
            ).fetchone()
            return row is not None

    def mark_processed(self, event_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO processed_events (event_id) VALUES (?)",
                (event_id,)
            )

    def get_last_event_created(self) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM state WHERE key = 'last_event_created'"
            ).fetchone()
            if row is None:
                return int(time.time()) - 86400
            return int(row[0])

    def set_last_event_created(self, timestamp: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO state (key, value) VALUES ('last_event_created', ?)",
                (str(timestamp),)
            )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_state.py -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add state.py tests/test_state.py
git commit -m "feat: add SQLite state module"
```

---

## Task 4: Stripe Client

**Files:**
- Create: `stripe_client.py`
- Create: `tests/test_stripe_client.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_stripe_client.py
# This file has been created with the assistance of an AI tool.
from unittest.mock import MagicMock, patch
import stripe_client


def _make_event(event_id: str, created: int, session_data: dict) -> MagicMock:
    event = MagicMock()
    event.id = event_id
    event.created = created
    event.data.object = MagicMock(**session_data)
    return event


def test_fetch_new_events_returns_list():
    mock_event = _make_event("evt_1", 1700000100, {
        "id": "cs_1",
        "customer_email": "user@example.com",
        "amount_total": 4900,
        "currency": "usd",
        "metadata": {"user_id": "uid_abc"},
    })

    with patch("stripe_client.stripe.Event.list") as mock_list:
        mock_list.return_value.auto_paging_iter.return_value = [mock_event]
        events = stripe_client.fetch_new_events(since_timestamp=1700000000)

    assert len(events) == 1
    assert events[0].id == "evt_1"
    mock_list.assert_called_once_with(
        type="checkout.session.completed",
        created={"gte": 1700000000},
    )


def test_fetch_new_events_returns_empty_list_when_none():
    with patch("stripe_client.stripe.Event.list") as mock_list:
        mock_list.return_value.auto_paging_iter.return_value = []
        events = stripe_client.fetch_new_events(since_timestamp=1700000000)

    assert events == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_stripe_client.py -v
```
Expected: `ModuleNotFoundError: No module named 'stripe_client'`

- [ ] **Step 3: Create `stripe_client.py`**

```python
# This file has been created with the assistance of an AI tool.
import logging
import stripe
import config

stripe.api_key = config.STRIPE_API_KEY

logger = logging.getLogger(__name__)


def fetch_new_events(since_timestamp: int) -> list:
    """Return list of checkout.session.completed events created >= since_timestamp."""
    try:
        result = stripe.Event.list(
            type="checkout.session.completed",
            created={"gte": since_timestamp},
        )
        return list(result.auto_paging_iter())
    except stripe.StripeError as e:
        logger.error("Stripe API error: %s", e)
        return []
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_stripe_client.py -v
```
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add stripe_client.py tests/test_stripe_client.py
git commit -m "feat: add Stripe client module"
```

---

## Task 5: Supabase Client

**Files:**
- Create: `supabase_client.py`
- Create: `tests/test_supabase_client.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_supabase_client.py
# This file has been created with the assistance of an AI tool.
from unittest.mock import MagicMock, patch
import supabase_client


def test_get_user_returns_user_dict_when_found():
    mock_response = MagicMock()
    mock_response.data = [{"id": "uid_abc", "email": "user@example.com", "created_at": "2025-01-15T10:00:00"}]

    with patch("supabase_client._client") as mock_client:
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
        result = supabase_client.get_user("uid_abc")

    assert result == {"id": "uid_abc", "email": "user@example.com", "created_at": "2025-01-15T10:00:00"}


def test_get_user_returns_none_when_not_found():
    mock_response = MagicMock()
    mock_response.data = []

    with patch("supabase_client._client") as mock_client:
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
        result = supabase_client.get_user("uid_missing")

    assert result is None


def test_get_user_returns_none_on_exception():
    with patch("supabase_client._client") as mock_client:
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = Exception("DB error")
        result = supabase_client.get_user("uid_abc")

    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_supabase_client.py -v
```
Expected: `ModuleNotFoundError: No module named 'supabase_client'`

- [ ] **Step 3: Create `supabase_client.py`**

```python
# This file has been created with the assistance of an AI tool.
import logging
from supabase import create_client
import config

logger = logging.getLogger(__name__)

_client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


def get_user(user_id: str) -> dict | None:
    """Fetch user record by id. Returns dict or None if not found."""
    try:
        response = (
            _client.table("users")
            .select("*")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error("Supabase error fetching user %s: %s", user_id, e)
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_supabase_client.py -v
```
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add supabase_client.py tests/test_supabase_client.py
git commit -m "feat: add Supabase client module"
```

---

## Task 6: Message Formatter

**Files:**
- Create: `message_formatter.py`
- Create: `tests/test_message_formatter.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_message_formatter.py
# This file has been created with the assistance of an AI tool.
from unittest.mock import MagicMock
import message_formatter


def _make_session(email: str, amount_total: int, currency: str, metadata: dict) -> MagicMock:
    session = MagicMock()
    session.customer_email = email
    session.amount_total = amount_total
    session.currency = currency
    session.metadata = metadata
    return session


def test_format_with_user_data():
    session = _make_session("user@example.com", 4900, "usd", {"user_id": "uid_abc"})
    user = {"created_at": "2025-01-15T10:00:00", "email": "user@example.com"}
    result = message_formatter.format_message(session, user)

    assert "user@example.com" in result
    assert "$49.00" in result
    assert "2025-01-15" in result
    assert "⚠️" not in result


def test_format_without_user_data_adds_warning():
    session = _make_session("user@example.com", 4900, "usd", {})
    result = message_formatter.format_message(session, None)

    assert "user@example.com" in result
    assert "$49.00" in result
    assert "⚠️ User not found in DB" in result


def test_format_converts_cents_to_dollars():
    session = _make_session("a@b.com", 10050, "usd", {})
    result = message_formatter.format_message(session, None)
    assert "$100.50" in result


def test_format_uppercase_currency():
    session = _make_session("a@b.com", 1000, "eur", {})
    result = message_formatter.format_message(session, None)
    assert "EUR" in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_message_formatter.py -v
```
Expected: `ModuleNotFoundError: No module named 'message_formatter'`

- [ ] **Step 3: Create `message_formatter.py`**

```python
# This file has been created with the assistance of an AI tool.


def format_message(session, user: dict | None) -> str:
    """Build Telegram message from Stripe session and optional Supabase user."""
    email = session.customer_email or "unknown"
    amount = session.amount_total / 100
    currency = session.currency.upper()

    lines = [
        "💳 New Purchase",
        f"Email: {email}",
        f"Amount: ${amount:.2f} {currency}",
    ]

    if user:
        registered = user.get("created_at", "")[:10]  # YYYY-MM-DD
        if registered:
            lines.append(f"Registered: {registered}")
    else:
        lines.append("⚠️ User not found in DB")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_message_formatter.py -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add message_formatter.py tests/test_message_formatter.py
git commit -m "feat: add message formatter module"
```

---

## Task 7: Telegram Client

**Files:**
- Create: `telegram_client.py`
- Create: `tests/test_telegram_client.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_telegram_client.py
# This file has been created with the assistance of an AI tool.
from unittest.mock import MagicMock, patch, call
import pytest
import telegram_client


def test_send_message_succeeds_on_first_try():
    mock_response = MagicMock()
    mock_response.ok = True

    with patch("telegram_client.requests.post", return_value=mock_response) as mock_post:
        telegram_client.send_message("Hello")

    assert mock_post.call_count == 1


def test_send_message_retries_on_failure_then_succeeds():
    fail_response = MagicMock()
    fail_response.ok = False
    fail_response.text = "Bad Gateway"

    ok_response = MagicMock()
    ok_response.ok = True

    with patch("telegram_client.requests.post", side_effect=[fail_response, ok_response]) as mock_post:
        with patch("telegram_client.time.sleep"):
            telegram_client.send_message("Hello")

    assert mock_post.call_count == 2


def test_send_message_logs_error_after_all_retries_fail():
    fail_response = MagicMock()
    fail_response.ok = False
    fail_response.text = "Server Error"

    with patch("telegram_client.requests.post", return_value=fail_response):
        with patch("telegram_client.time.sleep"):
            with patch("telegram_client.logger") as mock_logger:
                telegram_client.send_message("Hello")

    mock_logger.error.assert_called_once()


def test_send_message_uses_exponential_backoff():
    fail_response = MagicMock()
    fail_response.ok = False
    fail_response.text = "err"

    with patch("telegram_client.requests.post", return_value=fail_response):
        with patch("telegram_client.time.sleep") as mock_sleep:
            telegram_client.send_message("Hello")

    assert mock_sleep.call_args_list == [call(1), call(2), call(4)]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_telegram_client.py -v
```
Expected: `ModuleNotFoundError: No module named 'telegram_client'`

- [ ] **Step 3: Create `telegram_client.py`**

```python
# This file has been created with the assistance of an AI tool.
import logging
import time
import requests
import config

logger = logging.getLogger(__name__)

_API_URL = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
_MAX_RETRIES = 3


def send_message(text: str) -> None:
    """Send text message to configured Telegram chat. Retries up to 3 times."""
    payload = {"chat_id": config.TELEGRAM_CHAT_ID, "text": text}
    delay = 1

    for attempt in range(_MAX_RETRIES):
        response = requests.post(_API_URL, json=payload)
        if response.ok:
            return
        logger.warning("Telegram send failed (attempt %d/%d): %s", attempt + 1, _MAX_RETRIES, response.text)
        time.sleep(delay)
        delay *= 2

    logger.error("Telegram send failed after %d retries. Message lost: %s", _MAX_RETRIES, text[:100])
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_telegram_client.py -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add telegram_client.py tests/test_telegram_client.py
git commit -m "feat: add Telegram client with retry logic"
```

---

## Task 8: Main Polling Loop

**Files:**
- Create: `main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_main.py
# This file has been created with the assistance of an AI tool.
from unittest.mock import MagicMock, patch, call
import main


def _make_event(event_id: str, created: int, user_id: str = "uid_abc") -> MagicMock:
    event = MagicMock()
    event.id = event_id
    event.created = created
    event.data.object.customer_email = "user@example.com"
    event.data.object.amount_total = 4900
    event.data.object.currency = "usd"
    event.data.object.metadata = {"user_id": user_id}
    return event


def test_poll_cycle_processes_new_event():
    event = _make_event("evt_1", 1700000100)
    mock_state = MagicMock()
    mock_state.get_last_event_created.return_value = 1700000000
    mock_state.is_processed.return_value = False

    user = {"created_at": "2025-01-15T10:00:00"}

    with patch("main.stripe_client.fetch_new_events", return_value=[event]), \
         patch("main.supabase_client.get_user", return_value=user), \
         patch("main.telegram_client.send_message") as mock_send, \
         patch("main.message_formatter.format_message", return_value="msg") as mock_fmt:
        main.run_poll_cycle(mock_state)

    mock_fmt.assert_called_once_with(event.data.object, user)
    mock_send.assert_called_once_with("msg")
    mock_state.mark_processed.assert_called_once_with("evt_1")
    mock_state.set_last_event_created.assert_called_once_with(1700000100)


def test_poll_cycle_skips_already_processed_event():
    event = _make_event("evt_1", 1700000100)
    mock_state = MagicMock()
    mock_state.get_last_event_created.return_value = 1700000000
    mock_state.is_processed.return_value = True

    with patch("main.stripe_client.fetch_new_events", return_value=[event]), \
         patch("main.telegram_client.send_message") as mock_send:
        main.run_poll_cycle(mock_state)

    mock_send.assert_not_called()


def test_poll_cycle_continues_on_exception():
    mock_state = MagicMock()
    mock_state.get_last_event_created.return_value = 1700000000

    with patch("main.stripe_client.fetch_new_events", side_effect=Exception("boom")):
        # Should not raise
        main.run_poll_cycle(mock_state)


def test_poll_cycle_no_user_still_sends():
    event = _make_event("evt_1", 1700000100)
    mock_state = MagicMock()
    mock_state.get_last_event_created.return_value = 1700000000
    mock_state.is_processed.return_value = False

    with patch("main.stripe_client.fetch_new_events", return_value=[event]), \
         patch("main.supabase_client.get_user", return_value=None), \
         patch("main.telegram_client.send_message") as mock_send, \
         patch("main.message_formatter.format_message", return_value="msg"):
        main.run_poll_cycle(mock_state)

    mock_send.assert_called_once_with("msg")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_main.py -v
```
Expected: `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Create `main.py`**

```python
# This file has been created with the assistance of an AI tool.
import logging
import time
import config
import stripe_client
import supabase_client
import telegram_client
import message_formatter
from state import State

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_poll_cycle(state: State) -> None:
    try:
        since = state.get_last_event_created()
        events = stripe_client.fetch_new_events(since_timestamp=since)

        for event in events:
            if state.is_processed(event.id):
                continue

            session = event.data.object
            user_id = (session.metadata or {}).get("user_id")
            user = supabase_client.get_user(user_id) if user_id else None

            text = message_formatter.format_message(session, user)
            telegram_client.send_message(text)

            state.mark_processed(event.id)
            state.set_last_event_created(event.created)
            logger.info("Processed event %s", event.id)

    except Exception:
        logger.error("Unhandled exception in poll cycle", exc_info=True)


def main() -> None:
    logger.info("Starting Stripe notifier. Poll interval: %ds", config.POLL_INTERVAL)
    state = State(config.STATE_DB_PATH)

    while True:
        run_poll_cycle(state)
        time.sleep(config.POLL_INTERVAL)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
pytest -v
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: add main polling loop"
```

---

## Task 9: systemd Service File

**Files:**
- Create: `stripe-notifier.service`

- [ ] **Step 1: Create `stripe-notifier.service`**

```ini
[Unit]
Description=Stripe Notification Bot
After=network.target

[Service]
WorkingDirectory=/home/pi/stripe_notification
ExecStart=/home/pi/stripe_notification/venv/bin/python main.py
Restart=always
RestartSec=10
EnvironmentFile=/home/pi/stripe_notification/.env

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Document Pi deployment steps in a comment at top of file**

Add as comment line at top (INI files support `#` comments):

```ini
# Deploy: sudo cp stripe-notifier.service /etc/systemd/system/
# Enable: sudo systemctl enable stripe-notifier
# Start:  sudo systemctl start stripe-notifier
# Logs:   journalctl -u stripe-notifier -f
```

- [ ] **Step 3: Commit**

```bash
git add stripe-notifier.service
git commit -m "feat: add systemd service file for Pi deployment"
```

---

## Task 10: Full Test Run + Final Verification

- [ ] **Step 1: Run full test suite**

```bash
pytest -v
```
Expected: all tests PASS, no warnings.

- [ ] **Step 2: Verify module imports cleanly with a real `.env`**

```bash
python -c "import main; print('OK')"
```
Expected: `OK` (no errors)

- [ ] **Step 3: Dry-run smoke test**

Set `STRIPE_POLL_INTERVAL_SECONDS=5` in `.env`, run for 10 seconds, verify it polls without crashing:

```bash
timeout 10 python main.py || true
```
Expected: log lines showing poll cycles, no unhandled exceptions.

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "chore: final verification pass"
```
