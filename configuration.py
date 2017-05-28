import yaml


def get_machines_amt():
    with open("inventory.yml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile)
        return cfg['machines']['total']


def get_machine_config(machine_name):
    with open("inventory.yml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile)
        return cfg['machines'][machine_name]


def get_creds():
    with open("inventory.yml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile)
        return cfg['creds']
