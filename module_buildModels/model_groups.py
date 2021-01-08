from gensim.models.doc2vec import Doc2Vec
import shutil
import os


class D2VModelGroup:

    def __init__(self, name, models_folder, autoload=False):
        self.name = name
        self.models_folder = models_folder
        self.group_folder = self.models_folder + '/' + self.name
        self.models: list[Doc2Vec] = []
        if autoload:
            self.load()

    def add(self, models):
        if isinstance(models, Doc2Vec):
            self.models.append(models)
        elif isinstance(models, list):
            for mdl in models:
                if isinstance(mdl, Doc2Vec):
                    self.models.append(mdl)

    def save(self):
        if os.path.isdir(self.group_folder):
            shutil.rmtree(self.group_folder)
        os.makedirs(self.group_folder)
        for mdl in self.models:
            m_id = self.get_next_model_id()
            mdl.save(self.group_folder + '/' + '%s_%s%i_%i_%i_%i_%i.m'
                     % ('d2v', self.name, m_id, mdl.dm, mdl.epochs, mdl.vector_size, mdl.window))

    def load(self):
        if os.path.isdir(self.group_folder):
            self.models = [Doc2Vec.load(self.group_folder + '/' + mdl) for mdl in os.listdir(self.group_folder)]

    def get_next_model_id(self):  # get the next possible number, not the maximum + 1
        if not os.path.isdir(self.group_folder):
            return 0
        models_ids = [int(filename.split('_')[1][len(self.name):]) for filename in os.listdir(self.group_folder)]  # TODO error with unknown files
        if len(models_ids) == 0:
            return 0
        not_ids = [n for n in range(max(models_ids)+2) if n not in models_ids]
        return not_ids[0]

    def __iter__(self):
        return iter(self.models)


def get_all_d2v_groups(models_folder):
    if os.path.isdir(models_folder):
        return [D2VModelGroup(name=group_folder, models_folder=models_folder, autoload=True) for group_folder in os.listdir(models_folder)]
    return []
