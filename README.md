# Digital Wallet API
A Flask-based API for a digital wallet system with user authentication, fund transfers, and product purchases.

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Set up MySQL: `CREATE DATABASE digital_wallet;`
3. Create `.env` with `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`, `SECRET_KEY`, `CURRENCY_API_KEY`.
4. Run: `python app.py`

## Endpoints
- `POST /register`: Register a user.
- `POST /fund`: Fund account (Basic Auth).
- `POST /pay`: Pay another user (Basic Auth).
- `GET /bal`: Check balance (Basic Auth).
- `GET /stmt`: Transaction history (Basic Auth).
- `POST /product`: Add product (Basic Auth).
- `GET /product`: List products.
- `POST /buy`: Buy product (Basic Auth).

## Testing
Use Postman to test endpoints. Set `Authorization: Basic <base64(username:password)>` for protected routes.
