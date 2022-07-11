# njtsign-lambda
Arrivals board for NJ transit buses (good for kiosks, etc)
 
## invocation
by URL

## required args

### watchlist
A nested list of stop ids and route #s to watch.

URL to set on kiosk
https://dl67kt3smf.execute-api.us-east-1.amazonaws.com/dev/?watchlist=[(30189,[85,119]),(21062,[87]),(21765,[123])]

URL to test on local dev
http://127.0.0.1:5000/?watchlist=[(30189,[85,119]),(21062,[87]),(21765,[123])]


## optional args

