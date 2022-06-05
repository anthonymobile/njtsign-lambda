import xml.etree.ElementTree
from operator import itemgetter
import urllib.request, urllib.error, urllib.parse
from collections import defaultdict
import ast

from lxml import html
from src.WebScraper import WebScraper

import config as cfg

def get_arrivals(watchlist):
    arrivals = defaultdict(dict)
    for tuple in ast.literal_eval(watchlist):
        stop=tuple[0]
        routelist = tuple[1]
        for route in routelist:
            arrivals[stop][route]=(Service(stop, route).arrival_data)
    arrivals = get_occupancies(arrivals)
    arrivals = pare_arrivals(arrivals)
    arrivals = regroup_arrivals(arrivals)
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
        return fd

def pare_arrivals(arrivals):
    # drop ones under cutoff
    for stop, arrival_data in arrivals.items():
        for route, arrivals_list in arrival_data.items():
            for i,arrival in enumerate(arrivals_list):
                if int(arrival['eta_int']) > cfg.cutoff:
                    del arrivals_list[i]
    return arrivals


#TODO: this works, and is fast, but its ugly.
def get_occupancies(arrivals):

    #async fetch occupancy data    
    urls = [f"https://www.njtransit.com/my-bus-to?stopID={k}&form=stopID" for (k,v) in arrivals.items()]
    occupancy_data = WebScraper(urls = urls)
    
    # traverse occupancy_data.master_dict.items() and create a lookup dict of v, occupancy
    occupancies=dict()
    for url, response in occupancy_data.master_dict.items():
        tree = html.fromstring(response['content'])
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
        for row in filtered_rows:
            v = row[1].split('#')[1]
            occupancies[v] = row[4]

    # traverse the arrivals dict add the occupancy for each
    for stop, arrival_dict in arrivals.items():
        for route, arrivals_at_stop_on_route in arrival_dict.items():
            position = 0
            for a in arrivals_at_stop_on_route:              
                try:
                    arrivals[stop][route][position]['occupancy'] = occupancies[a['v']]
                except KeyError as e:
                    pass
                position += 1
  
    # until we update arrivals its just passing through here
    return arrivals


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
            pass  
        except urllib.error.URLError as e:
            pass
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

        return arrivals_list[:cfg.num_arrivials_per_route]

    def get_stop_name(self):
        stop_name = 'Stop name unknown.'
        for stop_id,stopname in cfg.stopnames.items():
            if self.stop == int(stop_id):
                stop_name = stopname
            else:
                continue
        return stop_name
