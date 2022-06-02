# https://pythonforundergradengineers.com/deploy-serverless-web-app-aws-lambda-zappa.html


from flask import Flask
from flask import render_template
from flask_bootstrap import Bootstrap4

from src.Service import get_arrivals


import config as cfg

app = Flask(__name__)
bootstrap = Bootstrap4(app)


#################################
# ROUTES
#################################

@app.route('/')
def index():
    arrivals = get_arrivals()
    return render_template('index.html', cfg=cfg, arrivals=arrivals)


#################################
# FILTERS
#################################

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

# We only need this for local development.
if __name__ == '__main__':
    app.run()