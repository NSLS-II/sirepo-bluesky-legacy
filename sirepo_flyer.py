from ophyd.sim import NullStatus, new_uid
from sirepo_bluesky import SirepoBluesky
from multiprocessing import Process
import hashlib
import datetime
from pathlib import Path
from collections import deque
import os
import itertools
import time as ttime


class SirepoFlyer:
    def __init__(self, sim_id, server_name, sim_code='srw', copy_count=10, run_parallel=True):
        self.name = 'sirepo_flyer'
        self.sim_id = sim_id
        self.server_name = server_name
        self.sim_code = sim_code
        self._copy_count = copy_count
        self.run_parallel = run_parallel
        self._asset_docs_cache = deque()
        self._resource_uid = None
        self._datum_counter = None

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
        sb.auth(self.sim_code, self.sim_id)

        self._copies = []
        self._srw_files = []
        self._resource_uids = []

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
            self._datum_counter = 1

        for i in range(self.copy_count):
            # name doesn't need to be unique, server will rename it
            c1 = sb.copy_sim('{} Bluesky'.format(sb.data['models']['simulation']['name']), )
            print('copy {}, {}'.format(c1.sim_id, c1.data['models']['simulation']['name']))
            # vary an aperture position
            aperture = c1.find_element(c1.data['models']['beamline'], 'title', 'Aperture')
            aperture['position'] = float(aperture['position']) + 0.5 * (i + 1)
            watch = sb.find_element(c1.data['models']['beamline'], 'title', 'W60')
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
                print('running sim: {}', self._copies[i].sim_id)
                self._copies[i].run_simulation()


        return NullStatus()

    def complete(self, *args, **kwargs):
        self._datum_ids = []
        for i in range(len(self._copies)):
            datum_id = '{}/{}'.format(self._resource_uids[i],  self._datum_counter)
            datum = {'resource': self._resource_uids[i],
                     'datum_kwargs': {},
                     'datum_id': datum_id}
            self._asset_docs_cache.append(('datum', datum))
            self._datum_ids.append(datum_id)
        return NullStatus()

    def describe_collect(self):
        return_dict = {'sirepo_flyer':
                        {'sirepo_flyer': {'source': 'sirepo_flyer',
                                              'dtype': 'array',
                                              'shape': [-1, -1],
                                              'external': 'FILESTORE:'}}}
        return return_dict

    def collect_asset_docs(self):
        items = list(self._asset_docs_cache)
        self._asset_docs_cache.clear()
        for item in items:
            yield item

    def collect(self):
        # get results and clean up the copied simulations
        for i in range(len(self._copies)):
            data_file = self._copies[i].get_datafile()
            with open(self._srw_files[i], 'wb') as f:
                f.write(data_file)
            print('copy {} data hash: {}'.format(self._copies[i].sim_id, hashlib.md5(data_file).hexdigest()))
            self._copies[i].delete_copy()
        now = ttime.time()
        for datum_id in self._datum_ids:
            data = {'sirepo_flyer': datum_id}
            yield {'data': data,
                   'timestamps': {key: now for key in data}, 'time': now,
                   'filled': {key: False for key in data}}

    def _run(self, sim):
        print('running sim {}'.format(sim.sim_id))
        sim.run_simulation()



sirepo_flyer = SirepoFlyer(sim_id='87XJ4oEb', server_name='http://10.10.10.10:8000')