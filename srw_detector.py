import datetime
from pathlib import Path

import unyt as u

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
    optic_name : str
        The name of the optic being accessed by Bluesky
    param0 : str
        The name of the first parameter of the optic being changed
    motor0 : Ophyd Component
        The first Ophyd component being controlled in Bluesky scan
    field0 : str
        The name corresponding to motor0 that is shown as axis in Bluesky scan
    param1 : str
        The name of the second parameter of the optic being changed
    motor1 :
        The second Ophyd component being controlled in Bluesky scan
    field1 : str
        The name corresponding to motor1 that is shown as axis in Bluesky scan
    reg : Databroker register
    sim_id : str
        The simulation id corresponding to the Sirepo simulation being run on
        local server
    watch_name : str
        The name of the watchpoint viewing the simulation
    sirepo_server : str
        Address that identifies access to local Sirepo server

    """
    image = Cpt(Signal)
    shape = Cpt(Signal)
    mean = Cpt(Signal)
    photon_energy = Cpt(Signal)
    horizontal_extent = Cpt(Signal)
    vertical_extent = Cpt(Signal)

    def __init__(self, name, sirepo_component, field0, field0_units, field1=None,
                 field1_units=None, reg=None, sim_id=None, watch_name=None,
                 sirepo_server='http://10.10.10.10:8000',
                 **kwargs):
        super().__init__(name=name, **kwargs)
        self.reg = reg
        self.sirepo_component = sirepo_component
        self.field0 = field0
        self.field0_units = field0_units
        self.field1 = field1
        self.field1_units = field1_units
        self._resource_id = None
        self._result = {}
        self._sim_id = sim_id
        self.watch_name = watch_name
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
        x = getattr(self.sirepo_component, self.field0).read()[f'{self.sirepo_component.name}_{self.field0}']['value']
        if self.field1 is not None:
            y = getattr(self.sirepo_component, self.field1).read()[f'{self.sirepo_component.name}_{self.field1}']['value']
        datum_id = new_uid()
        date = datetime.datetime.now()
        srw_file = Path('/tmp/data') / Path(date.strftime('%Y/%m/%d')) / \
            Path('{}.dat'.format(datum_id))

        sim_id = self._sim_id
        sb = SirepoBluesky(self._sirepo_server)
        data, schema = sb.auth('srw', sim_id)

        element = sb.find_element(data['models']['beamline'], 'title', self.sirepo_component.name)
        print(element)
        real_field0 = self.field0.replace('sirepo_','')
        if field1 is not None:
            real_field1 = self.field1.replace('sirepo_', '')

        unyt_obj = u.m
        starting_unit = x*unyt_obj
        converted_unit = starting_unit.to(field0_units)

        element[real_field0] = float(converted_unit.value)
        print(element[real_field0])
        #element[real_field0] = x * 1000

        if self.field1 is not None:
            unyt_obj1 = u.m
            starting_unit1 = y *unyt_obj
            converted_unit1 = starting_unit1.to(field1_units)
            element[real_field1] = float(converted_unit1.value)
            print(element[real_field1])
            #element[real_field1] = y * 1000

        watch = sb.find_element(data['models']['beamline'], 'title', self.watch_name)
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


class Positioner(Device):
    x = Cpt(SynAxis)
    y = Cpt(SynAxis)


if __name__ == "__main__":

    sim_id = input("Please enter sim ID: ")
    sb = SirepoBluesky('http://10.10.10.10:8000')
    data, sirepo_schema = sb.auth('srw', sim_id)
    watchpoints = {}
    print("Tunable parameters for Bluesky scan: ")

    non_parameters = ('title', 'type', 'id')

    for i in range(len(data['models']['beamline'])):
        print('OPTICAL ELEMENT:    ' + data['models']['beamline'][i]['title'])
        parameters = []
        for key in data['models']['beamline'][i]:
            if key not in non_parameters:
                parameters.append(key)
        print(f'PARAMETERS:        {parameters} \n')
        if data['models']['beamline'][i]['type'] == 'watch':
            watchpoints[data['models']['beamline'][i]['title']] = \
                str(data['models']['beamline'][i]['position'])
    print(f'WATCHPOINTS:       {watchpoints}')
    if len(watchpoints) < 1:
        raise ValueError('No watchpoints found. This simulation will not work')

    optic_name = input("Please select optical element: ")

    def find_optic_id_by_name(optic_name):
        for i in range(len(data['models']['beamline'])):
            if data['models']['beamline'][i]['title'] == optic_name:
                return i
        raise ValueError(f'Not valid optic {optic_name}')

    watch_name = input("Please select watchpoint: ")

    field0 = input("Please select parameter: ")
    if optic_name != watch_name:
        field0_units = sb.schema['model'][optic_name.lower()][field0][0].split('[')[1].split(']')[0]
    else:
        field0_units = sb.schema['model']['watch'][field0][0].split('[')[1].split(']')[0]
    print(field0_units)
    field0 = f'sirepo_{field0}'

    field1 = input("Please select another parameter or press ENTER to only use one: ")
    field1_units = None
    if field1 is not '':
        field1_units = sb.schema['model'][optic_name.lower()][field1][0].split('[')[1].split(']')[0]
        print(field1_units)
        field1 = f'sirepo_{field1}'
    else:
        field1 = None

    # First define a factory
    optic_id = find_optic_id_by_name(optic_name)
    schema = {f'sirepo_{k}': v for k, v in data['models']['beamline'][optic_id].items()}
              #if k not in non_parameters}
    def class_factory(cls_name):
        dd = {k: Cpt(SynAxis) for k in schema}
        return type(cls_name, (Device,), dd)

    SirepoComponent = class_factory('SirepoComponent')
    sirepo_component = SirepoComponent(name=optic_name)

    #obj0_su = 1 * unyt_obj0
    #in_meters = obj0_su.to('m')
    #print(float(in_meters.value))

    srw_det = SRWDetector(name='srw_det', sirepo_component=sirepo_component,
                          field0=field0, field0_units = field0_units,
                          field1=field1, field1_units = field1_units,
                          reg=db.reg, sim_id=sim_id, watch_name=watch_name)
    srw_det.read_attrs = ['image', 'mean', 'photon_energy']
    srw_det.configuration_attrs = ['horizontal_extent', 'vertical_extent',
                                   'shape']
    # Grid scan
    #RE(bp.grid_scan([srw_det],
                    #getattr(sirepo_component, field0), 0, 1e-3, 10,
                    #getattr(sirepo_component, field1), 0, 1e-3, 10,
                    #True))
    # 1D scan
    #RE(bps.mov(getattr(sirepo_component, field1), 1e-3))
    #RE(bp.scan([srw_det], getattr(sirepo_component, field0), 0,
               #1e-3, 10))

    # Watchpoint scan
    #RE(bp.rel_scan([srw_det], getattr(sirepo_component, field0), -.1, .1, 11))

