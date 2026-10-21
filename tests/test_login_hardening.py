"""Login hardening: a failed login must not reveal whether the email exists."""
import re

from conftest import DEMO_USERS, token_from


def failed_login(client, email, password):
    token = token_from(client.get("/login").text)
    return client.post("/login", data={"email": email, "password": password,
                                       "csrf_token": token},
                       follow_redirects=False)


def alert_text(html):
    match = re.search(r'<p role="alert">(.*?)</p>', html, re.S)
    assert match, "login page shows no error message"
    return match.group(1).strip()


def test_wrong_password_and_unknown_email_produce_the_same_error(client):
    wrong = failed_login(client, DEMO_USERS["admin"]["email"], "not-the-password")
    unknown = failed_login(client, "nobody@example.test", "not-the-password")

    assert wrong.status_code == unknown.status_code
    assert alert_text(wrong.text) == alert_text(unknown.text)
    assert alert_text(wrong.text) == "Invalid email or password."


ADMIN = DEMO_USERS["admin"]
EDITOR = DEMO_USERS["editor"]


def attempt(client, user, password=None):
    return failed_login(client, user["email"], password or user["password"])


def fail_five_times(client, user):
    for _ in range(5):
        assert attempt(client, user, "wrong-password").status_code == 200


def test_sixth_attempt_is_refused_even_with_the_right_password(locked_client):
    fail_five_times(locked_client, ADMIN)

    refused = attempt(locked_client, ADMIN)

    assert refused.status_code == 429


def test_login_works_again_once_fifteen_minutes_have_passed(locked_client, clock):
    fail_five_times(locked_client, ADMIN)
    assert attempt(locked_client, ADMIN).status_code == 429

    clock.advance(15 * 60)

    assert attempt(locked_client, ADMIN).status_code == 303


def test_still_locked_just_before_fifteen_minutes(locked_client, clock):
    fail_five_times(locked_client, ADMIN)

    clock.advance(15 * 60 - 1)

    assert attempt(locked_client, ADMIN).status_code == 429


def test_another_email_can_still_log_in(locked_client):
    fail_five_times(locked_client, ADMIN)

    assert attempt(locked_client, EDITOR).status_code == 303
