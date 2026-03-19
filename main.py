import sys

# Ensure the cydradar directory is on the path so that all imports work
# when this file is run directly from Thonny.
if '/cydradar' not in sys.path:
    sys.path.insert(0, '/cydradar')

from radar import App

app = App()
app.main()
