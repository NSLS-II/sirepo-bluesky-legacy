import datetime
from pathlib import Path

from bluesky.tests.utils import _print_redirect

from ophyd import Device, Signal, Component as Cpt
from ophyd.sim import SynAxis, NullStatus, new_uid

from srw_handler import read_srw_file
from sirepo_bluesky import SirepoBluesky


class SRWDetector(Device):
    """
    Use SRW code based on the value of the motor.

    Parameters
    ----------
    name : str
        The name of the detector

    TODO: complete doc-string.
    """
    image = Cpt(Signal)
    shape = Cpt(Signal)
    mean = Cpt(Signal)
    photon_energy = Cpt(Signal)
    horizontal_extent = Cpt(Signal)
    vertical_extent = Cpt(Signal)

    def __init__(self, name, cname, spec_name1, spec_name2, motor0, field0, motor1=None, field1=None, reg=None,
                 sim_id=None, sirepo_server='http://10.10.10.10:8000',
                 **kwargs):
        super().__init__(name=name, **kwargs)
        self.reg = reg
        self.cname = cname
        self.spec_name1 = spec_name1
        self.spec_name2 = spec_name2
        self._motor0 = motor0
        self._motor1 = motor1
        self._field0 = field0
        self._field1 = field1
        self._resource_id = None
        self._result = {}
        self._sim_id = sim_id
        self._sirepo_server = sirepo_server
        self._hints = None
        assert sim_id, 'Simulation ID must be provided. Currently it is set to {}'.format(sim_id)

    @property
    def hints(self):
        if self._hints is None:
            return {'fields': [self.mean.name]}
        return self._hints

    @hints.setter
    def hints(self, val):
        self._hints = dict(val)

    def trigger(self):
        super().trigger()
        x = self._motor0.read()[self._field0]['value']
        y = self._motor1.read()[self._field1]['value']
        datum_id = new_uid()
        date = datetime.datetime.now()
        srw_file = Path('/tmp/data') / Path(date.strftime('%Y/%m/%d')) / \
            Path('{}.dat'.format(datum_id))

        sim_id = self._sim_id
        sb = SirepoBluesky(self._sirepo_server)
        data = sb.auth('srw', sim_id)
        element = sb.find_element(data['models']['beamline'], 'title', self.cname)
        element[self.spec_name1] = x * 1000
        element[self.spec_name2] = y * 1000
        try:
            watch = sb.find_element(data['models']['beamline'], 'title', 'Watchpoint')
        except:
            watch = sb.find_element(data['models']['beamline'], 'title', 'Watchpoint')
        watch[self._field0] = x
        data['report'] = 'watchpointReport{}'.format(watch['id'])
        sb.run_simulation()
        with open(srw_file, 'wb') as f:
            f.write(sb.get_datafile())
        ret = read_srw_file(srw_file)

        self.image.put(datum_id)
        self.shape.put(ret['shape'])
        self.mean.put(ret['mean'])
        self.photon_energy.put(ret['photon_energy'])
        self.horizontal_extent.put(ret['horizontal_extent'])
        self.vertical_extent.put(ret['vertical_extent'])

        self._resource_id = self.reg.insert_resource('srw', srw_file, {})
        self.reg.insert_datum(self._resource_id, datum_id, {})

        return NullStatus()

    def describe(self):
        res = super().describe()
        res[self.image.name].update(dict(external="FILESTORE"))
        return res

    def unstage(self):
        super().unstage()
        self._resource_id = None
        self._result.clear()

class Component(Device):
    x = Cpt(SynAxis, delay=0.01)
    y = Cpt(SynAxis, delay=0.02)

def get_dict_parameters(d):
    non_parameters = ['title', 'shape', 'type', 'id']
    parameters = []
    for key in d:
        if key not in non_parameters:
            parameters.append(key)
    print(f'SPECIFICATION:   {parameters} \n')

def get_options():
    sb = SirepoBluesky('http://10.10.10.10:8000')
    data = sb.auth('srw', sim_id)
    print("Tunable parameters for Bluesky scan: ")
    for i in range(0, len(data['models']['beamline'])):
        print('COMPONENT:        ' + data['models']['beamline'][i]['title'])
        get_dict_parameters(data['models']['beamline'][i])

sim_id = input('Please enter sim ID: ')
get_options()
component_id = input("Please select component: ")
spec_id_one = input("Please select specification: ")
spec_id_two = input("Please select another specification or press ENTER to only use one: ")

c = Component(name=component_id)
srw_det = SRWDetector(name='srw_det', cname=component_id, spec_name1=spec_id_one,
                      spec_name2=spec_id_two, motor0=c.x, field0=component_id + '_x',
                      motor1=c.y, field1=component_id + '_y', reg=db.reg,
                      sim_id=sim_id)
srw_det.read_attrs = ['image', 'mean', 'photon_energy']
srw_det.configuration_attrs = ['horizontal_extent', 'vertical_extent', 'shape']

#Following comments are for testing purposes:

#srw_det.stage()
#srw_det.trigger()
#srw_det.unstage()

#RE(bp.grid_scan([srw_det], c.x, 0, 1e-3, 10, c.y, 0, 1e-3, 10, True))
#RE((bp.scan([srw_det], c.x, 0, 1e-3, 10)))
