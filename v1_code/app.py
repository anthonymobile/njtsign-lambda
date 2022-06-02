from flask_bootstrap import Bootstrap4
from flask import Flask
from flask import render_template
from collections import defaultdict
from operator import itemgetter
import urllib.request, urllib.error, urllib.parse
import xml.etree.ElementTree
import config as cfg
from lxml import html
import requests

# connect to gunicorn logger
# search with
# sudo grep -r "NJTSIGN" /var/log/supervisor
# logger https://trstringer.com/logging-flask-gunicorn-the-manageable-way/
import logging
import config as cfg

app = Flask(__name__)
bootstrap = Bootstrap4(app)

@app.route('/')
def index():
    app.logger.error(f'NJTSIGN: starting to fetch arrivals')
    arrivals = get_arrivals()
    return render_template('index.html', cfg=cfg, arrivals=arrivals)

@app.template_filter()
def headsign(fd):
    # insert a newline into the headsign
    headsign = fd.replace(' ','<br/>', 1)
    return headsign

@app.template_filter()
def approaching_fix(pt):
    if pt in cfg.pt_replacements:
        return cfg.pt_replacements[pt]
    else:
        return pt.lower()

def get_arrivals():
    arrivals = defaultdict(dict)
    for tuple in cfg.watchlist:
        stop=tuple[0]
        routelist = tuple[1]
        for route in routelist:
            arrivals[stop][route]=(Service(stop, route).arrival_data)
    arrivals = pare_arrivals(arrivals)
    arrivals = regroup_arrivals(arrivals)
    app.logger.error(f'NJTSIGN: finished fetch arrivals')
    return arrivals

def regroup_arrivals(arrivals):
    arrivals_board = []
    for stop, arrival_data in arrivals.items():
        for route, arrivals_list in arrival_data.items():      
            for arrival in arrivals_list:
                arrivals_board.append(arrival)
    for arrival in arrivals_board:
        arrival['fd']=headsign_lookup(arrival['fd'])
    # sort by destination and ETA
    arrivals_board = sorted(arrivals_board, key=itemgetter('fd', 'rd', 'eta_int'))
    ##  sort by ETA only
    # arrivals_board = sorted(arrivals_board, key=itemgetter('eta_int'))
    return arrivals_board

def headsign_lookup(fd):
    try:
        # split off the route number
        fd = fd.split(" ", 1)[1]
        fd=cfg.headsign_replacements[fd]
        return fd
    except KeyError:
        app.logger.error(f"NJTSIGN: headsign_lookup::||{fd}|| not found in headsign_replacements")
        return fd

def pare_arrivals(arrivals):
    # drop ones under cutoff
    for stop, arrival_data in arrivals.items():
        for route, arrivals_list in arrival_data.items():
            for i,arrival in enumerate(arrivals_list):
                if int(arrival['eta_int']) > cfg.cutoff:
                    del arrivals_list[i]
    return arrivals

#FIXME: add logging statements here to try to isolate bugs causing outages
class Service:

    def __init__(self, stop, route):
        self.stop = stop
        self.stop_name = self.get_stop_name()
        self.route = route
        self.arrival_data = self.get_arrivals()

    def __repr__(self):
        return 'Service (route=%s, arrivals=%s)' % (self.stop, self.route, self.arrival_data)

    def get_arrivals(self):

        # retrieve data and catch common errors
        try:
            arrivals_url = 'http://mybusnow.njtransit.com/bustime/map/getStopPredictions.jsp?route=%s&stop=%s'
            submit_url = arrivals_url % (self.route, self.stop)
            data = urllib.request.urlopen(submit_url).read()
        except urllib.error.HTTPError as e:
            app.logger.error(f"NJTSIGN: HTTPError fetching arrivals for route {self.route} at {self.stop}")
        except urllib.error.URLError as e:
            app.logger.error(f"NJTSIGN: URLError fetching arrivals for route {self.route} at {self.stop}")
        else:
            pass

        # parse response
        arrivals_list = []
        e = xml.etree.ElementTree.fromstring(data)

        # no arrivals
        x = e.findall('noPredictionMessage')
        if e.findall('noPredictionMessage'):
            dummy_record = {
                        'rd': str(self.route),
                        'fd': 'No service',
                        'eta': 'No service',
                        'eta_int': 99,
                        'v': '0000',
                        'pt': '',
                        'occupancy': 'NO DATA'
                        }
            arrivals_list.append(dummy_record)
            return arrivals_list

        # some arrivals
        for atype in e.findall('pre'):
            fields = {}
            for field in atype:
                if field.tag not in fields and hasattr(field, 'text'):
                    if field.text is None:
                        fields[field.tag] = ''
                        continue
                    fields[field.tag] = field.text.replace("&nbsp", "") 
            arrivals_list.append(fields)

        # parse needed fields
        for arrival in arrivals_list:
            arrival['stop_id'] = self.stop
            arrival['stopname'] = self.stop_name
            arrival['eta'] = '0'
            if arrival['pt']:

                # first see if its special, if so, recode then skip rest of loop

                if arrival['pt'] in cfg.pt_messages:
                    arrival['eta_int'] = cfg.pt_messages[arrival['pt']]
                    continue
                
                # otherwise split and try to cast as int
                try:
                   arrival['eta_int'] = int(arrival['pt'].split(' ')[0])
                # unless its a new special message
                except:
                    arrival['eta_int'] = -1

            arrival['occupancy'] = get_occupancy(arrival['stop_id'], arrival['v'])
            
            
        app.logger.debug(f'NJTSIGN: fetched {len(arrivals_list)} arrivals')

        return arrivals_list[:cfg.num_arrivials_per_route]

    def get_stop_name(self):
        stop_name = 'Stop name unknown.'
        for stop_id,stopname in cfg.stopnames.items():
            if self.stop == int(stop_id):
                stop_name = stopname
            else:
                continue
        return stop_name


def get_occupancy(stop, v):
    
    url=f"https://www.njtransit.com/my-bus-to?stopID={stop}&form=stopID"

    # Request the page and scrape the data
    try:
        app.logger.error(f'NJTSIGN: starting fetch occupancy data for stop {stop}')
        page = requests.get(url)
    except Exception as e:
        app.logger.error(f"NJTSIGN: {e} fetching occupancy data for stop {stop}")
        
    tree = html.fromstring(page.content)

    raw_rows = tree.xpath("//div[@class='media-body']")
    parsed_rows=[str(row.xpath("string()")) for row in raw_rows]
    split_rows = [row.split('\n') for row in parsed_rows]
    stripped_rows = []
    for row in split_rows:
        stripped_row = []
        for word in row:
            stripped_row.append(word.strip())
        stripped_rows.append([i for i in stripped_row if i])
    filtered_rows = [b for b in stripped_rows if len(b)==5]
    
    
    #FIXME: this could be optimized, but it works so..
    for row in filtered_rows:
        for field in row:
            # make sure types match
            try:
                if str(field.split('#')[1]) == str(v):
                    for field in row:
                        if field in ['LIGHT','MEDIUM','HEAVY']:
                            app.logger.error(f'NJTSIGN: done fetching occupancy data for stop {stop}')
                            return field
            except Exception as e:
                pass
    app.logger.error(f'NJTSIGN: done fetching occupancy data for stop {stop}')
    return 'N/A'


if __name__ == "__main__":

    # connect to gunicorn logger
    # https://trstringer.com/logging-flask-gunicorn-the-manageable-way/
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    # app.logger.setLevel(gunicorn_logger.level)
    app.logger.setLevel(logging.DEBUG)
    app.run()
