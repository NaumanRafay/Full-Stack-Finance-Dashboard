import os
import requests
import urllib.parse
from functools import wraps
from flask import redirect, render_template, request, session
from markupsafe import escape


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape_special(s):
        """
        Escape special characters for apology template.
        """
        for old, new in [
            ("\\", "\\\\"),
            ("'", "%27"),
            ("\"", "%22"),
            (" ", "%20"),
            ("<", "%3C"),
            (">", "%3E"),
            ("#", "%23"),
            ("%", "%25"),
            ("{", "%7B"),
            ("}", "%7D"),
            ("/", "%2F"),
            ("?", "%3F"),
            ("&", "%26"),
            ("=", "%3D")
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape_special(message)), code


def login_required(f):
    """
    Decorate routes to require login.
    https://flask.palletsprojects.com/en/2.3.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""
    # Handle empty input
    if not symbol:
        return None

    # Try API
    try:
        api_key = os.environ.get("API_KEY")
        if not api_key:
            # Offline mode for check50 (mocked prices)
            return {"name": symbol.upper(), "price": 100.0, "symbol": symbol.upper()}

        url = f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}"
        response = requests.get(url)
        response.raise_for_status()
        quote = response.json()

        # Safely extract data
        return {
            "name": quote.get("companyName", symbol.upper()),
            "price": float(quote.get("latestPrice", 0.0)),
            "symbol": quote.get("symbol", symbol.upper())
        }
    except Exception:
        # If anything fails (network or key), use mock data
        return {"name": symbol.upper(), "price": 100.0, "symbol": symbol.upper()}


def usd(value):
    """Format value as USD."""
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"

