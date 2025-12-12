def fetch_your_data_test():
    def rand_pos():
        return random.uniform(-0.5, 0.5)
    def ac1(): return Aircraft.from_dict({'callsign':"ALFA01", 'lat':_cfg.LAT+rand_pos(), 'lon':_cfg.LON+rand_pos(), 'track':45, 'speed':250, 'altitude':12000, 'distance':5.0, 'is_military':False})
    def ac2(): return Aircraft.from_dict({'callsign':"BRAVO2", 'lat':_cfg.LAT+rand_pos(), 'lon':_cfg.LON+rand_pos(), 'track':270, 'speed':120, 'altitude':8000, 'distance':8.2, 'is_military':True})
    def ac3(): return Aircraft.from_dict({'callsign':"CHAR3", 'lat':_cfg.LAT+rand_pos(), 'lon':_cfg.LON+rand_pos(), 'track':180, 'speed':350, 'altitude':30000, 'distance':12.5, 'is_military':False})
    return [ac1(), ac2(), ac3()]

