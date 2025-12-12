try:
    from ili9341 import color565
except:
    def color565(r,g,b):
        r = (r >> 5) << 11
        g = (g >> 5) << 5
        b = (b >> 5)
        return r | g | b

class _cfg:
    DUMP1090_URL='http://core.klotz.me:8080/aircraft.json'
    LAT=37.428833
    LON=-122.114667
    RADIUS_NM = 10
    TRAIL_MIN_LENGTH = 4
    TRAIL_MAX_LENGTH = 18
    TRAIL_MAX_SPEED = 600
    BLINK_MILITARY = True
    FETCH_INTERVAL = 5
    MAX_TABLE_ROWS = 8
    DEFAULT_FONT_HEIGHT = 8
    SCREEN_DELAY_SECONDS = 60
    # Color constants (16-bit RGB565 values)
    BRIGHT_GREEN = color565(0, 255, 0)
    DIM_GREEN = color565(0, 128, 0)
    RED = color565(255, 0, 0)
    AMBER = color565(255, 191, 0)
    YELLOW = color565(255, 255, 0)
    BLACK = color565(0, 0, 0)
    WHITE = color565(255, 255, 255)
    LABEL_RING = False
    MIL_PREFIX_LIST = ['7CF']
