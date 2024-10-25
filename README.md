The web-based stock trading simulation software Finances was developed with Flask and SQLite in Python. Users can create an account, log in, and oversee a stock portfolio. Users of the app can check their transaction history, purchase and sell shares, and obtain real-time stock prices. Using data from Yahoo Finance that has been organized and presented across multiple pages, this project simulates actual stock trading.

Qualities:
Authentication of Users: Users can safely register, log in, and log out. Werkzeug is used to hash passwords for safekeeping.
Stock Portfolio Management: Users can view their current stock holdings, including details like stock name, symbol, price, shares owned, and total value.
Buying Stocks: Users can search for stocks by their symbols and purchase shares using the cash balance in their accounts.
Selling Stocks: Users can sell shares of the stocks they own and receive the corresponding amount of cash in return.
Transaction History: Users can view a history of all their stock transactions (buying and selling) with relevant details such as stock symbol, number of shares, price, and timestamp.
Real-Time Stock Quotes: Users can search for stocks by their symbols and retrieve the latest price information using Yahoo Finance API.
USD Formatting: Monetary values are consistently formatted in USD using a custom Jinja filter.
Project Structure. the structure of this project is: app.py: Main Flask application
helpers.py: Helper functions and utilities
finance.db: SQLite database containing user and transaction data
templates/: Contains HTML templates for different pages
static/: Contains static files like CSS
README.md: Project README file
requirements.txt: Required Python packages
Backend - Flask Application
app.py
This is the main Flask application responsible for routing and handling user requests. The key functionalities include:

Index Page: Shows the user's stock portfolio, including stock symbols, names, current prices, shares owned, and total portfolio value.
Buy and Sell Stocks: Allows users to buy and sell shares of stock. When the user buys, the system checks for sufficient cash. When the user sells it checks that the user has enough shares.
History Page: Shows transaction history for the logged-in user.
Login and Registration: Manages user authentication with hashed passwords stored in the SQLite database.
Stock Quote: Gives users with real-time stock quotes using data from the Yahoo Finance API.

