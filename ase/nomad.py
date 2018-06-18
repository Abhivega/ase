import json
import numpy as np

import ase.units as units
from ase import Atoms
from ase.data import chemical_symbols


nomad_api_template = ('https://labdev-nomad.esc.rzg.mpg.de/'
                      'api/resolve/{hash}?format=recursiveJson')


def nmd2https(uri):
    assert uri.startswith('nmd://')
    return nomad_api_template.format(hash=uri[6:])


def nmd2dict(uri):
    try:
        from urllib2 import urlopen
    except ImportError:
        from urllib.request import urlopen

    httpsuri = nmd2https(uri)
    response = urlopen(httpsuri)
    txt = response.read().decode('utf8')
    return json.loads(txt, object_hook=lambda dct: NomadEntry(dct))


def read(fd):
    dct = json.load(fd, object_hook=lambda dct: NomadEntry(dct))
    return dct


def download(uri):
    # Might want to look/return sections also
    dct = nmd2dict(uri)
    return NomadEntry(dct)


def dict2images(d):
    assert 'section_run' in d, 'Missing section_run'
    runs = d['section_run']
    images = []
    for run in runs:
        systems = run['section_system']
        for system in systems:
            atoms = section_system2atoms(system)
            atoms.info['nomad_run_gIndex'] = run['gIndex']
            atoms.info['nomad_system_gIndex'] = system['gIndex']
            atoms.info['nomad_calculation_uri'] = d['uri']
            yield atoms


class NomadEntry(dict):
    def __init__(self, dct):
        #assert dct['type'] == 'nomad_calculation_2_0'
        #assert dct['name'] == 'calculation_context'
        # We could implement NomadEntries that represent sections.
        dict.__init__(self, dct)

    @property
    def hash(self):
        # The hash is a string, so not __hash__
        assert self['uri'].startswith('nmd://')
        return self['uri'][6:]

    def toatoms(self):
        return section_system2atoms(self)

    def iterimages(self):
        return dict2images(self)


def section_system2atoms(section):
    assert section['name'] == 'section_system'
    numbers = section['atom_species']
    numbers = np.array(numbers, int)
    numbers[numbers < 0] = 0
    numbers[numbers > len(chemical_symbols)] = 0
    positions = section['atom_positions']['flatData']
    positions = np.array(positions).reshape(-1, 3) * units.m
    pbc = section.get('configuration_periodic_dimensions')
    cell = section.get('lattice_vectors')
    atoms = Atoms(numbers, positions=positions)
    atoms.info['nomad_uri'] = section['uri']
    if pbc is not None:
        assert len(pbc) == 1
        pbc = pbc[0]  # it's a list??
        pbc = pbc['flatData']
        assert len(pbc) == 3
        atoms.pbc = pbc

    # celldisp?
    if cell is not None:
        cell = cell['flatData']
        cell = np.array(cell).reshape(3, 3) * units.m
        atoms.cell = cell

    return atoms


def section_singleconfig2calc(section):
    from ase.calculators.singlepoint import SinglePointCalculator
    kwargs = {}
    # Forces, total energy, ........
    # We should be able to extract e.g. a band structure as well.
    if 'energy_free' in section:
        kwargs['free_energy'] = section['energy_free'] * units.J
    calc = SinglePointCalculator(**kwargs)
    return calc


def main():
    #print('hello')
    uri = "nmd://N9Jqc1y-Bzf7sI1R9qhyyyoIosJDs/C74RJltyQeM9_WFuJYO49AR4gKuJ2"
    print(nmd2https(uri))
    entry = download(uri)
    #entry = read(open('out.json'))
    from ase.visualize import view
    view(list(entry.iterimages()))


if __name__ == '__main__':
    main()
