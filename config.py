# logging settings
LOG_FILE = 'app.log'
LEVEL = 'DEBUG'
MAX_BYTES = 50*1024
MAX_BACKUP_COUNT = 3

# tuples of stop_id, [routelist] to watch

## works
watchlist = [(30189, [85, 119]), (21062, [87]), (21765, [123])]

## testing
# watchlist = [(30189, [85, 119]), (21062, [87]), (21765, [123]), (21065, [86])]

# routes to display in black, rest will be text-muted (must be string)
vip_routes = ["85", "119"]

# home many arivals per route to show
num_arrivials_per_route=2

# decides which template to use
# screen_size = "big"
screen_size = "small"

# how short ETA has to be before we turn red (and yellow is this plus 5)
leave_alert_cutoff = 5

# how long ETA is before display is suppressed
cutoff = 45

# refresh rate in seconds
refresh_rate = 30

# lookup dict of stop_ids and names
stopnames = {'30189':'Congress St and Webster Ave',
            '21062':'Palisade Ave and Congress St',
            '21765': 'Palisade Ave and Paterson Plank Rd',
            '21065' : 'Palisade Ave and Congress St'
                }

# lookup dict of headsign (fd) and replacement text
headsign_replacements = {

    "HOBOKEN": "HOBOKEN",
    "NEW YORK": "NEW YORK",
    "HOBOKEN TERMINAL": "HOBOKEN",
    "HOBOKEN-PATH VIA JOURNAL SQ":"HOBOKEN",
    "NEWPORT MALL ":"GROVE ST",
    "NEWPORT MALL  VIA EXCHANGE PLACE":"GROVE ST",
    "NEWPORT MALL EXCHANGE PL VIA PARK AV":"GROVE ST",
    "NEWPORT MALL EXCHANGE PL VIA PARK AVE":"GROVE ST"
    }

# parsing the pt messages--add to this any others that show up in the error log
# No service is set when there by Service.get_arrivals() where there is noPredictionMessage 
# 0 will be first on list, 99 last, negatives will not be displayed
pt_messages = {
    "APPROACHING": 0,
    "Less than 1 MIN": 0,
    "DELAYED": 99
}

# used to rewrite the pt messages for better display
pt_replacements = {
    "APPROACHING": "NOW",
    "DELAYED": "DELAY",
    "Less than 1 MIN": "NOW"
}
