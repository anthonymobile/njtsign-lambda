import urllib.request, urllib.error, urllib.parse
import xml.etree.ElementTree
import config as cfg
from lxml import html
import requests
from WebScraper import WebScraper


'''
how to fetch urls async

urls = ['https://understandingdata.com/', 'http://twitter.com/']
scrapedata = WebScraper(urls = urls)

'''


#FIXME: how to log anything in here? move it back to the main?
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

            arrival['occupancy'] = get_occupancy(arrival['stop_id'], arrival['v'])

        return arrivals_list[:cfg.num_arrivials_per_route]

    def get_stop_name(self):
        stop_name = 'Stop name unknown.'
        for stop_id,stopname in cfg.stopnames.items():
            if self.stop == int(stop_id):
                stop_name = stopname
            else:
                continue
        return stop_name


#######################################################################################################
#
# lxml scraper -- integrate into above (perhaps just add the occupancy to the right service result if we can match it up?)
# 
#######################################################################################################

def get_occupancy(stop, v):
    
    url=f"https://www.njtransit.com/my-bus-to?stopID={stop}&form=stopID"

    # Request the page and scrape the data
    try:
        page = requests.get(url)
    except:
        print("error getting web page")
        
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
                            return field
            except:
                pass
    return 'N/A'
