from routesBuildModels import buildAndTrainNewModelGroup as _buildAndTrainNewModelGroup
from routesBuildModels import getAllSavedD2VGroups as _getAllSavedD2VGroups
from routesBuildModels import getLog as _getLog
from routesBuildModels import getKorpusPath as _getKorpusPath
from flask import Flask, send_from_directory, render_template, request
from flask_cors import CORS

# html templates dir
template_dir = "../templates"

# initializes a new Flask app
app = Flask(__name__, template_folder=template_dir)
# Flask extension for handling Cross Origin Resource Sharing
CORS(app)


@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory('../css', path)


@app.route('/params')
def send_params():
    return send_from_directory(".", "params.json")


# Flask routes binding for interface requests
app.add_url_rule("/getLog", "getLog", _getLog, methods=["GET"])
app.add_url_rule("/getKorpusPath", "getKorpusPath", _getKorpusPath, methods=["GET"])
app.add_url_rule("/getAllSavedD2VGroups", "getAllSavedD2VGroups", _getAllSavedD2VGroups, methods=["GET"])
app.add_url_rule("/buildAndTrainNewModelGroup", "buildAndTrainNewModelGroup", _buildAndTrainNewModelGroup, methods=["POST"])


# user interface entry of the models builder tool
@app.route('/train')
def home():
    # default folder path where new models groups were saved. If nothing is received in query, then
    # the value will be D2V_ModelsGroups
    models_folder = request.args.get("models_folder", "D2V_ModelsGroups")  # TODO remove these default values
    # default file with the paths of the training files (one per line). If nothing is received in query, then
    # the value will be training_files.txt
    training_docs_file = request.args.get("training_docs_file", "training_files.txt")
    # default type for the new models (w2v or d2v). Only d2v supported for now.
    models_type = request.args.get("models_type", "d2v")
    return render_template('template_buildModels.html', models_type=models_type, models_folder=models_folder, training_docs_file=training_docs_file)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6060, threaded=True)
