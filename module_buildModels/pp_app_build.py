from routesBuildModels import buildAndTrainNewModelGroup as _buildAndTrainNewModelGroup
from routesBuildModels import getAllSavedD2VGroups as _getAllSavedD2VGroups
from routesBuildModels import getLog as _getLog
from flask import Flask, send_from_directory, render_template, request
from flask_cors import CORS

template_dir = "../templates"

app = Flask(__name__, template_folder=template_dir)
CORS(app)


@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory('../css', path)


app.add_url_rule("/getLog", "getLog", _getLog, methods=["GET"])
app.add_url_rule("/getAllSavedD2VGroups", "getAllSavedD2VGroups", _getAllSavedD2VGroups, methods=["GET"])
app.add_url_rule("/buildAndTrainNewModelGroup", "buildAndTrainNewModelGroup", _buildAndTrainNewModelGroup, methods=["POST"])


@app.route('/train')
def home():
    models_folder = request.args.get("models_folder", "models")  # TODO remove these default values
    training_docs_file = request.args.get("training_docs_file", "training_t_files.txt")
    models_type = request.args.get("training_docs_file", "d2v")
    return render_template('template_buildModels.html', models_type=models_type, models_folder=models_folder, training_docs_file=training_docs_file)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6060, threaded=True)
