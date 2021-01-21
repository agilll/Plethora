from gensim.models.doc2vec import Doc2Vec
import shutil
import os


# This class represents a group of d2v models. Allows simply get, add and save models to a group.
# If autoload flag is True, an already created group will be searched. If the group exists in
# 'models_folder' (a folder named like the group name), saved models will be loaded in this group.
class D2VModelGroup:

    def __init__(self, name, models_folder, autoload=False):
        # group name
        self.name = name
        # folder path when the group folder will be saved
        self.models_folder = models_folder
        # folder path for the group. Models will be saved here
        self.group_folder = self.models_folder + ("/" if not self.models_folder.endswith("/") else "") + self.name
        # models list
        self.models: list[Doc2Vec] = []
        if autoload:
            self.load()

    # Add models to this group. This function allows one d2v model instance or a list of them. All models
    # are stored in the 'self.models' variable
    def add(self, models):
        if isinstance(models, Doc2Vec):
            self.models.append(models)
        elif isinstance(models, list):
            for mdl in models:
                if isinstance(mdl, Doc2Vec):
                    self.models.append(mdl)

    # Save all models in a group folder with the name 'self.name'. This folder is overwritten if
    # it already exists or created if not
    def save(self):

        # the folder is removed if already exists
        if os.path.isdir(self.group_folder):
            shutil.rmtree(self.group_folder)

        # a new group folder is created
        os.makedirs(self.group_folder)

        # save all models in the list with an unique number id (in the group)
        for mdl in self.models:
            m_id = self.get_next_model_id()
            # each model is saved with the same name pattern:
            #   <group_name>_id<model_id>_dm<param_dm>_ep<param_epochs>_vs<param_vectorsize>_wn<param_window>.d2v.model
            mdl.save(self.group_folder + "/" + "%s_id%i_dm%i_ep%i_vs%i_wn%i.%s.model"
                     % (self.name, m_id, mdl.dm, mdl.epochs, mdl.vector_size, mdl.window, "d2v"))

    # Load all saved models in 'group_folder' to 'self.models' variable. Load all the files in the folder which
    # end with the '.d2v.model' extension
    def load(self):
        # do nothing if the group folder does not exist. The new folder will be created when the group is saved
        if not os.path.isdir(self.group_folder):
            return

        saved_models = []
        # get all the files paths in the folder and load them to a new Doc2Vec instance
        for model in os.listdir(self.group_folder):
            if model.endswith(".d2v.model"):
                d2v_model = Doc2Vec.load(self.group_folder + "/" + model)
                saved_models.append(d2v_model)

        self.models = saved_models

    # This function gets a new id for a new model in this group. Calculate the next unused number id in the group to
    # assign it to a new d2v model
    #
    # * Get the next possible number id, not the maximum + 1
    # * Use ALL the files in the folder. A file with different name will generate an exception
    def get_next_model_id(self):

        # return 0 if the group folder does not exist yet
        if not os.path.isdir(self.group_folder):
            return 0

        # get all number ids from the name of all files. The name patters must be:
        #   <group_name>_id<model_id>_dm<param_dm>_ep<param_epochs>_vs<param_vectorsize>_wn<param_window>.d2v.model
        models_ids = []
        for filename in os.listdir(self.group_folder):
            if filename.endswith(".d2v.model"):
                model_id = filename.split("_")[1][len(self.name):]  # TODO error with wrong name formats
                models_ids.append(int(model_id))

        # return 0 if there are no files in the folder
        if len(models_ids) == 0:
            return 0

        # get all free (not used) ids from 0 to the maximum id (+1) in the folder.
        # if the saved models are 1, 2, 4 and 7, 'not_ids' will obtain 0, 3, 5, 6 and 8.
        not_ids = [n for n in range(max(models_ids)+2) if n not in models_ids]

        # return first element in 'not_ids'. This is the first unused number id.
        return not_ids[0]

    # This allows uses a D2VModelGroup instance in a for-each, directly. A list of the group models will be always the
    # iterable element of this class
    def __iter__(self):
        return iter(self.models)


# This function gets all saved d2v groups in the given folder. The return is a list of instances of D2VModelGroup
# with all the models of the group already loaded
def getAllD2VGroups(models_folder_path):
    if not os.path.isdir(models_folder_path):
        return []

    saved_groups = []
    for group_folder_name in os.listdir(models_folder_path):
        if os.path.isdir(models_folder_path + ("/" if not models_folder_path.endswith("/") else "") + group_folder_name):
            new_group = D2VModelGroup(name=group_folder_name, models_folder=models_folder_path, autoload=True)
            saved_groups.append(new_group)

    return saved_groups
