# -*- coding: utf-8 -*-
# this is the main program of the corpus builder tool
# it can be launched standalone, using a Flask server started here and calling localhost:5000/corpus
# or from the main tool with its Flask server

 # argument '-d' prints button labels with routes associated, to be easier to understand flow among interface and python modules
 
# it depends on px_DB_Manager and px_aux modules of the main tool, as well as the 

import sys

# only executed if this is the main program, that is, if we launch the corpus tool directly from the 'buildCorpus' folder
# not executed if we launch the corpus tool from the main tool
if __name__ == '__main__':
	import os
	
	# Flask is a module to launch a web server. It permits to map a function for each request template 
	from flask import Flask, render_template, request, flash, json, jsonify, redirect, url_for, send_from_directory
	
	# templates dir is shared with the main tool because it is possible for this tool to be called from the main one
	template_dir = os.path.abspath('../templates')
	# Create the Flask app to manage the HTTP request  
	app = Flask(__name__, template_folder=template_dir)


# this program has been launched in the Plethora/buildCorpus folder
# this is to search px_DB_Manager and px_aux in the Plethora folder
sys.path.append('../') 

# functions to be executed when Flask request are received 
from routesCorpus import getWikicatsFromText, getWikicatUrls
from routesCorpus2 import buildCorpus2


from aux import INITIAL_TEXT as _INITIAL_TEXT
initialTextFile = open(_INITIAL_TEXT, "r")
initialText = initialTextFile.read()

# Flask routes binding for interface requests
app.add_url_rule("/getWikicatsFromText", "getWikicatsFromText", getWikicatsFromText, methods=["POST"])  # to send a text and request the wikicats in it
app.add_url_rule("/buildCorpus2", "buildCorpus2", buildCorpus2, methods=["POST"])   # to send some wikicats and request to build the corpus
app.add_url_rule("/getWikicatUrls", "getWikicatUrls", getWikicatUrls) # ??

# this is the main entry point of the corpus builder tool
@app.route('/corpus',  methods=["GET", "POST"])
def hello_world():
	arguments = len(sys.argv) - 1;
	debug = False;
	if arguments == 1 and sys.argv[1] == "-d":   # argument '-d' prints button labels with routes associated
		debug = True;
	return render_template('./template_corpus.html', parDefaultText=initialText, parDebug=debug) # parDebug=True prints button labels with routes associated




# start web server listening port 5000 by default

# only executed if this is the main program, that is, if we launch the corpus tool directly from the 'buildCorpus' folder
# not executed if we launch the corpus tool from the main tool
if __name__ == '__main__':
	
	# only to serve style.js from the js folder of the main tool
	@app.route('/css/<path:path>')
	def send_js(path):
		return send_from_directory('../css', path)

	app.run(debug=True, host='0.0.0.0', threaded=True)
