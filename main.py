from radar import App
import wifi

wifi.connect_to_wifi()

app = App()
app.main()
