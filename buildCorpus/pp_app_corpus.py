# -*- coding: utf-8 -*-

if __name__ == '__main__':
	import os
	
	# Flask es un módulo para lanzar un servidor que gestiona solicitudes HTTP. Permite asociar una función con cada llamada
	from flask import Flask, render_template, request, flash, json, jsonify, redirect, url_for, send_from_directory

	template_dir = os.path.abspath('../templates')
	# Creamos la app de Flask que va a gestionar las solicitudes HTTP
	app = Flask(__name__, template_folder=template_dir)

	# leemos el texto por defecto de la demo
	DEFAULT_TEXT = '../defaultText.txt'
	defaultTextFile = open(DEFAULT_TEXT, "r")
	defaultText = defaultTextFile.read()



# funciones del pp_routes.py que se ejecutan al llegar una solicitud Flask
from pp_routesCorpus2 import buildCorpus2
from pp_routesCorpus import getWikicatsFromText, getWikicatUrls


# Flask routes binding
app.add_url_rule("/getWikicatsFromText", "getWikicatsFromText", getWikicatsFromText, methods=["POST"])
app.add_url_rule("/buildCorpus2", "buildCorpus2", buildCorpus2, methods=["POST"])
app.add_url_rule("/getWikicatUrls", "getWikicatUrls", getWikicatUrls)

@app.route('/corpus',  methods=["GET", "POST"])
def hello_world():
	return render_template('./template_corpus.html', parDefaultText=defaultText)




# Arranca el servidor HTTP escuchando en el puerto 5000

if __name__ == '__main__':
	
	# esto sólo se usa para servir el style.js
	@app.route('/js/<path:path>')
	def send_js(path):
		return send_from_directory('js', path)

	app.run(debug=True, host='0.0.0.0', threaded=True)
