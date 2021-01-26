# Build and Train Custom W2V&D2V Models

This module allows you to build and train groups of models with different parameters to see how they affect the performance of a model.


## How to use it

Install python requirements:

    pip install -r requirements.txt

Launch the Flask server:

    python pp_app_train

Open the template in the browser -- http://localhost:6060/train


**NOTE:** On the template you can add any model parameter with a simple pattern as its value. At the moment, this is how the pattern works:

    vector_size = "0:2:10,20:25"

    processPattern("0:2:4,10:13") --> [0, 2, 4, 10, 11, 12, 13]

### API

* GET __/train[?models_folder&training_docs_file]__ -- open the app
* GET __/getLog[?index]__ -- get all Log messages from 'index' position
* GET __/getAllSavedD2VGroups[?models_folder]__ -- get all saved groups in 'models_folder'
* POST __/buildAndTrainNewModelGroup__ -- create and train a new group with all combinations of the input parameters
    * __group_name__ - name for the new group
    * __models_type__ - d2v or w2v
    * __training_docs_file__ - path of the file with a training documents list (one per line). Paths can be absolutes ('/.../') or relatives (.../)
    * __models_folder__ - folder path where models will be saved
    * __params__ - models hyperparams list the models will be trained with (each param will be a multiple-value list)