# Full-Stack Finance Dashboard

## Overview
A full-stack web application that simulates real-time stock trading and portfolio management. Built with Python and Flask, this application allows users to register accounts, query real-time stock prices, and simulate buying and selling equities. 

The backend is engineered using pure `sqlite3` and Python to ensure robust, secure, and highly optimized database transactions.

## Key Features
* **Secure User Authentication:** Encrypted password hashing (`pbkdf2:sha256`) and secure session management.
* **Real-Time Financial Data:** Integrates with an external API to fetch live stock quotes.
* **Portfolio Management:** Dynamically calculates current portfolio value, cash balances, and total asset worth based on real-time market data.
* **Transaction Ledger:** Maintains an immutable history of all buy and sell orders, displaying timestamps, execution prices, and share volume.
* **Account Management:** Includes personal touches like the ability to deposit simulated cash and securely update user passwords.

## Tech Stack
* **Backend:** Python, Flask, Flask-Session
* **Database:** SQLite3 (Relational Database Management)
* **Frontend:** HTML5, CSS3, Jinja2 Templating, Bootstrap
* **Security:** Werkzeug Security (Password Hashing)

## Database Architecture
The application relies on a strictly structured relational database to maintain data integrity during financial transactions:

* **`users` Table:** Stores user credentials, hashed passwords, and current liquid cash balances.
* **`transactions` Table:** Acts as a ledger. Records `user_id`, `symbol`, `shares` (positive for buys, negative for sells), `price` at execution, and an automatic `timestamp`. 

*Note: Complex SQL queries, including `GROUP BY` and `HAVING` clauses, are utilized to aggregate transaction history into a live portfolio view.*

