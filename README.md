# Finance

## Purpose
Developed a web application that simulates a stock trading platform, allowing users to buy and sell stocks, check real-time stock prices, and manage their portfolio.

## Role
Full-stack developer responsible for designing and implementing both the front-end and back-end of the application.

## Technologies Used
- **Front-end**: HTML, CSS, JavaScript, Bootstrap
- **Back-end**: Python, Flask
- **Database**: SQLite
- **APIs**: Alpha Vantage API for real-time stock data

## Challenges and Solutions
- **Challenge**: Integrating real-time stock data from the Alpha Vantage API.
  - **Solution**: Implemented API calls to fetch real-time stock prices and update the user's portfolio dynamically.
- **Challenge**: Ensuring secure user authentication and data storage.
  - **Solution**: Used Flask's built-in security features and implemented secure password hashing and session management.
- **Challenge**: Handling the unavailability of the Yahoo Finance API.
  - **Solution**: Created a `mock_lookup` function to simulate stock data retrieval, allowing testers to ensure the code works correctly even when the Yahoo Finance API is down.

## Outcome
- Successfully created a functional stock trading platform that allows users to simulate buying and selling stocks.
- The application was well-received by peers and instructors, demonstrating a solid understanding of web development and API integration.
