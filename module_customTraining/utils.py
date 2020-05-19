from itertools import zip_longest as zipl, product as prod


def split_params_combinations_from_json(json: dict):
    nlist = [name for name in json.keys()]
    vlist = [value for value in json.values()]
    values_prod = prod(*vlist)
    parameters_list = []
    for values in values_prod:
        new_json = dict()
        [new_json.__setitem__(name,value) for name,value in zipl(nlist, values, fillvalue=None)]
        parameters_list.append(new_json)
    return parameters_list
