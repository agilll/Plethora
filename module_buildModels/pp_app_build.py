from routesBuildModels import buildAndTrainNewModelGroup as _buildAndTrainNewModelGroup
from routesBuildModels import getAllSavedGroups as _getAllSavedGroups
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
app.add_url_rule("/getAllSavedGroups", "getAllSavedGroups", _getAllSavedGroups, methods=["GET"])
app.add_url_rule("/buildAndTrainNewModelGroup", "buildAndTrainNewModelGroup", _buildAndTrainNewModelGroup, methods=["POST"])


# user interface entry of the models builder tool
@app.route('/train')
def home():
    # default folder path where new models groups were saved. Query param
    # 'ModelsGroups' by default
    models_folder = request.args.get("models_folder", "ModelsGroups")  # TODO remove these default values
    # default file with the paths of the training files (one per line). Query param
    # 'training_files.txt' by default
    training_docs_path = request.args.get("training_docs_path", "training_files.txt")
    # default type for the new models (w2v or d2v). Query param
    # 'd2v' by default
    models_type = request.args.get("models_type", "d2v")
    return render_template('template_buildModels.html', models_type=models_type, models_folder=models_folder, training_docs_path=training_docs_path)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6060, threaded=True)
