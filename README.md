
# Professional Trading Journal Dashboard

A Streamlit-based trading dashboard that works like a smart Excel journal for your trading.

## Features

- Add and store trades with:
  - Date
  - Symbol
  - Market
  - Timeframe
  - Session
  - Strategy
  - Direction (Long/Short)
  - Entry, Stop Loss, Take Profit, Exit
  - Position size and fees
  - Notes and trade review
- Automatic calculations:
  - Gross PnL
  - Net PnL
  - Risk amount
  - Planned risk-to-reward
  - R-multiple
  - Win/Loss/Breakeven
- Professional analytics dashboard:
  - KPI cards (win rate, net PnL, profit factor, average R)
  - Equity curve
  - Rolling win rate
  - PnL by session
  - PnL by strategy
- Advanced analytics:
  - Max drawdown (value and percentage)
  - Expectancy by strategy (table + chart)
- Sidebar filters for date, symbol, session, and strategy
- Open trade editor to close existing open trades without re-entering everything
- **Persistent PostgreSQL database** (Supabase for cloud hosting)

## Run Locally

For local development with **PostgreSQL / Supabase**:

1. Create a `.streamlit/secrets.toml` file (copy from `.streamlit/secrets.toml`):
   ```toml
   DB_HOST = "your-project.supabase.co"
   DB_NAME = "postgres"
   DB_USER = "postgres"
   DB_PASSWORD = "your-password"
   DB_PORT = 5432
   ```

2. Install and run:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   streamlit run app.py
   ```

The app will connect to your PostgreSQL database and start storing trades there.

## Notes

- `Status = Open` allows saving trades before they are closed.
- `Status = Closed` requires `Exit Price` and contributes to performance analytics.
- Use **Update Open Trade** to close an existing open position without re-entering full trade details.
- Use the **Danger Zone** in the sidebar only if you want to clear all trades.

## Deploy to Streamlit Community Cloud

### Step 1: Set Up Supabase (PostgreSQL)

1. Go to [supabase.com](https://supabase.com) and create a free account.
2. Create a new project and note the connection details:
   - **Host**: Project URL (e.g., `xxx-yyy-zzz.supabase.co`)
   - **Database**: `postgres`
   - **User**: `postgres`
   - **Password**: Your password
   - **Port**: `5432`

### Step 2: Push to GitHub

```bash
git add .
git commit -m "Migrate to Supabase PostgreSQL"
git branch -M main
git remote add origin https://github.com/ronniepro256/Trading-Journal.git
git push -u origin main
```

### Step 3: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app" → Connect your GitHub account.
3. Select your repo (`ronniepro256/Trading-Journal`), branch (`main`), and main file (`app.py`).
4. Click "Advanced settings" → Add secrets:
   ```toml
   DB_HOST = "your-project.supabase.co"
   DB_NAME = "postgres"
   DB_USER = "postgres"
   DB_PASSWORD = "your-password"
   DB_PORT = 5432
   ```
5. Click "Deploy" — your app is live!

Data now persists in Supabase PostgreSQL across app restarts.
