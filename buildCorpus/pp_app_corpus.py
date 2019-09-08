# -*- coding: utf-8 -*-

# it is only executed if this is the main program
if __name__ == '__main__':
	import os
	
	# Flask is a module to lauch a web server. It permits to map a function for each request template 
	from flask import Flask, render_template, request, flash, json, jsonify, redirect, url_for, send_from_directory

	template_dir = os.path.abspath('../templates')
	# Creamos la app de Flask que va a gestionar las solicitudes HTTP
	app = Flask(__name__, template_folder=template_dir)


# this program has been launched in the Plethora/buildCorpus folder
# this is to search px_DB_Manager and px_aux in the Plethora folder
import sys
sys.path.append('../') 

# functions to be executed when Flask request are received 
from pp_routesCorpus import getWikicatsFromText, getWikicatUrls
from pp_routesCorpus2 import buildCorpus2


from aux import INITIAL_TEXT as _INITIAL_TEXT
initialTextFile = open(_INITIAL_TEXT, "r")
initialText = initialTextFile.read()

# Flask routes binding
app.add_url_rule("/getWikicatsFromText", "getWikicatsFromText", getWikicatsFromText, methods=["POST"])
app.add_url_rule("/buildCorpus2", "buildCorpus2", buildCorpus2, methods=["POST"])
app.add_url_rule("/getWikicatUrls", "getWikicatUrls", getWikicatUrls)

@app.route('/corpus',  methods=["GET", "POST"])
def hello_world():
	return render_template('./template_corpus.html', parDefaultText=initialText)




# start web server listening port 5000 by default

if __name__ == '__main__':
	
	# only to serve style.js
	@app.route('/js/<path:path>')
	def send_js(path):
		return send_from_directory('js', path)

	app.run(debug=True, host='0.0.0.0', threaded=True)
