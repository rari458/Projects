from src.bot import PaperTradingBot

def main():
    # Start the bot with daily timeframe
    # You can change to '1h' or '15m' if you want faster signals for testing
    bot = PaperTradingBot(symbol='BTC/USDT', timeframe='1m', initial_balance=10000)
    bot.run()

if __name__ == "__main__":
    main()