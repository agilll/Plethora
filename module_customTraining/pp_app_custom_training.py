from flask import Flask, render_template, send_from_directory
from module_customTraining.build_d2v_models import build_d2v_models

app = Flask(__name__)

app.add_url_rule('/build_d2v_models', 'build_d2v_models', build_d2v_models, methods=["POST"])


@app.route('/css/<path:path>')
def send_js(path):
    return send_from_directory('css', path)


@app.route("/customModel")
def index():
    return render_template("./template_custom_training.html")


app.run(host='0.0.0.0', port='5080', debug=True)