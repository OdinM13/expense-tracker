# Expense Tracker with Advanced Analytics
#### Video Demo: <URL HERE>
#### Description:
This project is a comprehensive web-based financial management tool built with Python, Flask, and SQLite. It enables users to monitor their personal finances by logging expenditures and income, providing a clear visual representation of their financial health. 

While influenced by the CS50 "Finance" problem set, this application introduces significant custom features, including real-time data visualization via Chart.js, a dedicated tracking system for cash inflows, and a time-horizon filtering system that allows users to analyze data by week, month, or all-time history.

### Features:
- **User Authentication:** Secure registration and login system with password hashing using `werkzeug.security`.
- **Advanced Dashboard:** A central hub displaying current balance, total monthly spending, and dynamic charts.
- **Financial Visualization:** - **Doughnut Chart:** Displays spending breakdown by category with synchronized UI colors.
    - **Dual-Line Chart:** Visualizes cash flow trends, comparing daily income versus daily expenses.
- **Transaction Management:** Users can add new expenses, record cash deposits ("Charge Wallet"), and delete entries, which triggers an automatic balance refund.
- **Automated Balance Tracking:** Every transaction updates the user's `cash` balance in the database in real-time.
- **Responsive Design:** Optimized for various screen sizes using the Bootstrap 5 framework.

### File Structure:
- `app.py`: The core application logic, handling all routing, SQL queries, and session management.
- `helpers.py`: Utility functions including the `usd` currency formatter and the `login_required` decorator.
- `finance.db`: An SQLite database containing the `users`, `expenses`, and `income` tables.
- `templates/`:
    - `layout.html`: The base template containing the navigation bar, Bootstrap links, and common UI elements.
    - `index.html`: The main dashboard containing the Chart.js canvas elements and the unified transaction ledger.
    - `add.html`: A form-driven interface for recording new spending.
    - `charge.html`: An interface dedicated to adding funds (deposits) to the user's wallet.
    - `login.html`: The user entry point for secure session authentication.
    - `register.html`: The portal for new users to create an account with hashed password storage.
    - `apology.html`: A specialized error-handling page used to display validation or system errors.

### Design Choices:
1. **Schema Separation:** I implemented separate tables for `expenses` and `income`. This ensures data integrity and allows for more complex SQL `UNION` operations to generate the unified transaction history seen on the dashboard.
2. **Visual Consistency:** I developed a custom JavaScript Color Map to ensure that specific categories (like "Food" or "Rent") maintain the same color across both the doughnut chart and the table badges.
3. **Data Filling:** The trend chart utilizes a JavaScript mapping logic to ensure dates without transactions still appear on the X-axis with a zero-value, preventing broken visual lines.
4. **Time Management:** Timestamps were configured to use `localtime` within the SQL schema to ensure accurate reporting based on the user's actual time zone rather than UTC defaults.
