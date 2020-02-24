import datetime
import hashlib
import os
import time as ttime
from collections import deque
from multiprocessing import Process
from pathlib import Path

from ophyd.sim import NullStatus, new_uid

from sirepo_bluesky import SirepoBluesky
from srw_handler import read_srw_file


class BlueskyFlyer:
    def __init__(self):
        self.name = 'bluesky_flyer'
        self._asset_docs_cache = deque()
        self._resource_uids = []
        self._datum_counter = None
        self._datum_ids = []

    def kickoff(self):
        return NullStatus()

    def complete(self):
        return NullStatus()

    def collect(self):
        ...

    def collect_asset_docs(self):
        items = list(self._asset_docs_cache)
        self._asset_docs_cache.clear()
        for item in items:
            yield item


class SirepoFlyer(BlueskyFlyer):
    def __init__(self, sim_id, server_name, params_to_change, sim_code='srw',  # copy_count=5,
                 watch_name='Watchpoint', run_parallel=True):
        super().__init__()
        self.name = 'sirepo_flyer'
        self.sim_id = sim_id
        self.server_name = server_name
        self.params_to_change = params_to_change
        self.sim_code = sim_code
        self._copy_count = len(self.params_to_change)
        self.watch_name = watch_name
        self.run_parallel = run_parallel

    @property
    def copy_count(self):
        return self._copy_count

    @copy_count.setter
    def copy_count(self, value):
        try:
            value = int(value)
        except TypeError:
            raise
        self._copy_count = value

    def kickoff(self):
        sb = SirepoBluesky(self.server_name)
        data, schema = sb.auth(self.sim_code, self.sim_id)
        self._copies = []
        self._srw_files = []
        # print('Length of params_to_change', len(self.params_to_change), 'inside class')

        for i in range(self._copy_count):  # TODO: change it to loop over total number of simulations
            datum_id = new_uid()
            date = datetime.datetime.now()
            srw_file = str(Path('/tmp/data') / Path(date.strftime('%Y/%m/%d')) / Path('{}.dat'.format(datum_id)))
            self._srw_files.append(srw_file)
            _resource_uid = new_uid()
            resource = {'spec': 'SIREPO_FLYER',
                        'root': '/tmp/data',  # from 00-startup.py (added by mrakitin for future generations :D)
                        'resource_path': srw_file,
                        'resource_kwargs': {},
                        'path_semantics': {'posix': 'posix', 'nt': 'windows'}[os.name],
                        'uid': _resource_uid}
            self._resource_uids.append(_resource_uid)
            self._asset_docs_cache.append(('resource', resource))

        for param in self.params_to_change:
            # name doesn't need to be unique, server will rename it
            c1 = sb.copy_sim('{} Bluesky'.format(sb.data['models']['simulation']['name']), )
            print('copy {}, {}'.format(c1.sim_id, c1.data['models']['simulation']['name']))

            for key, parameters_to_update in param.items():
                optic_id = sb.find_optic_id_by_name(key)
                c1.data['models']['beamline'][optic_id].update(parameters_to_update)
            watch = sb.find_element(c1.data['models']['beamline'], 'title', self.watch_name)
            c1.data['report'] = 'watchpointReport{}'.format(watch['id'])
            self._copies.append(c1)

        if self.run_parallel:
            procs = []
            for i in range(self.copy_count):
                p = Process(target=self._run, args=(self._copies[i],))
                p.start()
                procs.append(p)
            # wait for procs to finish
            for p in procs:
                p.join()
        else:
            # run serial
            for i in range(self.copy_count):
                print(f'running sim: {self._copies[i].sim_id}')
                status = self._copies[i].run_simulation()
                print('Status:', status['state'])
        return NullStatus()

    def complete(self, *args, **kwargs):
        for i in range(len(self._copies)):
            datum_id = self._resource_uids[i]
            datum = {'resource': self._resource_uids[i],
                     'datum_kwargs': {},
                     'datum_id': datum_id}
            self._asset_docs_cache.append(('datum', datum))
            self._datum_ids.append(datum_id)
        return NullStatus()

    def describe_collect(self):
        return_dict = {self.name:
                        {f'{self.name}_image': {'source': f'{self.name}_image',
                                                'dtype': 'array',
                                                'shape': [-1, -1],
                                                'external': 'FILESTORE:'},
                         f'{self.name}_shape': {'source': f'{self.name}_shape',
                                                'dtype': 'array',
                                                'shape': [2]},
                         f'{self.name}_mean': {'source': f'{self.name}_mean',
                                               'dtype': 'number',
                                               'shape': []},
                         f'{self.name}_photon_energy': {'source': f'{self.name}_photon_energy',
                                                        'dtype': 'number',
                                                        'shape': []},
                         f'{self.name}_horizontal_extent': {'source': f'{self.name}_horizontal_extent',
                                                            'dtype': 'array',
                                                            'shape': [2]},
                         f'{self.name}_vertical_extent': {'source': f'{self.name}_vertical_extent',
                                                          'dtype': 'array',
                                                          'shape': [2]},
                         f'{self.name}_hash_value': {'source': f'{self.name}_hash_value',
                                                     'dtype': 'string',
                                                     'shape': []}
                         }
                       }

        elem_name = []
        curr_param = []
        for inputs in self.params_to_change:
            # inputs = self.params_to_change[i]
            for key, parameters_to_update in inputs.items():
                elem_name.append(key)  # e.g., 'Aperture'
                curr_param.append(list(parameters_to_update.keys()))  # e.g., 'horizontalSize'

        for i in range(len(elem_name)):
            for j in range(len(curr_param[i])):
                return_dict[self.name][f'{self.name}_{elem_name[i]}_{curr_param[i][j]}'] = {
                    'source': f'{self.name}_{elem_name[i]}_{curr_param[i][j]}',
                    'dtype': 'number',
                    'shape': []}
        return return_dict

    def collect(self):
        # get results and clean up the copied simulations
        shapes = []
        means = []
        photon_energies = []
        horizontal_extents = []
        vertical_extents = []
        hash_values = []
        for i in range(len(self._copies)):
            data_file = self._copies[i].get_datafile()
            with open(self._srw_files[i], 'wb') as f:
                f.write(data_file)

            ret = read_srw_file(self._srw_files[i])
            means.append(ret['mean'])
            shapes.append(ret['shape'])
            photon_energies.append(ret['photon_energy'])
            horizontal_extents.append(ret['horizontal_extent'])
            vertical_extents.append(ret['vertical_extent'])
            hash_values.append(hashlib.md5(data_file).hexdigest())

            print('copy {} data hash: {}'.format(self._copies[i].sim_id, hashlib.md5(data_file).hexdigest()))
            self._copies[i].delete_copy()
        print('length of hash values:', len(hash_values))

        assert len(self._copies) == len(self._datum_ids), \
            f'len(self._copies) != len(self._datum_ids) ({len(self._copies)} != {len(self._datum_ids)})'

        now = ttime.time()
        for i, datum_id in enumerate(self._datum_ids):
            elem_name = []
            curr_param = []

            data = {f'{self.name}_image': datum_id,
                    f'{self.name}_shape': shapes[i],
                    f'{self.name}_mean': means[i],
                    f'{self.name}_photon_energy': photon_energies[i],
                    f'{self.name}_horizontal_extent': horizontal_extents[i],
                    f'{self.name}_vertical_extent': vertical_extents[i],
                    f'{self.name}_hash_value': hash_values[i],
                    }

            for j in range(len(self.params_to_change)):
                inputs = self.params_to_change[j]
                for key, parameters_to_update in inputs.items():
                    elem_name.append(key)  # e.g., 'Aperture'
                    curr_param.append(list(parameters_to_update.keys()))  # e.g., 'horizontalSize'

            for ii in range(len(elem_name)):
                for jj in range(len(curr_param[ii])):
                    data[f'{self.name}_{elem_name[ii]}_{curr_param[ii][jj]}'] =\
                        params_to_change[i][elem_name[ii]][curr_param[ii][jj]]

            yield {'data': data,
                   'timestamps': {key: now for key in data}, 'time': now,
                   'filled': {key: False for key in data}}

    def _run(self, sim):
        print(f'running sim {sim.sim_id}')
        status = sim.run_simulation()
        print('Status:', status['state'])
        # return status, shared variable?


if __name__ == '__main__':
    # from re_config import *

    params_to_change = []
    for i in range(1, 10+1):
        key1 = 'Aperture'
        parameters_update1 = {'horizontalSize': i * .1, 'verticalSize': (11 - i) * .1}
        key2 = 'Lens'
        parameters_update2 = {'horizontalFocalLength': i + 10}

        params_to_change.append({key1: parameters_update1,
                                 key2: parameters_update2})
    # print('Length of params_to_change', len(params_to_change), 'outside class')

    sirepo_flyer = SirepoFlyer(sim_id='87XJ4oEb', server_name='http://10.10.10.10:8000',
                               params_to_change=params_to_change, watch_name='W60')

    # RE(bp.fly([sirepo_flyer]))
