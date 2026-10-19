from seed import seed
from gui import App

if __name__ == "__main__":
    seed()            # creates tables and sample data on first run only
    App().mainloop()
